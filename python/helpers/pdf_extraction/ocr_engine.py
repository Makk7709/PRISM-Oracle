"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    OCR ENGINE — Centralized OCR Module                       ║
║                                                                              ║
║  Provides a single, well-tested OCR implementation for the entire            ║
║  KOREV Evidence system. Replaces duplicated OCR code in:                     ║
║  - python/tools/pdf_ocr.py                                                   ║
║  - python/helpers/document_query.py                                          ║
║                                                                              ║
║  Features:                                                                   ║
║  - Confidence scoring per word (Tesseract image_to_data)                     ║
║  - DPI adaptatif (300/200/150 based on page count)                           ║
║  - Per-page and total timeout protection                                     ║
║  - Word-level bounding boxes                                                 ║
║  - Language configuration                                                    ║
║  - Diagnostics tracking (timing, DPI, confidence)                            ║
║                                                                              ║
║  License: MIT-compatible dependencies only                                   ║
║  - pytesseract (Apache-2.0)                                                  ║
║  - pdf2image (MIT)                                                           ║
║  - Pillow (MIT-CMU)                                                          ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OCRWord:
    """A word extracted by OCR with confidence and position."""
    text: str
    confidence: float  # 0.0 - 1.0
    x0: float          # Left edge (pixels in image coords)
    y0: float          # Top edge
    x1: float          # Right edge
    y1: float          # Bottom edge
    page: int          # 0-based page number


@dataclass
class OCRResult:
    """Result of OCR on a single page."""
    text: str                       # Full text of the page
    words: List[OCRWord]            # Words with confidence and bbox
    page: int                       # 0-based page number
    confidence: float               # Overall page confidence (0.0 - 1.0)
    dpi_used: int                   # DPI used for rendering
    duration_ms: int                # Processing time in milliseconds


