from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.models.tts import TTSRequest

router = APIRouter(prefix="/api")

@router.post("/tts")
async def text_to_speech(request: Request, payload: TTSRequest):
    """
    Synthesizes the request text into a neural speech audio stream.
    Supports European and Indian regional dialects and returns a chunked MP3 stream.
    """
    tts_service = request.app.state.tts_service
    
    try:
        # Generate the asynchronous generator from the TTS service
        audio_generator = tts_service.stream_audio(
            text=payload.text,
            language=payload.language,
            gender=payload.gender,
            rate_val=payload.rate
        )
        
        return StreamingResponse(
            audio_generator,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "max-age=86400",  # Cache headers for CDNs/browsers
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {str(e)}"
        )
