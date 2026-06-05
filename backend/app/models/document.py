from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="Unique ID assigned to the uploaded document")
    filename: str = Field(..., description="Original name of the uploaded file")
    chunks_created: int = Field(..., description="Number of text chunks generated and indexed")
    status: str = Field("indexed", description="Ingestion processing status")

class DocumentMetadata(BaseModel):
    document_id: str = Field(..., description="Unique ID of the document")
    filename: str = Field(..., description="Original name of the file")
    chunk_id: str = Field(..., description="Unique ID of the specific chunk")
    upload_time: str = Field(..., description="ISO formatted upload timestamp")
    page_number: Optional[int] = Field(None, description="Page number the text chunk was extracted from (if applicable)")
    source_type: str = Field("pdf", description="Format type of the source document (pdf, docx, txt, md)")
