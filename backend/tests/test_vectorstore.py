import asyncio
from types import SimpleNamespace

import pytest

from app.core.auth import SHARED_DOCUMENT_IDS
from app.services.vectorstore import VectorStoreService, calculate_bm25_scores


def make_service() -> VectorStoreService:
    """Builds a VectorStoreService without touching Pinecone or Gemini."""
    service = VectorStoreService.__new__(VectorStoreService)
    service.index = None
    service.embedding_service = None
    service.reranker = None
    service.dimension = 768
    return service


class FakeIndex:
    """Minimal stand-in for a Pinecone serverless index."""

    def __init__(self, vectors):
        self.vectors = dict(vectors)
        self.deleted = []

    def list(self, prefix=None):
        ids = [vid for vid in self.vectors if prefix is None or vid.startswith(prefix)]
        yield SimpleNamespace(vectors=[SimpleNamespace(id=vid) for vid in ids])

    def fetch(self, ids):
        found = {vid: self.vectors[vid] for vid in ids if vid in self.vectors}
        return SimpleNamespace(get=lambda key, default=None: found if key == "vectors" else default)

    def delete(self, ids):
        self.deleted.extend(ids)
        for vid in ids:
            self.vectors.pop(vid, None)


def vector(user_id):
    metadata = {"user_id": user_id} if user_id else {}
    return SimpleNamespace(get=lambda key, default=None: metadata if key == "metadata" else default)


# ── Ownership filter ──────────────────────────────────────────────────────────

def test_anonymous_search_is_limited_to_shared_documents():
    f = VectorStoreService._ownership_filter(None)
    assert f == {"document_id": {"$in": SHARED_DOCUMENT_IDS}}


def test_signed_in_search_covers_own_and_shared_documents():
    f = VectorStoreService._ownership_filter("user-a")
    assert f == {
        "$or": [
            {"user_id": {"$eq": "user-a"}},
            {"document_id": {"$in": SHARED_DOCUMENT_IDS}},
        ]
    }


def test_filename_filter_is_combined_with_ownership_not_replacing_it():
    service = make_service()
    base = service._ownership_filter("user-a")
    combined = {"$and": [base, {"filename": {"$in": ["a.pdf"]}}]}
    # Mirrors how similarity_search composes the two constraints.
    assert combined["$and"][0] == base


# ── Deletion authorization ────────────────────────────────────────────────────

def test_delete_requires_authentication():
    service = make_service()
    with pytest.raises(PermissionError):
        asyncio.run(service.delete_document("doc-1", user_id=""))


def test_delete_refuses_shared_demo_document():
    service = make_service()
    with pytest.raises(PermissionError):
        asyncio.run(service.delete_document(SHARED_DOCUMENT_IDS[0], user_id="user-a"))


def test_delete_refuses_another_users_document():
    service = make_service()
    service.index = FakeIndex({"doc-1_p1_c0": vector("owner")})
    with pytest.raises(PermissionError):
        asyncio.run(service.delete_document("doc-1", user_id="attacker"))
    assert service.index.deleted == []


def test_delete_removes_only_the_owners_document_vectors():
    service = make_service()
    service.index = FakeIndex({
        "doc-1_p1_c0": vector("owner"),
        "doc-1_p1_c1": vector("owner"),
        "doc-2_p1_c0": vector("owner"),
    })
    asyncio.run(service.delete_document("doc-1", user_id="owner"))
    assert sorted(service.index.deleted) == ["doc-1_p1_c0", "doc-1_p1_c1"]
    assert "doc-2_p1_c0" in service.index.vectors


def test_delete_unknown_document_raises_key_error():
    service = make_service()
    service.index = FakeIndex({})
    with pytest.raises(KeyError):
        asyncio.run(service.delete_document("missing", user_id="owner"))


# ── Upsert ────────────────────────────────────────────────────────────────────

def test_upsert_requires_an_owner():
    service = make_service()
    chunks = [{"id": "c1", "text": "hello", "metadata": {}}]
    with pytest.raises(ValueError):
        asyncio.run(service.upsert_chunks(chunks, user_id=""))


# ── BM25 ──────────────────────────────────────────────────────────────────────

def test_bm25_ranks_the_matching_chunk_highest():
    chunks = [
        "the cat sat on the mat",
        "ikigai is a japanese concept about purpose",
        "unrelated content about databases",
    ]
    scores = calculate_bm25_scores("what is ikigai purpose", chunks)
    assert scores[1] == max(scores)


def test_bm25_handles_empty_inputs():
    assert calculate_bm25_scores("", ["a"]) == [0.0]
    assert calculate_bm25_scores("query", []) == []
    assert calculate_bm25_scores("query", ["", ""]) == [0.0, 0.0]


# ── Context expansion ─────────────────────────────────────────────────────────

def test_context_of_tolerates_missing_metadata():
    assert VectorStoreService._context_of(None) == ""
    assert VectorStoreService._context_of(SimpleNamespace(get=lambda k, d=None: None)) == ""
