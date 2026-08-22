from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    pinecone_api_key: str = Field(..., description="Pinecone Vector Database API Key")
    pinecone_index_name: str = Field("documind", description="Pinecone Index Name")
    gemini_model_name: str = Field("gemini-2.5-flash", description="Gemini Generative Model Name")

    # Supabase JWT verification (HS256 shared secret from the Supabase dashboard).
    # Required: without it the backend cannot prove which user a request belongs to,
    # and per-user document isolation would be unenforceable.
    supabase_jwt_secret: str = Field(..., description="Supabase JWT secret used to verify access tokens")
    supabase_jwt_audience: str = Field("authenticated", description="Expected 'aud' claim on Supabase access tokens")

    # HTTP. Kept as a raw string so the value can be supplied as a plain comma-separated
    # list in Render/CI env vars rather than JSON; see `cors_origins`.
    cors_allow_origins: str = Field(
        "http://localhost:5173",
        description="Comma-separated list of browser origins allowed to call this API",
    )

    # Ingestion limits
    max_upload_mb: int = Field(25, ge=1, le=200, description="Maximum accepted upload size in megabytes")
    max_tts_chars: int = Field(5000, ge=100, le=50000, description="Maximum accepted text length for a TTS request")

    # Project Settings
    api_title: str = "DocuMind AI Backend"
    api_version: str = "1.0.0"

    @property
    def cors_origins(self) -> List[str]:
        """The configured origins as a list, for the CORS middleware."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    # Allow loading from a local .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Fail fast: a missing or malformed critical setting must surface at startup rather than
# silently degrade into placeholder credentials that produce confusing runtime errors.
settings = Settings()
