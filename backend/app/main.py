from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.routes import document, chat, tts
from app.services.document import DocumentProcessor
from app.services.embedding import EmbeddingService
from app.services.vectorstore import VectorStoreService
from app.services.router import QueryRouter
from app.services.chat import ChatService
from app.services.reranker import GeminiReranker
from app.services.tts import TTSService

# 1. Setup system-wide structured logging
setup_logging()

app = FastAPI(
    title=getattr(settings, "api_title", "DocuMind AI API"),
    version=getattr(settings, "api_version", "1.0.0")
)

# 2. Configure CORS middleware (permits frontend client communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to specify the frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """
    State-based dependency injection on FastAPI application startup.
    Instantiates services once and binds them to the application state context.
    """
    gemini_key = getattr(settings, "gemini_api_key", "")
    pinecone_key = getattr(settings, "pinecone_api_key", "")
    index_name = getattr(settings, "pinecone_index_name", "documind")
    
    model_name = getattr(settings, "gemini_model_name", "gemini-2.5-flash")
    
    # Initialize services
    embedding_svc = EmbeddingService(api_key=gemini_key)
    reranker_svc = GeminiReranker(api_key=gemini_key, model_name=model_name)
    
    vectorstore_svc = VectorStoreService(
        api_key=pinecone_key,
        index_name=index_name,
        embedding_service=embedding_svc,
        reranker=reranker_svc
    )
    
    doc_processor = DocumentProcessor(api_key=gemini_key, model_name=model_name)
    router_svc = QueryRouter(api_key=gemini_key, model_name=model_name)
    
    chat_svc = ChatService(
        api_key=gemini_key,
        vector_store_service=vectorstore_svc,
        model_name=model_name
    )
    
    tts_svc = TTSService()
    
    # Store instances in app state for request-level route sharing
    app.state.embedding_service = embedding_svc
    app.state.vector_store_service = vectorstore_svc
    app.state.document_processor = doc_processor
    app.state.query_router = router_svc
    app.state.chat_service = chat_svc
    app.state.reranker_service = reranker_svc
    app.state.tts_service = tts_svc

# 3. Include endpoint routers
app.include_router(document.router)
app.include_router(chat.router)
app.include_router(tts.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "DocuMind AI Backend API",
        "version": getattr(settings, "api_version", "1.0.0")
    }
