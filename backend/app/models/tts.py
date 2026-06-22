from pydantic import BaseModel, Field
from typing import Optional

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The text content to convert to speech.")
    language: str = Field("de", description="Language code (e.g. de, fr, es, it, pt, ta, te, ml, kn, mr).")
    gender: Optional[str] = Field("female", description="Gender of the voice: 'female' or 'male'.")
    rate: Optional[float] = Field(1.0, description="Speech rate/speed, e.g. 1.0 (normal), 1.2 (fast), 0.8 (slow).")
