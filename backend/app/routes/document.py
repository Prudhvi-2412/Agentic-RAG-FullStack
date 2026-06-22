from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Header
from app.models.document import DocumentUploadResponse
from app.core.auth import get_user_id_from_header
from typing import Optional
import uuid

router = APIRouter(prefix="/api")

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
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
    
    # Decode user ID if Authorization header is present
    user_id = get_user_id_from_header(authorization)
    
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

        # Vector database upserting (pass user_id for multi-tenancy)
        await vectorstore.upsert_chunks(chunks, user_id=user_id)

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

@router.delete("/documents/{document_id}")
async def delete_document_endpoint(request: Request, document_id: str, authorization: Optional[str] = Header(None)):
    """
    Deletes all indexed vectors associated with a document_id from Pinecone.
    """
    vectorstore = request.app.state.vector_store_service
    user_id = get_user_id_from_header(authorization)
    try:
        # Pass user_id to ensure a user can only delete their own documents
        await vectorstore.delete_document(document_id, user_id=user_id)
        return {"status": "success", "message": f"Document {document_id} deleted from Pinecone"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


import os

@router.get("/setup-ikigai")
async def setup_ikigai(request: Request):
    """
    Deletes all vectors of meditations.pdf and ingests Ikigai.pdf into Pinecone.
    """
    vectorstore = request.app.state.vector_store_service
    processor = request.app.state.document_processor
    
    # 1. Delete all vectors associated with old meditations books
    try:
        vectorstore.index.delete(filter={"filename": {"$in": ["meditations.pdf", "meidations.pdf", "Meditations.pdf"]}})
    except Exception as de:
        print(f"No existing meditations vectors to delete or delete failed: {de}")
        
    # 2. Locate and read Ikigai PDF
    pdf_filename = "Ikigai _ the Japanese secret to a long and happy life ( PDFDrive.com ).pdf"
    pdf_path = os.path.join("d:\\RAG-on-PDF-main\\Ai agent\\Agentic-RAG-FullStack", pdf_filename)
    
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join(os.getcwd(), pdf_filename)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Ikigai PDF not found in workspace path.")
            
    try:
        with open(pdf_path, "rb") as f:
            content_bytes = f.read()
            
        document_id = "ikigai-default-doc-id"
        chunks = await processor.process_file(content_bytes, "Ikigai.pdf", document_id)
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to parse text from Ikigai PDF.")
            
        await vectorstore.upsert_chunks(chunks)
        return {
            "status": "success",
            "message": "Deleted meditations.pdf and successfully ingested Ikigai.pdf",
            "chunks_created": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest Ikigai PDF: {str(e)}")
