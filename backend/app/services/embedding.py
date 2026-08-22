import logging
from collections import OrderedDict
from typing import List

from google import genai
from google.genai import types

from app.core.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# The Gemini embeddings endpoint rejects oversized batches, so document chunks are embedded
# in fixed-size groups instead of a single request per upload.
_EMBED_BATCH_SIZE = 64

# Query embeddings are cached to avoid paying for a repeated HyDE round-trip on identical
# questions. Bounded so a long-running server cannot grow the cache without limit.
_QUERY_CACHE_MAX = 256


class EmbeddingService:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initializes the EmbeddingService using the new google-genai Client.

        `model_name` is the generative model used for HyDE hypothetical-answer generation;
        embeddings always use the dedicated embedding model.
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-embedding-001"
        self.generation_model_name = model_name.replace("models/", "")
        self.dimension = 768
        self.query_cache: "OrderedDict[str, List[float]]" = OrderedDict()

    def _cache_get(self, key: str):
        if key in self.query_cache:
            self.query_cache.move_to_end(key)
            return self.query_cache[key]
        return None

    def _cache_put(self, key: str, value: List[float]) -> None:
        self.query_cache[key] = value
        self.query_cache.move_to_end(key)
        while len(self.query_cache) > _QUERY_CACHE_MAX:
            self.query_cache.popitem(last=False)

    def generate_hyde_text(self, query: str) -> str:
        """
        Generates a hypothetical document answer using Gemini for HyDE retrieval.
        Falls back to the raw query when generation fails, so retrieval still proceeds.
        """
        prompt = f"""Write a single paragraph that answers the following search query.
Write it as if it were a direct excerpt from a reference document or book.
Do not include any headers, preambles, or explanations. Just write the factual paragraph.

Query: {query}

Hypothetical Answer:"""
        try:
            response = retry_with_backoff(
                self.client.models.generate_content,
                model=self.generation_model_name,
                contents=prompt
            )
            text = getattr(response, "text", None)
            if text:
                return text.strip()
        except Exception as e:
            logger.warning("HyDE document generation failed, using raw query: %s", e)
        return query

    def _embed(self, contents, task_type: str) -> List[List[float]]:
        response = retry_with_backoff(
            self.client.models.embed_content,
            model=self.model_name,
            contents=contents,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimension
            )
        )
        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            raise RuntimeError("Gemini embeddings API returned no embeddings")
        return [emb.values for emb in embeddings]

    def get_query_embedding(self, text: str, use_hyde: bool = False) -> List[float]:
        """
        Generates a 768-dimensional embedding for a search query.
        Uses task_type='RETRIEVAL_QUERY'. Uses cache if available.
        Optionally uses HyDE (Hypothetical Document Embedding) query expansion.
        """
        cache_key = f"hyde_{text}" if use_hyde else f"raw_{text}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        query_emb = self._embed(text, "RETRIEVAL_QUERY")[0]

        if use_hyde:
            # generate_hyde_text already degrades to the raw query on failure; if embedding the
            # hypothetical answer fails we still have a usable plain query embedding.
            hyde_txt = self.generate_hyde_text(text)
            if hyde_txt and hyde_txt != text:
                try:
                    hyde_emb = self._embed(hyde_txt, "RETRIEVAL_QUERY")[0]
                    query_emb = [0.5 * q + 0.5 * h for q, h in zip(query_emb, hyde_emb)]
                except Exception as e:
                    logger.warning("HyDE embedding failed, using plain query embedding: %s", e)

        self._cache_put(cache_key, query_emb)
        return query_emb

    def get_document_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates 768-dimensional embeddings for a batch of document chunks.
        Uses task_type='RETRIEVAL_DOCUMENT'.
        """
        if not texts:
            return []

        embeddings: List[List[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[i : i + _EMBED_BATCH_SIZE]
            batch_embeddings = self._embed(batch, "RETRIEVAL_DOCUMENT")
            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    f"Gemini returned {len(batch_embeddings)} embeddings for {len(batch)} chunks"
                )
            embeddings.extend(batch_embeddings)
        return embeddings
