"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF BACKEND ABSTRACTION LAYER                             ║
║                                                                              ║
║  Decouples the extraction pipeline from any specific PDF library.            ║
║                                                                              ║
║  Provides:                                                                   ║
║  - PDFBackend (abstract interface)                                           ║
║  - PyMuPDFBackend (current, AGPL — to be removed)                           ║
║  - PdfPlumberBackend (replacement, MIT)                                      ║
║  - get_backend() factory function                                            ║
║                                                                              ║
║  Migration strategy:                                                         ║
║  1. Both backends implement the same interface                               ║
║  2. Parity tests verify equivalent output                                    ║
║  3. Switch default backend once parity confirmed                             ║
║  4. Remove PyMuPDFBackend + pymupdf dependency                              ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES (backend-agnostic)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PDFWord:
    """A word extracted from a PDF page with position."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    confidence: float = 1.0


@dataclass(frozen=True)
class PDFImage:
    """Metadata about an image in a PDF page."""
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float


@dataclass
class PDFPage:
    """A single page from a PDF document."""
    page_num: int
    width: float
    height: float
    text: str
    words: list[PDFWord]
    images: list[PDFImage]


# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class PDFDocument(ABC):
    """Abstract PDF document. Provides page-level access."""

    @abstractmethod
    def page_count(self) -> int:
        """Return the number of pages."""
        ...

    @abstractmethod
    def get_page(self, page_num: int) -> PDFPage:
        """
        Get a page by number (0-indexed).
        
        Returns a PDFPage with text, words (with positions), and image metadata.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release resources."""
        ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_all_words(self, max_pages: Optional[int] = None) -> list[PDFWord]:
        """Get words from all pages (convenience method)."""
        words = []
        limit = min(self.page_count(), max_pages) if max_pages else self.page_count()
        for i in range(limit):
            page = self.get_page(i)
            words.extend(page.words)
        return words

    def get_full_text(self, max_pages: Optional[int] = None) -> str:
        """Get text from all pages (convenience method)."""
        parts = []
        limit = min(self.page_count(), max_pages) if max_pages else self.page_count()
        for i in range(limit):
            page = self.get_page(i)
            if page.text.strip():
                parts.append(page.text)
        return "\n\n".join(parts)


class PDFBackend(ABC):
    """
    Abstract PDF backend factory.
    
    Implementations must be able to open PDFs from file paths or bytes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging/diagnostics."""
        ...

    @abstractmethod
    def open_path(self, path: Union[str, Path]) -> PDFDocument:
        """Open a PDF from a file path."""
        ...

    @abstractmethod
    def open_bytes(self, data: bytes) -> PDFDocument:
        """Open a PDF from bytes."""
        ...

    def open(self, source: Union[str, Path, bytes]) -> PDFDocument:
        """Open a PDF from path or bytes (convenience method)."""
        if isinstance(source, bytes):
            return self.open_bytes(source)
        return self.open_path(source)


# ═══════════════════════════════════════════════════════════════════════════════
# IMPLEMENTATION: PyMuPDF (fitz)
# STATUS: Current backend — AGPL licensed, to be removed after migration
# ═══════════════════════════════════════════════════════════════════════════════

class PyMuPDFDocument(PDFDocument):
    """PDF document backed by PyMuPDF (fitz)."""

    def __init__(self, doc):
        self._doc = doc

    def page_count(self) -> int:
        return self._doc.page_count

    def get_page(self, page_num: int) -> PDFPage:
        page = self._doc[page_num]

        # Extract text
        text = page.get_text("text")

        # Extract words: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        raw_words = page.get_text("words", sort=True)
        words = []
        for w in raw_words:
            if len(w) >= 5:
                word_text = w[4]
                word_text = " ".join(word_text.split())  # normalize whitespace
                if word_text:
                    words.append(PDFWord(
                        text=word_text,
                        x0=w[0],
                        y0=w[1],
                        x1=w[2],
                        y1=w[3],
                        page=page_num,
                        confidence=1.0,
                    ))

        # Extract image metadata
        images = []
        for img in page.get_images():
            try:
                xref = img[0]
                img_rect = page.get_image_bbox(xref)
                if img_rect:
                    images.append(PDFImage(
                        x0=img_rect.x0,
                        y0=img_rect.y0,
                        x1=img_rect.x1,
                        y1=img_rect.y1,
                        width=img_rect.width,
                        height=img_rect.height,
                    ))
            except Exception:
                pass

        return PDFPage(
            page_num=page_num,
            width=page.rect.width,
            height=page.rect.height,
            text=text,
            words=words,
            images=images,
        )

    def close(self) -> None:
        self._doc.close()


class PyMuPDFBackend(PDFBackend):
    """PyMuPDF backend. AGPL licensed — migration target for removal."""

    @property
    def name(self) -> str:
        return "pymupdf"

    def open_path(self, path: Union[str, Path]) -> PDFDocument:
        import fitz
        return PyMuPDFDocument(fitz.open(str(path)))

    def open_bytes(self, data: bytes) -> PDFDocument:
        import fitz
        return PyMuPDFDocument(fitz.open(stream=data, filetype="pdf"))


# ═══════════════════════════════════════════════════════════════════════════════
# IMPLEMENTATION: pdfplumber + pypdf
# STATUS: Replacement backend — MIT licensed
# ═══════════════════════════════════════════════════════════════════════════════

class PdfPlumberDocument(PDFDocument):
    """PDF document backed by pdfplumber (MIT)."""

    def __init__(self, pdf):
        self._pdf = pdf

    def page_count(self) -> int:
        return len(self._pdf.pages)

    def get_page(self, page_num: int) -> PDFPage:
        page = self._pdf.pages[page_num]

        # Extract text
        text = page.extract_text() or ""

        # Extract words with positions
        raw_words = page.extract_words() or []
        words = []
        for w in raw_words:
            word_text = w.get("text", "")
            word_text = " ".join(word_text.split())  # normalize whitespace
            if word_text:
                words.append(PDFWord(
                    text=word_text,
                    x0=float(w.get("x0", 0)),
                    y0=float(w.get("top", 0)),
                    x1=float(w.get("x1", 0)),
                    y1=float(w.get("bottom", 0)),
                    page=page_num,
                    confidence=1.0,
                ))

        # Extract image metadata
        images = []
        for img in (page.images or []):
            images.append(PDFImage(
                x0=float(img.get("x0", 0)),
                y0=float(img.get("top", 0)),
                x1=float(img.get("x1", 0)),
                y1=float(img.get("bottom", 0)),
                width=float(img.get("x1", 0)) - float(img.get("x0", 0)),
                height=float(img.get("bottom", 0)) - float(img.get("top", 0)),
            ))

        return PDFPage(
            page_num=page_num,
            width=float(page.width),
            height=float(page.height),
            text=text,
            words=words,
            images=images,
        )

    def close(self) -> None:
        self._pdf.close()


class PdfPlumberBackend(PDFBackend):
    """pdfplumber backend. MIT licensed — migration target."""

    @property
    def name(self) -> str:
        return "pdfplumber"

    def open_path(self, path: Union[str, Path]) -> PDFDocument:
        import pdfplumber
        return PdfPlumberDocument(pdfplumber.open(str(path)))

    def open_bytes(self, data: bytes) -> PDFDocument:
        import pdfplumber
        return PdfPlumberDocument(pdfplumber.open(io.BytesIO(data)))


# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

# Default backend — switched to pdfplumber (MIT) to remove AGPL dependency
_DEFAULT_BACKEND = "pdfplumber"

_BACKENDS: dict[str, type[PDFBackend]] = {
    "pymupdf": PyMuPDFBackend,
    "pdfplumber": PdfPlumberBackend,
}


def get_backend(name: Optional[str] = None) -> PDFBackend:
    """
    Get a PDF backend by name.
    
    Args:
        name: Backend name ("pymupdf" or "pdfplumber"). 
              If None, uses the default.
    
    Returns:
        PDFBackend instance.
    """
    name = name or _DEFAULT_BACKEND
    if name not in _BACKENDS:
        raise ValueError(
            f"Unknown PDF backend: {name}. "
            f"Available: {list(_BACKENDS.keys())}"
        )
    return _BACKENDS[name]()


def set_default_backend(name: str) -> None:
    """
    Set the default PDF backend.
    
    Args:
        name: Backend name ("pymupdf" or "pdfplumber").
    """
    global _DEFAULT_BACKEND
    if name not in _BACKENDS:
        raise ValueError(f"Unknown backend: {name}")
    _DEFAULT_BACKEND = name
    logger.info("PDF backend switched to: %s", name)
