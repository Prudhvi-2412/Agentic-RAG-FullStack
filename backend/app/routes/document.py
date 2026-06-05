from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from app.models.document import DocumentUploadResponse
import uuid

router = APIRouter(prefix="/api")

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Ingests an uploaded file (PDF, DOCX, TXT, MD), parses text page-by-page,
    generates embeddings, and indexes them into Pinecone.
    """
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    
    # Validation check
    if ext not in ["pdf", "docx", "txt", "md", "markdown"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format: .{ext}. Supported formats are PDF, DOCX, TXT, and Markdown."
        )

    try:
        content_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file payload: {str(e)}")

    document_id = str(uuid.uuid4())
    
    # Retrieve singletons from app state
    processor = request.app.state.document_processor
    vectorstore = request.app.state.vector_store_service

    try:
        # Process and split file
        chunks = await processor.process_file(content_bytes, filename, document_id)
        if not chunks:
            raise HTTPException(
                status_code=400, 
                detail="No readable text contents could be parsed from this document. Please verify the file is not empty or scanned image only."
            )

        # Vector database upserting
        await vectorstore.upsert_chunks(chunks)

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            chunks_created=len(chunks),
            status="indexed"
        )
        
    except ImportError as ie:
        raise HTTPException(status_code=500, detail=f"Missing dependencies on server: {str(ie)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline ingestion failed: {str(e)}")
