from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's query or conversation prompt")
    filters: Optional[List[str]] = Field(None, description="Optional list of filenames to restrict the RAG vector search space")

class SourceCitation(BaseModel):
    filename: str = Field(..., description="Name of the source document file")
    chunk_id: str = Field(..., description="Unique ID of the text chunk")
    page_number: Optional[int] = Field(None, description="Page number where the chunk resides")
    relevance_score: float = Field(..., description="Cosine similarity relevance score (0.0 to 1.0)")
    context: str = Field(..., description="Snippet of retrieved text content")

# SSE event payloads
class SSEMetadataPayload(BaseModel):
    query_type: str = Field(..., description="Classification type: DOCUMENT_QUERY or GENERAL_CHAT")

class SSETokenPayload(BaseModel):
    text: str = Field(..., description="Generated text token")

class SSESourcesPayload(BaseModel):
    sources: List[SourceCitation] = Field(..., description="Retrieved source attributions")

class SSECompletePayload(BaseModel):
    status: str = Field("done", description="Completion status flag")
