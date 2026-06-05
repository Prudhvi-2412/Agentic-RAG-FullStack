import re
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.services.embedding import EmbeddingService

class VectorStoreService:
    def __init__(self, api_key: str, index_name: str, embedding_service: EmbeddingService):
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.embedding_service = embedding_service
        self.dimension = 768  # text-embedding-004 outputs 768-dimensional vectors
        
        # Verify index existence, creating if necessary
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index_exists(self):
        """
        Checks if the Pinecone index exists. If not, creates a new Serverless index.
        """
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'  # Default cloud/region for serverless free tier
                )
            )

    async def upsert_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Takes raw text chunks, generates embeddings, and upserts them to Pinecone.
        Each chunk is expected to be: {"id": str, "text": str, "metadata": dict}
        """
        if not chunks:
            return
        
        # Extract texts and get their embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_service.get_document_embeddings(texts)
        
        vectors = []
        for idx, chunk in enumerate(chunks):
            # Clone metadata to avoid modifying the input dict
            meta = chunk["metadata"].copy()
            meta["context"] = chunk["text"]  # Save actual text content inside metadata
            vectors.append((
                chunk["id"],
                embeddings[idx],
                meta
            ))
            
        # Batch upsert to prevent size limits
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch)

    async def similarity_search(self, query: str, top_k: int = 4, filters: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generates query embedding and retrieves relevant context chunks from Pinecone.
        Supports selective metadata filtering and dense-sparse hybrid keyword overlap reranking.
        """
        # 1. Setup metadata filter if specified
        pinecone_filter = None
        if filters:
            pinecone_filter = {"filename": {"$in": filters}}

        # 2. Get dense embedding
        query_vector = self.embedding_service.get_query_embedding(query)
        
        # 3. Retrieve candidate matches (get slightly more for reranking)
        candidate_k = top_k * 3 if top_k else 12
        response = self.index.query(
            vector=query_vector,
            top_k=candidate_k,
            filter=pinecone_filter,
            include_metadata=True
        )
        
        candidates = []
        for match in response.get("matches", []):
            metadata = match.get("metadata", {})
            context = metadata.pop("context", "")
            candidates.append({
                "filename": metadata.get("filename", "Unknown"),
                "chunk_id": metadata.get("chunk_id", match.id),
                "page_number": metadata.get("page_number"),
                "relevance_score": match.score,
                "context": context
            })
            
        if not candidates:
            return []

        # 4. Hybrid Search: Calculate keyword overlap (sparse simulation) & rerank
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        for cand in candidates:
            cand_text = cand["context"].lower()
            # Calculate match frequency for search terms
            match_count = sum(1 for term in query_terms if term in cand_text)
            # Normalize keyword overlap score
            keyword_score = match_count / max(1, len(query_terms))
            
            # Combine score: 0.7 dense (cosine) + 0.3 sparse (keyword overlap)
            cand["combined_score"] = 0.7 * cand["relevance_score"] + 0.3 * keyword_score

        # 5. Sort by combined score and return top_k
        candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Normalize score label back to relevance_score
        for cand in candidates:
            cand["relevance_score"] = cand.pop("combined_score")
            
        return candidates[:top_k]

    async def delete_document(self, document_id: str):
        """
        Deletes all vectors associated with a document_id using metadata filtering.
        """
        self.index.delete(filter={"document_id": {"$eq": document_id}})
