import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.parsers import PDFParser, DocxParser, TextParser

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
                print(f"Failed to initialize Gemini Client in DocumentProcessor: {e}")

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
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
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

    async def process_file(self, file_bytes: bytes, filename: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Asynchronously processes an uploaded file.
        Extracts, cleans, chunks, and attaches metadata.
        Returns list of chunks.
        """
        raw_pages = self.extract_text(file_bytes, filename)
        ext = filename.split(".")[-1].lower()
        upload_time = datetime.utcnow().isoformat()
        
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
