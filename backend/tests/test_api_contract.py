"""
End-to-end checks of the HTTP surface with the external services stubbed out.

These cover the parts of the contract the frontend depends on: which endpoints require
authentication, and the exact SSE event sequence emitted by /api/query.
"""

import io
import time
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.chat import ChatService
from app.services.document import DocumentProcessor


def auth_header(user_id="user-a"):
    token = jwt.encode(
        {"sub": user_id, "aud": settings.supabase_jwt_audience, "exp": int(time.time()) + 3600},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class StubVectorStore:
    def __init__(self):
        self.searches = []
        self.deleted = []

    async def similarity_search(self, query, top_k=4, filters=None, user_id=None):
        self.searches.append({"query": query, "filters": filters, "user_id": user_id})
        return [{
            "filename": "Ikigai.pdf",
            "chunk_id": "ikigai-default-doc-id_p1_c0",
            "page_number": 1,
            "relevance_score": 0.9,
            "context": "Ikigai is a reason for being.",
        }]

    async def upsert_chunks(self, chunks, user_id):
        self.upserted = (chunks, user_id)

    async def delete_document(self, document_id, user_id):
        self.deleted.append((document_id, user_id))


class StubRouter:
    def __init__(self, query_type="DOCUMENT_QUERY"):
        self.query_type = query_type

    async def classify_query(self, query):
        return self.query_type

    async def condense_query(self, query, history):
        return f"condensed::{query}"


class StubGeminiClient:
    """Mimics client.models.generate_content_stream yielding text chunks."""

    def __init__(self, texts):
        self.models = SimpleNamespace(generate_content_stream=lambda **kwargs: iter(
            [SimpleNamespace(text=t) for t in texts]
        ))


@pytest.fixture
def client():
    # Constructed without the lifespan context on purpose: startup would build real Pinecone
    # and Gemini clients. The services the routes read are injected directly instead.
    test_client = TestClient(app)
    store = StubVectorStore()
    app.state.vector_store_service = store
    app.state.query_router = StubRouter()
    app.state.document_processor = DocumentProcessor(api_key=None)

    chat_service = ChatService.__new__(ChatService)
    chat_service.vector_store_service = store
    chat_service.client = StubGeminiClient(["Hello ", "world"])
    chat_service.model_name = "stub-model"
    app.state.chat_service = chat_service

    test_client.stub_store = store
    return test_client


def parse_sse(body: str):
    events = []
    for packet in body.split("\n\n"):
        if not packet.strip():
            continue
        name = data = None
        for line in packet.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        events.append((name, data))
    return events


def test_root_reports_online(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


# ── Authentication enforcement ────────────────────────────────────────────────

def test_upload_requires_authentication(client):
    response = client.post("/api/upload", files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")})
    assert response.status_code == 401


def test_upload_rejects_forged_token(client):
    forged = jwt.encode({"sub": "attacker", "aud": "authenticated", "exp": int(time.time()) + 60},
                        "wrong-secret", algorithm="HS256")
    response = client.post(
        "/api/upload",
        files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")},
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/upload",
        files={"file": ("payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=auth_header(),
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(client):
    oversized = b"x" * (settings.max_upload_mb * 1024 * 1024 + 10)
    response = client.post(
        "/api/upload",
        files={"file": ("big.txt", io.BytesIO(oversized), "text/plain")},
        headers=auth_header(),
    )
    assert response.status_code == 413


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers=auth_header(),
    )
    assert response.status_code == 400


def test_upload_indexes_under_the_caller_id(client):
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", io.BytesIO(b"ikigai " * 200), "text/plain")},
        headers=auth_header("user-a"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "indexed"
    _, owner = client.stub_store.upserted
    assert owner == "user-a"


def test_delete_requires_authentication(client):
    assert client.delete("/api/documents/doc-1").status_code == 401


def test_delete_passes_caller_id_to_the_store(client):
    response = client.delete("/api/documents/doc-1", headers=auth_header("user-a"))
    assert response.status_code == 200
    assert client.stub_store.deleted == [("doc-1", "user-a")]


# ── SSE contract ──────────────────────────────────────────────────────────────

def test_query_streams_metadata_sources_tokens_then_complete(client):
    response = client.post("/api/query", json={"query": "What is ikigai?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "metadata"
    assert names[1] == "sources"
    assert names[-1] == "complete"
    assert names.count("token") == 2
    assert events[-1][1] == '{"status": "done"}'


def test_anonymous_query_is_scoped_to_anonymous_user_id(client):
    client.post("/api/query", json={"query": "What is ikigai?"})
    assert client.stub_store.searches[-1]["user_id"] is None


def test_authenticated_query_passes_verified_user_id(client):
    client.post("/api/query", json={"query": "What is ikigai?"}, headers=auth_header("user-a"))
    assert client.stub_store.searches[-1]["user_id"] == "user-a"


def test_query_with_history_uses_the_condensed_search_query(client):
    client.post("/api/query", json={
        "query": "and the second one?",
        "history": [{"role": "user", "text": "what is the first principle?"}],
    })
    assert client.stub_store.searches[-1]["query"].startswith("condensed::")


def test_query_rejects_invalid_payload(client):
    assert client.post("/api/query", json={"query": ""}).status_code == 422
    assert client.post("/api/query", json={}).status_code == 422


def test_query_rejects_forged_token(client):
    forged = jwt.encode({"sub": "attacker", "aud": "authenticated", "exp": int(time.time()) + 60},
                        "wrong-secret", algorithm="HS256")
    response = client.post(
        "/api/query",
        json={"query": "hi"},
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401


def test_general_chat_emits_no_sources_event(client):
    client.app.state.query_router = StubRouter("GENERAL_CHAT")
    response = client.post("/api/query", json={"query": "hello"})
    names = [name for name, _ in parse_sse(response.text)]
    assert "sources" not in names
    assert names[0] == "metadata"
    assert names[-1] == "complete"


def test_tts_validates_request_body(client):
    assert client.post("/api/tts", json={"text": "", "language": "de"}).status_code == 422
    assert client.post("/api/tts", json={"text": "hi", "rate": 99}).status_code == 422
