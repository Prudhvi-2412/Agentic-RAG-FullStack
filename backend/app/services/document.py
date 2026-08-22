import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.parsers import PDFParser, DocxParser, TextParser

logger = logging.getLogger(__name__)

# Unicode control characters that corrupt prompts/metadata. Printable non-ASCII text
# (accents, CJK, Indic scripts) must be preserved.
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

class DocumentProcessor:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        """
        Initializes the DocumentProcessor. If api_key is supplied, enables
        multimodal visual layout analysis for scanned/complex PDF documents.
        """
        self.api_key = api_key
        self.model_name = model_name.replace("models/", "")
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Gemini Client in DocumentProcessor: %s", e)

        # High-quality semantic RAG splitting parameters
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=750,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        # Register parser strategies
        self.parsers = {
            "pdf": PDFParser(),
            "docx": DocxParser(),
            "txt": TextParser(),
            "md": TextParser(),
            "markdown": TextParser()
        }

    def clean_text(self, text: str) -> str:
        """
        Cleans text content by normalizing whitespace and removing control characters.
        """
        if not text:
            return ""
        
        # Replace multiple whitespace characters/newlines with a single space
        text = re.sub(r'\s+', ' ', text)

        # Remove non-printable control characters
        text = _CONTROL_CHARS.sub('', text)

        return text.strip()

    def extract_text(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extracts raw text and visual layout details from file bytes using the registered parser.
        """
        ext = filename.split(".")[-1].lower()
        if ext not in self.parsers:
            raise ValueError(f"Unsupported file format: .{ext}")
            
        parser = self.parsers[ext]
        return parser.parse(file_bytes, filename, client=self.client, model_name=self.model_name)

    def process_file(self, file_bytes: bytes, filename: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Processes an uploaded file: extracts, cleans, chunks, and attaches metadata.

        This is CPU-bound (PDF rasterisation) and makes blocking network calls, so callers
        must run it off the event loop (see `asyncio.to_thread` in the upload route).
        """
        raw_pages = self.extract_text(file_bytes, filename)
        ext = filename.split(".")[-1].lower()
        upload_time = datetime.now(timezone.utc).isoformat()
        
        chunks: List[Dict[str, Any]] = []
        
        for page in raw_pages:
            cleaned_text = self.clean_text(page["text"])
            if not cleaned_text or len(cleaned_text) < 10:
                continue
            
            # Split the page's text into smaller semantic pieces
            splits = self.text_splitter.split_text(cleaned_text)
            for split_idx, split_text in enumerate(splits):
                chunk_id = f"{document_id}_p{page['page_number']}_c{split_idx}"
                chunks.append({
                    "id": chunk_id,
                    "text": split_text,
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_id": chunk_id,
                        "upload_time": upload_time,
                        "page_number": page["page_number"],
                        "source_type": ext
                    }
                })
                
        return chunks
