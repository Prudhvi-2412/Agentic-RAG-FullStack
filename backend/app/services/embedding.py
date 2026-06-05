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
        self.model_name = "text-embedding-004"

    def get_query_embedding(self, text: str) -> List[float]:
        """
        Generates a 768-dimensional embedding for a search query.
        Uses task_type='RETRIEVAL_QUERY'.
        """
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY"
            )
        )
        return response.embeddings[0].values

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
                task_type="RETRIEVAL_DOCUMENT"
            )
        )
        return [emb.values for emb in response.embeddings]
