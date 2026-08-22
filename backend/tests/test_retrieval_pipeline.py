"""Exercises similarity_search end to end with Pinecone/Gemini replaced by fakes."""

import asyncio
from types import SimpleNamespace

from app.core.auth import SHARED_DOCUMENT_IDS
from app.services.vectorstore import VectorStoreService


class FakeEmbeddings:
    dimension = 768

    def __init__(self):
        self.queries = []

    def get_query_embedding(self, text, use_hyde=False):
        self.queries.append((text, use_hyde))
        return [0.1] * 8


class PassthroughReranker:
    async def rerank(self, query, candidates, top_k=4):
        return candidates[:top_k]


def match(chunk_id, score, context, metadata_extra=None, metadata=True):
    if not metadata:
        return SimpleNamespace(id=chunk_id, score=score, get=lambda k, d=None: None)
    meta = {"filename": "doc.pdf", "chunk_id": chunk_id, "page_number": 1, "context": context}
    meta.update(metadata_extra or {})
    return SimpleNamespace(id=chunk_id, score=score, get=lambda k, d=None: meta if k == "metadata" else d)


class FakeQueryIndex:
    def __init__(self, matches):
        self.matches = matches
        self.last_query = None

    def query(self, vector, top_k, filter, include_metadata):
        self.last_query = {"vector": vector, "top_k": top_k, "filter": filter}
        return SimpleNamespace(get=lambda k, d=None: self.matches if k == "matches" else d)

    def fetch(self, ids):
        return SimpleNamespace(get=lambda k, d=None: {} if k == "vectors" else d)


def build(matches):
    service = VectorStoreService.__new__(VectorStoreService)
    service.embedding_service = FakeEmbeddings()
    service.reranker = PassthroughReranker()
    service.dimension = 768
    service.index = FakeQueryIndex(matches)
    return service


def test_search_always_sends_an_ownership_filter_to_pinecone():
    service = build([match("d_p1_c0", 0.8, "some text about ikigai")])
    asyncio.run(service.similarity_search("ikigai", top_k=2, user_id="user-a"))
    assert service.index.last_query["filter"] == {
        "$or": [
            {"user_id": {"$eq": "user-a"}},
            {"document_id": {"$in": SHARED_DOCUMENT_IDS}},
        ]
    }


def test_anonymous_search_cannot_reach_user_documents():
    service = build([match("d_p1_c0", 0.8, "text")])
    asyncio.run(service.similarity_search("ikigai", top_k=2, user_id=None))
    assert service.index.last_query["filter"] == {"document_id": {"$in": SHARED_DOCUMENT_IDS}}


def test_filename_filter_cannot_widen_the_ownership_scope():
    service = build([match("d_p1_c0", 0.8, "text")])
    asyncio.run(service.similarity_search("ikigai", top_k=2, filters=["other.pdf"], user_id="user-a"))
    sent = service.index.last_query["filter"]
    assert "$and" in sent
    assert sent["$and"][0] == VectorStoreService._ownership_filter("user-a")
    assert sent["$and"][1] == {"filename": {"$in": ["other.pdf"]}}


def test_candidate_pool_is_three_times_top_k():
    service = build([match("d_p1_c0", 0.8, "text")])
    asyncio.run(service.similarity_search("ikigai", top_k=4, user_id="user-a"))
    assert service.index.last_query["top_k"] == 12


def test_hyde_expansion_is_enabled_for_the_query_embedding():
    service = build([match("d_p1_c0", 0.8, "text")])
    asyncio.run(service.similarity_search("ikigai", top_k=2, user_id="user-a"))
    assert service.embedding_service.queries == [("ikigai", True)]


def test_matches_without_metadata_do_not_crash_the_search():
    service = build([
        match("d_p1_c0", 0.8, "ikigai is purpose"),
        match("no-meta", 0.7, "", metadata=False),
    ])
    results = asyncio.run(service.similarity_search("ikigai", top_k=4, user_id="user-a"))
    assert [r["chunk_id"] for r in results] == ["d_p1_c0"]


def test_relevance_scores_stay_within_zero_and_one():
    service = build([
        match("d_p1_c0", 0.95, "ikigai purpose longevity"),
        match("d_p1_c1", -0.4, "completely unrelated"),
    ])
    results = asyncio.run(service.similarity_search("ikigai purpose", top_k=4, user_id="user-a"))
    assert results
    assert all(0.0 <= r["relevance_score"] <= 1.0 for r in results)


def test_empty_result_set_returns_no_sources():
    service = build([])
    assert asyncio.run(service.similarity_search("ikigai", top_k=4, user_id="user-a")) == []
