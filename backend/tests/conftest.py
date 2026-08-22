import os

# Settings are constructed at import time and intentionally fail fast when a critical
# variable is missing, so the test environment must be populated before app imports.
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:5173")
