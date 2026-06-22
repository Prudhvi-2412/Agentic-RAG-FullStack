import json
import asyncio
from google import genai
from typing import AsyncGenerator, Optional
from app.services.vectorstore import VectorStoreService

class ChatService:
    def __init__(self, api_key: str, vector_store_service: VectorStoreService, model_name: str = "gemini-2.5-flash"):
        """
        Initializes the ChatService using the new google-genai Client.
        """
        self.api_key = api_key
        self.vector_store_service = vector_store_service
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name.replace("models/", "")

    async def stream_response(self, query: str, query_type: str, search_query: Optional[str] = None, filters: Optional[list] = None, user_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Coordinates routing paths and streams response tokens formatted as Server-Sent Events (SSE).
        Uses search_query (if provided) for vector retrieval, and query for generation context.
        Yields:
            event: metadata -> classification path
            event: sources  -> retrieved source attributions (if DOCUMENT_QUERY)
            event: token    -> generated token text
            event: complete -> streaming finished event
        """
        try:
            # 1. Immediately yield metadata event
            yield f"event: metadata\ndata: {json.dumps({'query_type': query_type})}\n\n"
            await asyncio.sleep(0.01)  # Brief yield to push buffer

            sources = []
            
            # 2. Retrieve sources if it is a document query
            if query_type == "DOCUMENT_QUERY":
                try:
                    retrieval_query = search_query or query
                    sources = await self.vector_store_service.similarity_search(retrieval_query, top_k=4, filters=filters, user_id=user_id)
                    yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
                    await asyncio.sleep(0.01)
                except Exception as ve:
                    print(f"Error retrieving sources from Pinecone: {ve}")
                    # Yield empty sources so client knows retrieval step is done
                    yield f"event: sources\ndata: {json.dumps({'sources': []})}\n\n"
                    await asyncio.sleep(0.01)


            # 3. Construct prompt based on type
            if query_type == "DOCUMENT_QUERY" and sources:
                # Compile retrieved snippets
                context_blocks = []
                for s in sources:
                    page_info = f"Page {s['page_number']}" if s.get('page_number') else "Unknown Page"
                    context_blocks.append(
                        f"Source Document: {s['filename']} ({page_info})\n"
                        f"Snippet:\n{s['context']}"
                    )
                
                context_str = "\n\n---\n\n".join(context_blocks)
                
                prompt = f"""You are an expert AI document assistant named DocuMind AI.
Answer the user's query using ONLY the retrieved context below.

Retrieved Context:
{context_str}

User Query: {query}

Instructions:
- Base your answers strictly on the context provided above.
- Ground your statements and use inline numerical citations like [1], [2] to reference the context sources. The index corresponds to the 1-based order of the source documents provided in the Retrieved Context above.
- Place citations at the end of relevant sentences.
- If the context does not contain enough information to answer the question, state clearly that the answer is not present in the uploaded documents. Do not make up facts or hallucinate.
- Use clean, premium markdown formatting (headers, bold, bullet points, tables where appropriate) for readability.
- Maintain a helpful, analytical, and professional tone.

Answer:"""
            else:
                # General conversation or fallback path
                prompt = f"""You are an expert AI assistant named DocuMind AI. 
Answer the user's general query. You do not need to look up document contexts for this.

User Query: {query}

Answer:"""

            # 4. Generate content stream from Gemini in a separate thread to prevent blocking the async loop
            loop = asyncio.get_event_loop()
            
            def generate():
                from app.core.retry import retry_with_backoff
                return retry_with_backoff(
                    self.client.models.generate_content_stream,
                    model=self.model_name,
                    contents=prompt
                )

            response_stream = await loop.run_in_executor(None, generate)

            # 5. Stream the tokens to the client
            for chunk in response_stream:
                if chunk.text:
                    token_data = {"text": chunk.text}
                    yield f"event: token\ndata: {json.dumps(token_data)}\n\n"
                    # Small sleep to yield execution to event loop
                    await asyncio.sleep(0.01)

            # 6. Stream completion confirmation
            yield f"event: complete\ndata: {json.dumps({'status': 'done'})}\n\n"

        except Exception as e:
            # Clean error handler yielding failure token so UI doesn't hang
            error_data = {"text": f"\n\n*Error generating response: {str(e)}*"}
            yield f"event: token\ndata: {json.dumps(error_data)}\n\n"
            yield f"event: complete\ndata: {json.dumps({'status': 'error'})}\n\n"
