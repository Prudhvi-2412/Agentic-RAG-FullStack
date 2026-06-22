import json
import re
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from google import genai
from google.genai import types
from app.core.retry import retry_with_backoff

class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Abstract method to rerank candidate documents based on user query relevance.
        """
        pass

class GeminiReranker(BaseReranker):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name.replace("models/", "")

    async def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 4) -> List[Dict[str, Any]]:
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
            loop = asyncio.get_event_loop()
            
            def call_gemini():
                return retry_with_backoff(
                    self.client.models.generate_content,
                    model=self.model_name,
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
