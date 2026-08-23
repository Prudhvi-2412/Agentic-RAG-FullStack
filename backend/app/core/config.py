from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    pinecone_api_key: str = Field(..., description="Pinecone Vector Database API Key")
    pinecone_index_name: str = Field("documind", description="Pinecone Index Name")
    gemini_model_name: str = Field("gemini-2.5-flash", description="Gemini Generative Model Name")

    # Supabase access-token verification. Supabase signs tokens either with a legacy shared
    # HS256 secret or with asymmetric keys published as a JWKS, depending on the project's
    # age and settings — so at least one of these must be configured. Without a way to verify
    # signatures the backend cannot prove which user a request belongs to, and per-user
    # document isolation would be unenforceable.
    supabase_jwt_secret: Optional[str] = Field(
        None, description="Legacy Supabase JWT secret, for projects signing with HS256"
    )
    supabase_url: Optional[str] = Field(
        None, description="Supabase project URL, used to fetch the JWKS for asymmetric (ES256/RS256) tokens"
    )
    supabase_jwt_audience: str = Field("authenticated", description="Expected 'aud' claim on Supabase access tokens")

    @model_validator(mode="after")
    def _require_a_token_verification_method(self):
        if not self.supabase_jwt_secret and not self.supabase_url:
            raise ValueError(
                "No way to verify Supabase access tokens. Set SUPABASE_JWT_SECRET (Supabase "
                "dashboard -> Project Settings -> API -> JWT Secret / Legacy JWT Secret) for "
                "HS256-signed projects, or SUPABASE_URL (e.g. https://<ref>.supabase.co) for "
                "projects using asymmetric JWT signing keys. Setting both is safe."
            )
        return self

    @property
    def supabase_jwks_url(self) -> Optional[str]:
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

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
