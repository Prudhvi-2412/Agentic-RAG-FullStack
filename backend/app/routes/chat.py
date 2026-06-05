from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.models.chat import QueryRequest

router = APIRouter(prefix="/api")

@router.post("/query")
async def query_chat(request: Request, payload: QueryRequest):
    """
    Handles conversational user queries. Uses the agentic classifier to route
    queries and streams token/source data back via Server-Sent Events (SSE).
    """
    query = payload.query
    
    router_service = request.app.state.query_router
    chat_service = request.app.state.chat_service
    
    try:
        # 1. Agentic Routing: Determine if query requires document retrieval or direct answer
        query_type = await router_service.classify_query(query)
        
        # 2. Return SSE Stream
        return StreamingResponse(
            chat_service.stream_response(query, query_type, filters=payload.filters),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Prevents Nginx/CDN proxy token buffering
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query stream initialization failed: {str(e)}")
