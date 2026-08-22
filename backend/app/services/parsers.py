import concurrent.futures
import io
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.core.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Graceful docx import
try:
    import docx
except ImportError:
    docx = None

VISION_PROMPT = (
    "Extract and describe all structural elements on this page. If there are tables, "
    "transcribe them in markdown format. If there are charts or diagrams, describe them "
    "in detail. If there are headers, signatures, or handwriting, mention them."
)

# Pages are rendered on the calling thread (PyMuPDF Document objects are not thread-safe)
# and only the Gemini vision calls are parallelised, in groups of this size.
_VISION_BATCH_SIZE = 8


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str, client = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, Any]]:
        """
        Parses file bytes and returns a list of dictionaries with text and page numbers.
        [{"text": str, "page_number": int}]
        """
        pass

class PDFParser(BaseParser):
    def parse(self, file_bytes: bytes, filename: str, client = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, Any]]:
        import fitz  # PyMuPDF

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"The PDF could not be opened; it may be corrupted or password protected. ({e})")

        pages: List[Dict[str, Any]] = []
        try:
            if doc.needs_pass:
                raise ValueError("Password protected PDFs are not supported.")

            for start in range(0, doc.page_count, _VISION_BATCH_SIZE):
                batch = list(range(start, min(start + _VISION_BATCH_SIZE, doc.page_count)))
                rendered = [self._render_page(doc, idx, want_image=client is not None) for idx in batch]
                images = [(item["page_number"], item.pop("image")) for item in rendered]

                if client is not None:
                    descriptions = self._describe_pages(client, model_name, images)
                    for item in rendered:
                        description = descriptions.get(item["page_number"], "")
                        if description:
                            item["text"] += f"\n\n[Visual & Layout Analysis]:\n{description}"

                pages.extend(rendered)
        finally:
            doc.close()

        return pages

    @staticmethod
    def _render_page(doc, page_idx: int, want_image: bool) -> Dict[str, Any]:
        """Extracts a page's text and (optionally) a 150 DPI PNG for visual layout analysis."""
        entry: Dict[str, Any] = {"text": "", "page_number": page_idx + 1, "image": None}
        try:
            page = doc[page_idx]
            entry["text"] = page.get_text()
            if want_image:
                entry["image"] = page.get_pixmap(dpi=150).tobytes("png")
        except Exception as pe:
            logger.warning("Error reading page %s: %s", page_idx + 1, pe)
        return entry

    @staticmethod
    def _describe_pages(client, model_name: str, images: List[tuple]) -> Dict[int, str]:
        """Runs Gemini visual layout analysis for a batch of rendered pages in parallel."""
        from google.genai import types

        def describe(item):
            page_number, img_bytes = item
            if not img_bytes:
                return page_number, ""
            try:
                response = retry_with_backoff(
                    client.models.generate_content,
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                        VISION_PROMPT,
                    ],
                )
                return page_number, (getattr(response, "text", None) or "")
            except Exception as ve:
                logger.warning("Failed to generate layout analysis for page %s: %s", page_number, ve)
                return page_number, ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=_VISION_BATCH_SIZE) as executor:
            return dict(executor.map(describe, images))

class DocxParser(BaseParser):
    def parse(self, file_bytes: bytes, filename: str, client = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, Any]]:
        if docx is None:
            raise ImportError("python-docx is not installed. Unable to parse Word (.docx) files.")
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"The Word document could not be opened; it may be corrupted. ({e})")
        pages: List[Dict[str, Any]] = []

        # Extract paragraphs
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        # Since Word docs don't have hardcoded physical pages,
        # we group every 10 paragraphs together to represent a "page" block
        grouped_blocks = []
        temp = []
        for idx, p in enumerate(paragraphs):
            temp.append(p)
            if (idx + 1) % 10 == 0 or (idx + 1) == len(paragraphs):
                grouped_blocks.append("\n".join(temp))
                temp = []

        for idx, text in enumerate(grouped_blocks):
            pages.append({
                "text": text,
                "page_number": idx + 1
            })
        return pages

class TextParser(BaseParser):
    def parse(self, file_bytes: bytes, filename: str, client = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, Any]]:
        text = file_bytes.decode("utf-8", errors="replace")
        return [{
            "text": text,
            "page_number": 1
        }]
