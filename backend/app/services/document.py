import io
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Graceful docx import
try:
    import docx
except ImportError:
    docx = None

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
        Extracts raw text and visual layout details from file bytes.
        Returns a list of dicts: [{"text": str, "page_number": int}]
        """
        ext = filename.split(".")[-1].lower()
        pages: List[Dict[str, Any]] = []

        if ext == "pdf":
            import fitz  # PyMuPDF
            import concurrent.futures
            
            # Open PDF from memory stream
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            def process_single_page(page_idx: int) -> Dict[str, Any]:
                try:
                    # Open a thread-local copy or use the main doc safely
                    # (fitz page reads are generally safe if not modifying the structure)
                    page = doc[page_idx]
                    raw_text = page.get_text()
                    visual_description = ""
                    
                    if self.client:
                        try:
                            from google.genai import types
                            # Render page as a pixmap at 150 DPI for balance of detail and performance
                            pix = page.get_pixmap(dpi=150)
                            img_bytes = pix.tobytes("png")
                            
                            # Request visual OCR, table markdown conversion, and image descriptors
                            response = self.client.models.generate_content(
                                model=self.model_name,
                                contents=[
                                    types.Part.from_bytes(
                                        data=img_bytes,
                                        mime_type='image/png'
                                    ),
                                    "Extract and describe all structural elements on this page. If there are tables, transcribe them in markdown format. If there are charts or diagrams, describe them in detail. If there are headers, signatures, or handwriting, mention them."
                                ]
                            )
                            if response.text:
                                visual_description = f"\n\n[Visual & Layout Analysis]:\n{response.text}"
                        except Exception as ve:
                            print(f"Failed to generate layout analysis for page {page_idx+1}: {ve}")
                    
                    return {
                        "text": raw_text + visual_description,
                        "page_number": page_idx + 1
                    }
                except Exception as pe:
                    print(f"Error processing page {page_idx+1}: {pe}")
                    return {"text": "", "page_number": page_idx + 1}
            
            # Use ThreadPoolExecutor to run page layout API calls in parallel (max 8 concurrent threads)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                # Map maintains page order
                results = list(executor.map(process_single_page, range(doc.page_count)))
                
            pages.extend(results)
            doc.close()

            
        elif ext == "docx":
            if docx is None:
                raise ImportError("python-docx is not installed. Unable to parse Word (.docx) files.")
            doc = docx.Document(io.BytesIO(file_bytes))
            
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
                
        elif ext in ["txt", "md", "markdown"]:
            text = file_bytes.decode("utf-8", errors="ignore")
            # TXT and Markdown files are ingested as a single page (Page 1)
            pages.append({
                "text": text,
                "page_number": 1
            })
            
        else:
            raise ValueError(f"Unsupported file format: .{ext}")
        
        return pages

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
