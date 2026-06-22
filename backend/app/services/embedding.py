from google import genai
from google.genai import types
from typing import List

class EmbeddingService:
    def __init__(self, api_key: str):
        """
        Initializes the EmbeddingService using the new google-genai Client.
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-embedding-001"
        self.query_cache = {}  # Cache for query embeddings to reduce latency and API cost

    def generate_hyde_text(self, query: str) -> str:
        """
        Generates a hypothetical document answer using Gemini for HyDE retrieval.
        """
        prompt = f"""Write a single paragraph that answers the following search query.
Write it as if it were a direct excerpt from a reference document or book.
Do not include any headers, preambles, or explanations. Just write the factual paragraph.

Query: {query}

Hypothetical Answer:"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"HyDE document generation failed: {e}")
        return query

    def get_query_embedding(self, text: str, use_hyde: bool = False) -> List[float]:
        """
        Generates a 768-dimensional embedding for a search query.
        Uses task_type='RETRIEVAL_QUERY'. Uses cache if available.
        Optionally uses HyDE (Hypothetical Document Embedding) query expansion.
        """
        cache_key = f"hyde_{text}" if use_hyde else f"raw_{text}"
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        # Helper to get embedding from Gemini
        def _embed(txt: str) -> List[float]:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=txt,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
            )
            return response.embeddings[0].values

        try:
            if use_hyde:
                # 1. Embed raw query
                query_emb = _embed(text)
                # 2. Generate hypothetical answer and embed it
                hyde_txt = self.generate_hyde_text(text)
                hyde_emb = _embed(hyde_txt)
                # 3. Fuse embeddings (0.5 query + 0.5 HyDE)
                final_emb = [0.5 * q + 0.5 * h for q, h in zip(query_emb, idx_val) for q, idx_val in [(query_emb, hyde_emb)]]
                # Wait, let's write zip directly:
                final_emb = [0.5 * q + 0.5 * h for q, h in zip(query_emb, hyde_emb)]
                self.query_cache[cache_key] = final_emb
                return final_emb
            else:
                final_emb = _embed(text)
                self.query_cache[cache_key] = final_emb
                return final_emb
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            # Fallback to direct raw embedding if HyDE processing fails
            return _embed(text)

    def get_document_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates 768-dimensional embeddings for a batch of document chunks.
        Uses task_type='RETRIEVAL_DOCUMENT'.
        """
        if not texts:
            return []
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768
            )
        )
        return [emb.values for emb in response.embeddings]

