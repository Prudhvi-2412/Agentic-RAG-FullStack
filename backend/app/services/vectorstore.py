import re
import math
import json
import asyncio
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.services.embedding import EmbeddingService

def calculate_bm25_scores(query: str, chunks: List[str]) -> List[float]:
    """
    Computes standard BM25 scores for a list of document chunks against a search query.
    """
    query_terms = [t for t in re.findall(r'\w+', query.lower()) if len(t) > 1]
    if not query_terms or not chunks:
        return [0.0] * len(chunks)
        
    tokenized_chunks = [[t for t in re.findall(r'\w+', c.lower())] for c in chunks]
    doc_lengths = [len(c) for c in tokenized_chunks]
    avg_doc_len = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
    
    k1 = 1.5
    b = 0.75
    N = len(chunks)
    
    # Calculate document frequency (DF) for each query term
    df = {}
    for term in query_terms:
        df[term] = sum(1 for chunk in tokenized_chunks if term in chunk)
        
    # Calculate IDF for each query term
    idf = {}
    for term in query_terms:
        n_q = df[term]
        idf[term] = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
        
    scores = []
    for doc_idx, chunk in enumerate(tokenized_chunks):
        score = 0.0
        doc_len = doc_lengths[doc_idx]
        term_freqs = {}
        for term in chunk:
            term_freqs[term] = term_freqs.get(term, 0) + 1
            
        for term in query_terms:
            f_q = term_freqs.get(term, 0)
            if f_q > 0:
                numerator = f_q * (k1 + 1)
                denominator = f_q + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                score += idf[term] * (numerator / denominator)
        scores.append(score)
        
    return scores

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

    async def upsert_chunks(self, chunks: List[Dict[str, Any]], user_id: Optional[str] = None):
        """
        Takes raw text chunks, generates embeddings, and upserts them to Pinecone.
        Attaches user_id to metadata for multi-tenant isolation.
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
            if user_id:
                meta["user_id"] = user_id
                
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

    async def rerank_with_llm(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Reranks candidate chunks using Gemini (Cross-Encoder style) to select the most relevant ones.
        """
        if not candidates:
            return []
            
        # Limit to top 8 to control latency and token costs
        candidates_to_rank = candidates[:8]
        
        # Format chunks for prompt
        chunks_text = ""
        for idx, cand in enumerate(candidates_to_rank):
            chunks_text += f"[ID: {idx}] Document: {cand['filename']} (Page {cand.get('page_number', 'N/A')})\nContent: {cand['context']}\n---\n"
            
        prompt = f"""You are an expert search reranker. Your task is to select the top {top_k} most relevant candidate chunks to answer the User Query.
        
User Query: {query}

Candidate Chunks:
{chunks_text}

Analyze the user's intent and select the candidate chunks that contain directly useful information to answer the query.
Provide your response in JSON format matching this schema:
{{
  "ranked_ids": [integer, ...]
}}
List only the IDs (0-indexed) in order of relevance, with the most relevant first. Return at most {top_k} IDs.
Do not include any explanation or markdown formatting outside the JSON."""

        try:
            from google.genai import types
            loop = asyncio.get_event_loop()
            
            def call_gemini():
                return self.embedding_service.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                
            response = await loop.run_in_executor(None, call_gemini)
            
            # Clean potential codeblock wrappers
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```[a-zA-Z]*\n', '', text)
                text = re.sub(r'\n```$', '', text)
                text = text.strip()
                
            data = json.loads(text)
            ranked_ids = data.get("ranked_ids", [])
            
            reranked = []
            seen = set()
            for idx_val in ranked_ids:
                try:
                    idx = int(idx_val)
                    if 0 <= idx < len(candidates_to_rank) and idx not in seen:
                        reranked.append(candidates_to_rank[idx])
                        seen.add(idx)
                except (ValueError, TypeError):
                    continue
            
            # Fill remaining in original order
            for idx, cand in enumerate(candidates):
                if len(reranked) >= top_k:
                    break
                if cand not in reranked:
                    reranked.append(cand)
                    
            return reranked[:top_k]
        except Exception as e:
            print(f"Gemini reranking failed: {e}. Falling back to hybrid score ranking.")
            return candidates[:top_k]

    async def _expand_chunk_contexts(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sentence-Window Context Retrieval. Fetches adjacent preceding/succeeding chunks 
        from Pinecone to restore complete context block before generator ingestion.
        """
        if not candidates:
            return []
            
        fetch_ids = []
        cand_map = {}
        for cand in candidates:
            chunk_id = cand["chunk_id"]
            cand_map[chunk_id] = cand
            
            match = re.match(r"(.+)_p(\d+)_c(\d+)", chunk_id)
            if match:
                base_id, page_str, split_str = match.groups()
                split_idx = int(split_str)
                
                prev_id = f"{base_id}_p{page_str}_c{split_idx - 1}"
                next_id = f"{base_id}_p{page_str}_c{split_idx + 1}"
                fetch_ids.extend([prev_id, next_id])
                
        if not fetch_ids:
            return candidates
            
        try:
            fetch_response = self.index.fetch(ids=fetch_ids)
            vectors = fetch_response.get("vectors", {})
            
            for cand in candidates:
                chunk_id = cand["chunk_id"]
                match = re.match(r"(.+)_p(\d+)_c(\d+)", chunk_id)
                if match:
                    base_id, page_str, split_str = match.groups()
                    split_idx = int(split_str)
                    
                    prev_id = f"{base_id}_p{page_str}_c{split_idx - 1}"
                    next_id = f"{base_id}_p{page_str}_c{split_idx + 1}"
                    
                    prev_text = vectors.get(prev_id, {}).get("metadata", {}).get("context", "") if prev_id in vectors else ""
                    next_text = vectors.get(next_id, {}).get("metadata", {}).get("context", "") if next_id in vectors else ""
                    
                    full_context = ""
                    if prev_text:
                        full_context += prev_text + "\n"
                    full_context += cand["context"]
                    if next_text:
                        full_context += "\n" + next_text
                        
                    cand["context"] = full_context.strip()
        except Exception as e:
            print(f"Error expanding context windows: {e}")
            
        return candidates

    async def similarity_search(self, query: str, top_k: int = 4, filters: Optional[List[str]] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generates query embedding, retrieves relevant candidate chunks from Pinecone, 
        applies BM25 hybrid ranking, and reranks utilizing Gemini model.
        Supports selective metadata user_id isolation.
        """
        # 1. Setup multi-tenant query filter
        pinecone_filter = None
        if user_id:
            pinecone_filter = {
                "$or": [
                    {"user_id": {"$eq": user_id}},
                    {"document_id": {"$eq": "ikigai-default-doc-id"}}
                ]
            }
            if filters:
                pinecone_filter["filename"] = {"$in": filters}
        elif filters:
            pinecone_filter = {"filename": {"$in": filters}}

        # 2. Get dense embedding (utilizes HyDE query expansion)
        query_vector = self.embedding_service.get_query_embedding(query, use_hyde=True)
        
        # 3. Retrieve candidates (expand search boundary to retrieve more candidates for reranking)
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

        # 4. Local BM25 Hybrid reranking
        contexts = [c["context"] for c in candidates]
        bm25_scores = calculate_bm25_scores(query, contexts)
        
        min_bm25 = min(bm25_scores)
        max_bm25 = max(bm25_scores)
        bm25_range = max_bm25 - min_bm25
        
        # Normalize BM25 scores
        normalized_bm25 = []
        for s in bm25_scores:
            val = (s - min_bm25) / bm25_range if bm25_range > 0 else 0.0
            normalized_bm25.append(val)
            
        # Combine score: 0.5 dense cosine similarity + 0.5 normalized BM25 score
        for idx, cand in enumerate(candidates):
            cand["combined_score"] = 0.5 * cand["relevance_score"] + 0.5 * normalized_bm25[idx]

        candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Normalize relevance back to candidate representation
        for cand in candidates:
            cand["relevance_score"] = cand.pop("combined_score")

        # 5. LLM-Based Reranking (Gemini Cross-Encoder)
        reranked_candidates = await self.rerank_with_llm(query, candidates, top_k=top_k)
        
        # 6. Sentence-Window Context Expansion
        expanded_candidates = await self._expand_chunk_contexts(reranked_candidates)
        
        return expanded_candidates

    async def delete_document(self, document_id: str, user_id: Optional[str] = None):
        """
        Deletes all vectors associated with a document_id using metadata filtering.
        Optionally restricts to user_id for multi-tenant security.
        """
        delete_filter = {"document_id": {"$eq": document_id}}
        if user_id:
            delete_filter["user_id"] = {"$eq": user_id}
        self.index.delete(filter=delete_filter)