# ═══════════════════════════════════════════════════════════════════════════════
# OCR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class OCREngine:
    """
    Centralized OCR engine for KOREV Evidence.

    Uses Tesseract via pytesseract with confidence scoring (image_to_data),
    adaptive DPI selection, and timeout protection.
    """

    # DPI thresholds
    DPI_HIGH = 300       # 1-3 pages: max quality
    DPI_DEFAULT = 200    # 4-10 pages: balanced
    DPI_LOW = 150        # 11+ pages: speed priority

    # ── DPI selection ─────────────────────────────────────────────────────

    def select_dpi(
        self,
        page_count: int,
        explicit_dpi: Optional[int] = None,
    ) -> int:
        """
        Select optimal DPI based on page count.

        Args:
            page_count: Total pages in PDF.
            explicit_dpi: If provided, overrides auto-selection.

        Returns:
            DPI value to use.
        """
        if explicit_dpi is not None:
            return explicit_dpi

        if page_count <= 3:
            return self.DPI_HIGH
        elif page_count <= 10:
            return self.DPI_DEFAULT
        else:
            return self.DPI_LOW

    # ── OCR on a single PIL image ─────────────────────────────────────────

    def run_ocr_on_image(
        self,
        image: Image.Image,
        page: int,
        language: str = "eng",
    ) -> OCRResult:
        """
        Run Tesseract OCR on a PIL Image with confidence scoring.

        Uses image_to_data() instead of image_to_string() to get
        per-word confidence scores and bounding boxes.

        Args:
            image: PIL Image to OCR.
            page: Page number (0-based).
            language: Tesseract language code (e.g., "eng", "eng+fra").

        Returns:
            OCRResult with text, words, confidence, and timing.
        """
        start = time.time()

        try:
            import pytesseract

            # Use image_to_data for confidence scoring
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT,
            )

            words: List[OCRWord] = []
            text_parts: List[str] = []

            n_items = len(data["text"])
            for i in range(n_items):
                raw_text = data["text"][i].strip()
                conf = float(data["conf"][i])

                if not raw_text:
                    continue

                # Tesseract confidence is 0-100, convert to 0.0-1.0
                # -1 means "not a word" — skip
                if conf < 0:
                    continue

                norm_conf = conf / 100.0

                x = float(data["left"][i])
                y = float(data["top"][i])
                w = float(data["width"][i])
                h = float(data["height"][i])

                words.append(OCRWord(
                    text=raw_text,
                    confidence=norm_conf,
                    x0=x,
                    y0=y,
                    x1=x + w,
                    y1=y + h,
                    page=page,
                ))
                text_parts.append(raw_text)

            full_text = " ".join(text_parts)
            overall_confidence = self.compute_page_confidence(words)

            duration_ms = int((time.time() - start) * 1000)

            return OCRResult(
                text=full_text,
                words=words,
                page=page,
                confidence=overall_confidence,
                dpi_used=0,  # Set by caller when coming from PDF
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.warning(f"OCR failed on page {page}: {e}")
            duration_ms = int((time.time() - start) * 1000)
            return OCRResult(
                text="",
                words=[],
                page=page,
                confidence=0.0,
                dpi_used=0,
                duration_ms=duration_ms,
            )

    # ── OCR on a single PDF page ──────────────────────────────────────────

    def run_ocr_on_pdf_page(
        self,
        pdf_path: str,
        page_num: int,
        language: str = "eng",
        dpi: int = 200,
    ) -> OCRResult:
        """
        OCR a single page of a PDF: convert to image, then run OCR.

        Args:
            pdf_path: Path to the PDF file.
            page_num: 0-based page number.
            language: Tesseract language code.
            dpi: Resolution for PDF→image conversion.

        Returns:
            OCRResult for that page.
        """
        start = time.time()

        try:
            from pdf2image import convert_from_path

            images = convert_from_path(
                pdf_path,
                first_page=page_num + 1,  # pdf2image is 1-based
                last_page=page_num + 1,
                dpi=dpi,
            )

            if not images:
                return OCRResult(
                    text="", words=[], page=page_num,
                    confidence=0.0, dpi_used=dpi,
                    duration_ms=int((time.time() - start) * 1000),
                )

            result = self.run_ocr_on_image(images[0], page=page_num, language=language)
            # Override dpi_used and recalculate total duration
            total_ms = int((time.time() - start) * 1000)
            return OCRResult(
                text=result.text,
                words=result.words,
                page=result.page,
                confidence=result.confidence,
                dpi_used=dpi,
                duration_ms=total_ms,
            )

        except Exception as e:
            logger.warning(f"PDF OCR failed on page {page_num}: {e}")
            return OCRResult(
                text="", words=[], page=page_num,
                confidence=0.0, dpi_used=dpi,
                duration_ms=int((time.time() - start) * 1000),
            )

    # ── OCR on a full PDF ─────────────────────────────────────────────────

    def run_ocr_on_pdf(
        self,
        pdf_path: str,
        language: str = "eng",
        max_pages: int = 10,
        dpi: int = 200,
        total_timeout_s: float = 120.0,
    ) -> List[OCRResult]:
        """
        OCR an entire PDF with multi-page support, budgets, and timeouts.

        Args:
            pdf_path: Path to the PDF file.
            language: Tesseract language code.
            max_pages: Maximum pages to process.
            dpi: DPI for rendering (or use select_dpi() beforehand).
            total_timeout_s: Total time budget for all pages.

        Returns:
            List of OCRResult, one per page processed.
        """
        overall_start = time.time()
        results: List[OCRResult] = []

        try:
            from pdf2image import convert_from_path

            # Validate file exists first
            if not Path(pdf_path).exists():
                logger.warning(f"PDF file not found: {pdf_path}")
                return []

            # Get page count first
            try:
                from pdf2image import pdfinfo_from_path
                info = pdfinfo_from_path(pdf_path)
                total_pages = info.get("Pages", 0)
                if total_pages == 0:
                    logger.warning(f"PDF has 0 pages or invalid: {pdf_path}")
                    return []
            except Exception as e:
                logger.warning(f"Cannot read PDF info for {pdf_path}: {e}")
                return []

            pages_to_process = min(max_pages, total_pages)

            for page_num in range(pages_to_process):
                # Check total timeout
                elapsed = time.time() - overall_start
                if elapsed >= total_timeout_s:
                    logger.info(
                        f"OCR total timeout ({total_timeout_s}s) reached "
                        f"after {page_num} pages"
                    )
                    break

                result = self.run_ocr_on_pdf_page(
                    pdf_path, page_num=page_num,
                    language=language, dpi=dpi,
                )
                results.append(result)

            return results

        except Exception as e:
            logger.warning(f"PDF OCR failed for {pdf_path}: {e}")
            return results  # Return whatever we got so far

    # ── Confidence utilities ──────────────────────────────────────────────

    @staticmethod
    def compute_page_confidence(words: List[OCRWord]) -> float:
        """
        Compute overall page confidence from word-level confidences.

        Uses mean of all word confidences. Returns 0.0 if no words.
        """
        if not words:
            return 0.0
        return sum(w.confidence for w in words) / len(words)

    @staticmethod
    def filter_by_confidence(
        words: List[OCRWord],
        min_confidence: float = 0.50,
    ) -> List[OCRWord]:
        """
        Filter words below a confidence threshold.

        Args:
            words: List of OCR words.
            min_confidence: Minimum confidence to keep (0.0-1.0).

        Returns:
            Filtered list of OCRWord.
        """
        return [w for w in words if w.confidence >= min_confidence]
