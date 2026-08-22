from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import settings


class TTSRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_tts_chars,
        description="The text content to convert to speech.",
    )
    language: str = Field("de", max_length=10, description="Language code (e.g. de, fr, es, it, pt, ta, te, ml, kn, mr).")
    gender: Optional[Literal["female", "male"]] = Field("female", description="Gender of the voice: 'female' or 'male'.")
    rate: float = Field(
        1.0,
        ge=0.5,
        le=2.0,
        description="Speech rate/speed, e.g. 1.0 (normal), 1.2 (fast), 0.8 (slow).",
    )
