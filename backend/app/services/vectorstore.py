import asyncio
import logging
import math
import re
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from app.core.auth import SHARED_DOCUMENT_IDS
from app.services.embedding import EmbeddingService
from app.services.reranker import BaseReranker

logger = logging.getLogger(__name__)

# Pinecone accepts at most 1000 ids per fetch/delete call.
_ID_BATCH_SIZE = 500


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
    # Guard against a division by zero when every candidate chunk is empty.
    if avg_doc_len <= 0:
        return [0.0] * len(chunks)

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
    def __init__(self, api_key: str, index_name: str, embedding_service: EmbeddingService, reranker: BaseReranker):
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.embedding_service = embedding_service
        self.reranker = reranker
        self.dimension = embedding_service.dimension

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

    async def upsert_chunks(self, chunks: List[Dict[str, Any]], user_id: str):
        """
        Takes raw text chunks, generates embeddings, and upserts them to Pinecone.
        Attaches user_id to metadata so retrieval and deletion can be scoped to the owner.
        """
        if not chunks:
            return
        if not user_id:
            raise ValueError("upsert_chunks requires an owning user_id")

        # Extract texts and get their embeddings (blocking HTTP call -> worker thread)
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await asyncio.to_thread(self.embedding_service.get_document_embeddings, texts)
        if len(embeddings) != len(chunks):
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(chunks)}, received {len(embeddings)}"
            )

        vectors = []
        for idx, chunk in enumerate(chunks):
            # Clone metadata to avoid modifying the input dict
            meta = chunk["metadata"].copy()
            meta["context"] = chunk["text"]  # Save actual text content inside metadata
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
            await asyncio.to_thread(self.index.upsert, vectors=batch)

    @staticmethod
    def _ownership_filter(user_id: Optional[str]) -> Dict[str, Any]:
        """
        Builds the metadata constraint that scopes a search to content the caller may read.

        Signed-in users see their own documents plus the shared demo document; anonymous
        callers see the shared demo document only. Without this, an anonymous request would
        match every tenant's vectors in the index.
        """
        if user_id:
            return {
                "$or": [
                    {"user_id": {"$eq": user_id}},
                    {"document_id": {"$in": SHARED_DOCUMENT_IDS}},
                ]
            }
        return {"document_id": {"$in": SHARED_DOCUMENT_IDS}}

    async def _expand_chunk_contexts(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sentence-Window Context Retrieval. Fetches adjacent preceding/succeeding chunks
        from Pinecone to restore complete context block before generator ingestion.
        """
        if not candidates:
            return []

        chunk_pattern = re.compile(r"(.+)_p(\d+)_c(\d+)")

        neighbours: Dict[str, tuple] = {}
        for cand in candidates:
            match = chunk_pattern.match(cand["chunk_id"])
            if not match:
                continue
            base_id, page_str, split_str = match.groups()
            split_idx = int(split_str)
            neighbours[cand["chunk_id"]] = (
                f"{base_id}_p{page_str}_c{split_idx - 1}",
                f"{base_id}_p{page_str}_c{split_idx + 1}",
            )

        if not neighbours:
            return candidates

        # De-duplicate: neighbouring candidates frequently request the same adjacent chunk.
        fetch_ids = sorted({cid for pair in neighbours.values() for cid in pair})

        try:
            fetch_response = await asyncio.to_thread(self.index.fetch, ids=fetch_ids)
            vectors = fetch_response.get("vectors", {}) or {}

            for cand in candidates:
                pair = neighbours.get(cand["chunk_id"])
                if not pair:
                    continue
                prev_id, next_id = pair

                prev_text = self._context_of(vectors.get(prev_id))
                next_text = self._context_of(vectors.get(next_id))

                full_context = ""
                if prev_text:
                    full_context += prev_text + "\n"
                full_context += cand["context"]
                if next_text:
                    full_context += "\n" + next_text

                cand["context"] = full_context.strip()
        except Exception as e:
            logger.warning("Context window expansion failed, using unexpanded chunks: %s", e)

        return candidates

    @staticmethod
    def _context_of(vector: Any) -> str:
        """Reads the stored chunk text off a Pinecone vector, tolerating absent metadata."""
        if vector is None:
            return ""
        metadata = vector.get("metadata") or {}
        return metadata.get("context", "") or ""

    async def similarity_search(self, query: str, top_k: int = 4, filters: Optional[List[str]] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generates query embedding, retrieves relevant candidate chunks from Pinecone,
        applies BM25 hybrid ranking, and reranks utilizing Gemini model.
        Results are always scoped to content the caller is allowed to read.
        """
        # 1. Setup multi-tenant query filter (always applied — never search the whole index)
        pinecone_filter: Dict[str, Any] = self._ownership_filter(user_id)
        if filters:
            pinecone_filter = {"$and": [pinecone_filter, {"filename": {"$in": filters}}]}

        # 2. Get dense embedding (utilizes HyDE query expansion)
        query_vector = await asyncio.to_thread(
            self.embedding_service.get_query_embedding, query, True
        )

        # 3. Retrieve candidates (expand search boundary to retrieve more candidates for reranking)
        candidate_k = top_k * 3 if top_k else 12
        response = await asyncio.to_thread(
            self.index.query,
            vector=query_vector,
            top_k=candidate_k,
            filter=pinecone_filter,
            include_metadata=True,
        )

        candidates = []
        for match in response.get("matches", []) or []:
            # Pinecone returns metadata=None when a vector carries no metadata.
            metadata = dict(match.get("metadata") or {})
            context = metadata.pop("context", "")
            if not context:
                continue
            candidates.append({
                "filename": metadata.get("filename", "Unknown"),
                "chunk_id": metadata.get("chunk_id", match.id),
                "page_number": metadata.get("page_number"),
                "relevance_score": float(match.score),
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

        # Normalize relevance back to candidate representation. The combined score is a
        # 0..1 blend, so clamp to keep the UI's "% match" readout meaningful even when a
        # dense cosine score comes back negative.
        for cand in candidates:
            cand["relevance_score"] = max(0.0, min(1.0, cand.pop("combined_score")))

        # 5. LLM-Based Reranking (Gemini Cross-Encoder)
        reranked_candidates = await self.reranker.rerank(query, candidates, top_k=top_k)

        # 6. Sentence-Window Context Expansion
        expanded_candidates = await self._expand_chunk_contexts(reranked_candidates)

        return expanded_candidates

    async def delete_document(self, document_id: str, user_id: str):
        """
        Deletes every vector belonging to a document, after verifying the caller owns it.

        Serverless Pinecone indexes do not support delete-by-metadata-filter, so vectors are
        enumerated by their `{document_id}_p{page}_c{n}` id prefix and removed by id.

        Raises PermissionError when the document belongs to another user or is shared demo
        content, and KeyError when no such document is indexed.
        """
        if not user_id:
            raise PermissionError("Authentication required to delete documents.")
        if document_id in SHARED_DOCUMENT_IDS:
            raise PermissionError("The shared demo document cannot be deleted.")

        prefix = f"{document_id}_"
        ids = await asyncio.to_thread(self._list_ids_with_prefix, prefix)
        if not ids:
            raise KeyError(document_id)

        # Every chunk of a document is written by a single upload, so the owner recorded on
        # the first chunk authoritatively identifies the document's owner.
        owner = await asyncio.to_thread(self._owner_of, ids[:1])
        if owner != user_id:
            raise PermissionError("You do not have permission to delete this document.")

        for i in range(0, len(ids), _ID_BATCH_SIZE):
            await asyncio.to_thread(self.index.delete, ids=ids[i : i + _ID_BATCH_SIZE])

    def _list_ids_with_prefix(self, prefix: str) -> List[str]:
        ids: List[str] = []
        for page in self.index.list(prefix=prefix):
            for vector in page.vectors or []:
                if vector.id:
                    ids.append(vector.id)
        return ids

    def _owner_of(self, ids: List[str]) -> Optional[str]:
        response = self.index.fetch(ids=ids)
        for vector in (response.get("vectors", {}) or {}).values():
            metadata = vector.get("metadata") or {}
            return metadata.get("user_id")
        return None
