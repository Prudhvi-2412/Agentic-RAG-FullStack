import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.auth import get_user_id_from_header
from app.models.chat import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/query")
async def query_chat(
    request: Request,
    payload: QueryRequest,
    user_id: Optional[str] = Depends(get_user_id_from_header),
):
    """
    Handles conversational user queries. Uses the agentic classifier to route
    queries and streams token/source data back via Server-Sent Events (SSE).

    Anonymous callers are allowed, but retrieval is scoped to shared demo content only.
    """
    query = payload.query

    router_service = request.app.state.query_router
    chat_service = request.app.state.chat_service

    try:
        # 1. Agentic Routing: Determine if query requires document retrieval or direct answer
        query_type = await router_service.classify_query(query)

        # 2. Query Condensation: If it is a follow-up document query, condense with history
        search_query = query
        if query_type == "DOCUMENT_QUERY" and payload.history:
            search_query = await router_service.condense_query(query, payload.history)
    except Exception as e:
        logger.exception("Query stream initialization failed: %s", e)
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable. Please try again.")

    # 3. Return SSE Stream
    return StreamingResponse(
        chat_service.stream_response(
            query=query,
            query_type=query_type,
            search_query=search_query,
            filters=payload.filters,
            user_id=user_id,
            history=payload.history,
            is_disconnected=request.is_disconnected,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Prevents Nginx/CDN proxy token buffering
        }
    )
