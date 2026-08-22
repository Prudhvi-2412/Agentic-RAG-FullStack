import asyncio
import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.core.auth import require_user_id
from app.core.config import settings
from app.models.document import DocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

SUPPORTED_EXTENSIONS = ("pdf", "docx", "txt", "md", "markdown")
_MAX_FILENAME_LENGTH = 200
_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')


def sanitize_filename(raw_name: str) -> str:
    """
    Reduces a client-supplied filename to a safe display/metadata value.

    The name is never used to build a filesystem path, but it is stored in vector metadata,
    echoed back to every client, and used as a search filter — so path separators, traversal
    sequences and control characters are stripped here rather than trusted.
    """
    name = os.path.basename(raw_name.replace("\\", "/")).strip()
    name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    name = name.lstrip(".") or "document"
    return name[:_MAX_FILENAME_LENGTH]


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(require_user_id),
):
    """
    Ingests an uploaded file (PDF, DOCX, TXT, MD), parses text page-by-page,
    generates embeddings, and indexes them into Pinecone under the caller's user id.

    Authentication is required: an indexed document must have an owner, otherwise it could
    not be scoped on retrieval or deletion.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    filename = sanitize_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{ext}. Supported formats are PDF, DOCX, TXT, and Markdown."
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    try:
        content_bytes = await file.read(max_bytes + 1)
    except Exception as e:
        logger.warning("Failed to read upload payload: %s", e)
        raise HTTPException(status_code=400, detail="Failed to read the uploaded file.")

    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than the {settings.max_upload_mb} MB upload limit."
        )
    if not content_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    document_id = str(uuid.uuid4())

    # Retrieve singletons from app state
    processor = request.app.state.document_processor
    vectorstore = request.app.state.vector_store_service

    try:
        # Parsing rasterises pages and calls Gemini synchronously — keep it off the event loop.
        chunks = await asyncio.to_thread(processor.process_file, content_bytes, filename, document_id)
    except ImportError as ie:
        logger.error("Missing parser dependency: %s", ie)
        raise HTTPException(status_code=500, detail="This file type cannot be processed on the server.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Document parsing failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to parse the uploaded document.")

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No readable text contents could be parsed from this document. Please verify the file is not empty or scanned image only."
        )

    try:
        await vectorstore.upsert_chunks(chunks, user_id=user_id)
    except Exception as e:
        logger.exception("Indexing failed for %s: %s", filename, e)
        # A partially upserted document would answer queries with half its content, so roll
        # back whatever made it into the index before reporting the failure.
        try:
            await vectorstore.delete_document(document_id, user_id=user_id)
        except Exception as cleanup_error:
            logger.error("Could not roll back partial index for %s: %s", document_id, cleanup_error)
        raise HTTPException(status_code=502, detail="Failed to index the document. Please try again.")

    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        chunks_created=len(chunks),
        status="indexed"
    )


@router.delete("/documents/{document_id}")
async def delete_document_endpoint(
    request: Request,
    document_id: str,
    user_id: str = Depends(require_user_id),
):
    """
    Deletes all indexed vectors associated with a document_id from Pinecone.
    Ownership is verified server-side before anything is removed.
    """
    vectorstore = request.app.state.vector_store_service
    try:
        await vectorstore.delete_document(document_id, user_id=user_id)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found in the vector index.")
    except Exception as e:
        logger.exception("Deletion failed for %s: %s", document_id, e)
        raise HTTPException(status_code=502, detail="Failed to delete the document from the vector index.")

    return {"status": "success", "message": f"Document {document_id} deleted from Pinecone"}
