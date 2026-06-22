from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from app.models.chat import QueryRequest
from app.core.auth import get_user_id_from_header
from typing import Optional

router = APIRouter(prefix="/api")

@router.post("/query")
async def query_chat(request: Request, payload: QueryRequest, authorization: Optional[str] = Header(None)):
    """
    Handles conversational user queries. Uses the agentic classifier to route
    queries and streams token/source data back via Server-Sent Events (SSE).
    """
    query = payload.query
    
    router_service = request.app.state.query_router
    chat_service = request.app.state.chat_service
    
    try:
        # 1. Decode user ID if Authorization header is present
        user_id = get_user_id_from_header(authorization)
        
        # 2. Agentic Routing: Determine if query requires document retrieval or direct answer
        query_type = await router_service.classify_query(query)
        
        # 3. Query Condensation: If it is a follow-up document query, condense with history
        search_query = query
        if query_type == "DOCUMENT_QUERY" and payload.history:
            search_query = await router_service.condense_query(query, payload.history)
        
        # 4. Return SSE Stream
        return StreamingResponse(
            chat_service.stream_response(
                query=query, 
                query_type=query_type, 
                search_query=search_query, 
                filters=payload.filters,
                user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Prevents Nginx/CDN proxy token buffering
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query stream initialization failed: {str(e)}")

