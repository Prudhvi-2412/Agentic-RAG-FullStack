from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    pinecone_api_key: str = Field(..., description="Pinecone Vector Database API Key")
    pinecone_index_name: str = Field("documind", description="Pinecone Index Name")
    gemini_model_name: str = Field("gemini-1.5-flash", description="Gemini Generative Model Name")
    
    # Project Settings
    api_title: str = "DocuMind AI Backend"
    api_version: str = "1.0.0"
    
    # Allow loading from a local .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

try:
    settings = Settings()
except Exception as e:
    # If variables are missing, print a clear warning but don't crash the importing script during code editing
    print(f"Configuration warning: {e}")
    # Create a dummy settings instance with placeholders to prevent import-time crashes
    class DummySettings:
        gemini_api_key = "PLACEHOLDER_GEMINI_KEY"
        pinecone_api_key = "PLACEHOLDER_PINECONE_KEY"
        pinecone_index_name = "documind"
        gemini_model_name = "gemini-1.5-flash"
        api_title = "DocuMind AI Backend (Development Mode)"
        api_version = "1.0.0"
    settings = DummySettings()
