import io
import concurrent.futures
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.core.retry import retry_with_backoff

# Graceful docx import
try:
    import docx
except ImportError:
    docx = None

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
        pages: List[Dict[str, Any]] = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        def process_single_page(page_idx: int) -> Dict[str, Any]:
            try:
                page = doc[page_idx]
                raw_text = page.get_text()
                visual_description = ""
                
                if client:
                    try:
                        from google.genai import types
                        # Render page as a pixmap at 150 DPI for balance of detail and performance
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        
                        # Request visual OCR, table markdown conversion, and image descriptors with retry backoff
                        response = retry_with_backoff(
                            client.models.generate_content,
                            model=model_name,
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
        return pages

class DocxParser(BaseParser):
    def parse(self, file_bytes: bytes, filename: str, client = None, model_name: str = "gemini-2.5-flash") -> List[Dict[str, Any]]:
        if docx is None:
            raise ImportError("python-docx is not installed. Unable to parse Word (.docx) files.")
        doc = docx.Document(io.BytesIO(file_bytes))
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
        text = file_bytes.decode("utf-8", errors="ignore")
        return [{
            "text": text,
            "page_number": 1
        }]
