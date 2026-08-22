"""
Indexes the shared demo document that every visitor (signed in or not) can query.

This used to be an unauthenticated `GET /api/setup-ikigai` endpoint that deleted vectors by
filter and re-ingested a PDF from a hard-coded local path. It is an operator task, not part
of the public API, so it lives here instead.

Usage (from the backend/ directory, with backend/.env configured):

    python seed_demo_document.py "../Ikigai _ the Japanese secret to a long and happy life ( PDFDrive.com ).pdf"

Optional second argument overrides the display filename shown in citations (default Ikigai.pdf).
"""

import asyncio
import sys
from pathlib import Path

from app.core.auth import SHARED_DOCUMENT_IDS
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.document import DocumentProcessor
from app.services.embedding import EmbeddingService
from app.services.reranker import GeminiReranker
from app.services.vectorstore import VectorStoreService

DEMO_DOCUMENT_ID = SHARED_DOCUMENT_IDS[0]


async def main(pdf_path: Path, display_name: str) -> int:
    if not pdf_path.is_file():
        print(f"File not found: {pdf_path}")
        return 1

    embedding_svc = EmbeddingService(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name)
    vectorstore = VectorStoreService(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        embedding_service=embedding_svc,
        reranker=GeminiReranker(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name),
    )
    processor = DocumentProcessor(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name)

    content_bytes = pdf_path.read_bytes()
    chunks = await asyncio.to_thread(
        processor.process_file, content_bytes, display_name, DEMO_DOCUMENT_ID
    )
    if not chunks:
        print("No readable text could be parsed from the document.")
        return 1

    # The demo document is shared, so it is stored under a reserved owner id that no Supabase
    # user can hold; delete_document() additionally refuses to remove it.
    await vectorstore.upsert_chunks(chunks, user_id="shared-demo")
    print(f"Indexed {len(chunks)} chunks as '{display_name}' (document_id={DEMO_DOCUMENT_ID}).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)

    setup_logging()
    path = Path(sys.argv[1]).expanduser()
    name = sys.argv[2] if len(sys.argv) > 2 else "Ikigai.pdf"
    raise SystemExit(asyncio.run(main(path, name)))
