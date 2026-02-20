"""
PDF OCR Tool — Extract text from scanned PDFs using Tesseract OCR.

This tool handles the complexity of OCR automatically:
1. Detects if PDF is scanned (image-based)
2. Converts pages to images
3. Runs OCR on each page
4. Returns extracted text
"""

import os
import tempfile
from python.helpers.tool import Tool, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle


class PdfOcr(Tool):
    """
    OCR tool for scanned PDFs.
    Automatically detects and processes image-based PDFs.
    """

    async def execute(self, **kwargs) -> Response:
        file_path = self.args.get("path", "")
        max_pages = int(self.args.get("max_pages", 10))
        language = self.args.get("language", "eng+fra")  # English + French by default
        
        if not file_path:
            return Response(
                message="Error: 'path' argument is required.",
                break_loop=False
            )
        
        # Resolve path
        abs_path = self._resolve_path(file_path)
        
        if not os.path.exists(abs_path):
            return Response(
                message=f"Error: File not found: {file_path}\n"
                        f"Available files:\n{self._list_uploads()}",
                break_loop=False
            )
        
        PrintStyle(font_color="cyan").print(f"[PDF OCR] Processing: {abs_path}")
        
        try:
            # First try direct text extraction
            text = self._extract_text_direct(abs_path)
            
            if len(text.strip()) > 50:
                # PDF has selectable text, no OCR needed
                PrintStyle(font_color="green").print("[PDF OCR] Text extracted directly (not scanned)")
                return Response(
                    message=f"**PDF Text Extraction** (direct, not scanned)\n"
                            f"File: {os.path.basename(abs_path)}\n\n{text}",
                    break_loop=False
                )
            
            # PDF is likely scanned, use OCR
            PrintStyle(font_color="yellow").print("[PDF OCR] PDF appears scanned, running OCR...")
            
            ocr_text = self._run_ocr(abs_path, max_pages, language)
            
            if not ocr_text.strip():
                return Response(
                    message="Warning: OCR produced no text. The PDF may be:\n"
                            "- Very low quality\n"
                            "- In an unsupported language\n"
                            "- Not actually containing text",
                    break_loop=False
                )
            
            PrintStyle(font_color="green").print(f"[PDF OCR] Extracted {len(ocr_text)} characters")
            
            return Response(
                message=f"**PDF OCR Extraction**\n"
                        f"File: {os.path.basename(abs_path)}\n"
                        f"Pages processed: up to {max_pages}\n"
                        f"Language: {language}\n\n"
                        f"--- Extracted Text ---\n{ocr_text}",
                break_loop=False
            )
            
        except Exception as e:
            return Response(
                message=f"Error during OCR: {e}",
                break_loop=False
            )
    
    def _resolve_path(self, path: str) -> str:
        """Resolve file path to absolute."""
        if os.path.isabs(path):
            return path
        
        # Check in uploads
        uploads = files.get_abs_path("tmp/uploads")
        candidate = os.path.join(uploads, os.path.basename(path))
        if os.path.exists(candidate):
            return candidate
        
        # Check relative to work dir
        return files.get_abs_path(path)
    
    def _list_uploads(self) -> str:
        """List PDF files in uploads folder."""
        uploads = files.get_abs_path("tmp/uploads")
        if not os.path.exists(uploads):
            return "(no uploads folder)"
        
        pdf_files = [f for f in os.listdir(uploads) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return "(no PDF files)"
        
        return "\n".join(f"- {f}" for f in sorted(pdf_files)[:15])
    
    def _extract_text_direct(self, path: str) -> str:
        """Try to extract text directly using pypdf (BSD license)."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)

            return "\n\n".join(text_parts)

        except ImportError:
            return ""
        except Exception:
            return ""
    
    def _run_ocr(self, path: str, max_pages: int, language: str) -> str:
        """Run OCR on PDF pages using centralized OCREngine."""
        try:
            from python.helpers.pdf_extraction.ocr_engine import OCREngine

            engine = OCREngine()
            adaptive_dpi = engine.select_dpi(page_count=max_pages)

            PrintStyle(font_color="cyan").print(
                f"[PDF OCR] Running OCR (max {max_pages} pages, DPI={adaptive_dpi})..."
            )

            results = engine.run_ocr_on_pdf(
                path,
                language=language,
                max_pages=max_pages,
                dpi=adaptive_dpi,
                total_timeout_s=120.0,
            )

            text_parts = []
            for result in results:
                if result.text.strip():
                    conf_pct = f"{result.confidence * 100:.0f}%"
                    text_parts.append(
                        f"--- Page {result.page + 1} "
                        f"(confidence: {conf_pct}, DPI: {result.dpi_used}) ---\n"
                        f"{result.text}"
                    )

            return "\n\n".join(text_parts)

        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else str(e)
            return f"Error: Missing library '{missing}'. Install with: pip install {missing}"
        except Exception as e:
            return f"OCR Error: {e}"
