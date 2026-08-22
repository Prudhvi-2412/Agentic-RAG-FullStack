"""TEMPORARY live integration check. Writes a handful of vectors under synthetic test
user ids and deletes them again. Deleted after the run."""

import asyncio
import os
import time
import uuid

os.environ.setdefault("SUPABASE_JWT_SECRET", "local-check-only")

from app.core.config import settings  # noqa: E402
from app.services.document import DocumentProcessor  # noqa: E402
from app.services.embedding import EmbeddingService  # noqa: E402
from app.services.reranker import GeminiReranker  # noqa: E402
from app.services.vectorstore import VectorStoreService  # noqa: E402

USER_A = "live-check-user-a"
USER_B = "live-check-user-b"

DOC_A = "Ikigai is the Japanese concept of a reason for being. " * 30
DOC_B = "Quantum chromodynamics describes the strong interaction between quarks. " * 30

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


async def wait_for(fn, attempts=12, delay=2.0):
    """Pinecone is eventually consistent; poll until the expectation holds."""
    for _ in range(attempts):
        value = await fn()
        if value:
            return value
        time.sleep(delay)
    return None


async def main():
    embeddings = EmbeddingService(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name)
    store = VectorStoreService(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        embedding_service=embeddings,
        reranker=GeminiReranker(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name),
    )
    processor = DocumentProcessor(api_key=None)  # skip vision to keep the check cheap

    doc_a = f"livecheck-{uuid.uuid4()}"
    doc_b = f"livecheck-{uuid.uuid4()}"

    try:
        chunks_a = processor.process_file(DOC_A.encode(), "live_check_a.txt", doc_a)
        chunks_b = processor.process_file(DOC_B.encode(), "live_check_b.txt", doc_b)
        check("chunking produces multiple chunks", len(chunks_a) > 1, f"{len(chunks_a)} chunks")

        await store.upsert_chunks(chunks_a, user_id=USER_A)
        await store.upsert_chunks(chunks_b, user_id=USER_B)
        check("upsert + real Gemini embeddings", True, f"{len(chunks_a) + len(chunks_b)} vectors")

        found = await wait_for(lambda: store.similarity_search("what is ikigai", top_k=3, user_id=USER_A))
        check("owner retrieves own document", bool(found),
              f"{[f['filename'] for f in (found or [])]}")

        leaked = [s for s in (found or []) if s["filename"] == "live_check_b.txt"]
        check("no cross-user leakage into user A's results", not leaked)

        b_results = await store.similarity_search("what is ikigai", top_k=3, user_id=USER_B)
        check("user B cannot retrieve user A's document",
              all(s["filename"] != "live_check_a.txt" for s in b_results),
              f"{[s['filename'] for s in b_results]}")

        anon = await store.similarity_search("what is ikigai", top_k=3, user_id=None)
        check("anonymous search excludes both private documents",
              all(s["filename"] not in ("live_check_a.txt", "live_check_b.txt") for s in anon),
              f"{[s['filename'] for s in anon]}")

        try:
            await store.delete_document(doc_a, user_id=USER_B)
            check("delete by non-owner is refused", False, "deletion was allowed!")
        except PermissionError:
            check("delete by non-owner is refused", True)

        await store.delete_document(doc_a, user_id=USER_A)
        check("owner delete succeeds on serverless index", True)

        gone = await wait_for(lambda: _absent(store, doc_a))
        check("deleted vectors are actually removed", bool(gone))

    finally:
        for doc, user in ((doc_a, USER_A), (doc_b, USER_B)):
            try:
                await store.delete_document(doc, user_id=user)
            except Exception:
                pass
        print("\ncleanup complete")

    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} live checks passed")
    return 1 if failed else 0


async def _absent(store, document_id):
    ids = await asyncio.to_thread(store._list_ids_with_prefix, f"{document_id}_")
    return not ids


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
