from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.models.tts import TTSRequest

router = APIRouter(prefix="/api")


@router.post("/tts")
async def text_to_speech(request: Request, payload: TTSRequest):
    """
    Synthesizes the request text into a neural speech audio stream.
    Supports European and Indian regional dialects and returns a chunked MP3 stream.

    Synthesis errors surface as a truncated stream rather than an HTTP error status, because
    response headers are already committed once streaming starts; they are logged server-side.
    """
    tts_service = request.app.state.tts_service

    return StreamingResponse(
        tts_service.stream_audio(
            text=payload.text,
            language=payload.language,
            gender=payload.gender,
            rate_val=payload.rate
        ),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "Cache-Control": "max-age=86400",  # Cache headers for CDNs/browsers
            "X-Accel-Buffering": "no"
        }
    )
