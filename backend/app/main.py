import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.routes import chat, document, tts
from app.services.chat import ChatService
from app.services.document import DocumentProcessor
from app.services.embedding import EmbeddingService
from app.services.reranker import GeminiReranker
from app.services.router import QueryRouter
from app.services.tts import TTSService
from app.services.vectorstore import VectorStoreService

# 1. Setup system-wide structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    State-based dependency injection on FastAPI application startup.
    Instantiates services once and binds them to the application state context.
    """
    model_name = settings.gemini_model_name

    embedding_svc = EmbeddingService(api_key=settings.gemini_api_key, model_name=model_name)
    reranker_svc = GeminiReranker(api_key=settings.gemini_api_key, model_name=model_name)

    vectorstore_svc = VectorStoreService(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        embedding_service=embedding_svc,
        reranker=reranker_svc
    )

    app.state.embedding_service = embedding_svc
    app.state.vector_store_service = vectorstore_svc
    app.state.document_processor = DocumentProcessor(api_key=settings.gemini_api_key, model_name=model_name)
    app.state.query_router = QueryRouter(api_key=settings.gemini_api_key, model_name=model_name)
    app.state.chat_service = ChatService(
        api_key=settings.gemini_api_key,
        vector_store_service=vectorstore_svc,
        model_name=model_name
    )
    app.state.reranker_service = reranker_svc
    app.state.tts_service = TTSService()

    logger.info("DocuMind AI services initialized (index=%s, model=%s)", settings.pinecone_index_name, model_name)
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)

# 2. Configure CORS middleware. Credentialed requests cannot use a wildcard origin, so the
# allowed origins are configured explicitly per environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# 3. Include endpoint routers
app.include_router(document.router)
app.include_router(chat.router)
app.include_router(tts.router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "DocuMind AI Backend API",
        "version": settings.api_version
    }
