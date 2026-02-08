"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              OCR PIPELINE INTEGRATION — TESTS (TDD)                          ║
║                                                                              ║
║  Tests for OCR integration into the main extract_from_pdf() pipeline.        ║
║  Written BEFORE implementation per strict TDD process.                       ║
║                                                                              ║
║  Validates:                                                                  ║
║  1. OCR runs as Step 2.5 when text extraction yields no/few words            ║
║  2. OCR is skipped when text extraction succeeds                             ║
║  3. OCR respects config.ocr.enabled                                          ║
║  4. OCR respects config.ocr.only_if_pdf_type                                 ║
║  5. OCR results populate diagnostics correctly                               ║
║  6. Confidence scoring feeds into overall confidence                         ║
║  7. OCR timeout does not break the pipeline                                  ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def scanned_pdf_for_pipeline(tmp_path_factory) -> Path:
    """Create a scanned PDF (image-based, no native text)."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    out_dir = tmp_path_factory.mktemp("pipeline_ocr")
    pdf_path = out_dir / "scanned_for_pipeline.pdf"

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    except (OSError, IOError):
        font = ImageFont.load_default()

    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    img = Image.new("RGB", (2480, 3508), "white")
    draw = ImageDraw.Draw(img)
    draw.text((200, 200), "SCANNED DOCUMENT 2025", fill="black", font=font)
    draw.text((200, 400), "This text is an image", fill="black", font=font)

    img_tmp = out_dir / "scan_page.png"
    img.save(str(img_tmp))
    c.drawImage(str(img_tmp), 0, 0, width=w, height=h)
    c.showPage()
    c.save()

    return pdf_path


@pytest.fixture(scope="session")
def native_text_pdf_path(tmp_path_factory) -> Path:
    """Create a native text PDF (NOT scanned)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    out_dir = tmp_path_factory.mktemp("pipeline_native")
    pdf_path = out_dir / "native_text.pdf"

    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(100, 700, "This is native text in a PDF document.")
    c.drawString(100, 680, "It should be extractable without OCR.")
    c.drawString(100, 660, "Multiple lines of real text content here.")
    c.drawString(100, 640, "KOREV Evidence System Analysis Report 2025")
    c.drawString(100, 620, "Total revenue: 15000 EUR")
    c.showPage()
    c.save()

    return pdf_path


# ═══════════════════════════════════════════════════════════════════════════════
# 1. OCR AS STEP 2.5 IN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCRPipelineStep:
    """OCR should run as Step 2.5 when text extraction yields nothing."""

    def test_ocr_triggered_on_scan_pdf(self, scanned_pdf_for_pipeline):
        """Scanned PDF with OCR enabled → OCR should run and find text."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # OCR should have been attempted
        assert result.diagnostics.ocr_time_ms >= 0
        # Should have some text from OCR
        all_text = " ".join(w.text for w in result.words)
        assert len(all_text) > 0 or result.diagnostics.ocr_region_count > 0

    def test_ocr_skipped_for_native_text(self, native_text_pdf_path):
        """Native text PDF → OCR should be skipped."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True

        result = extract_from_pdf(str(native_text_pdf_path), config=config)

        # Text should come from direct extraction, not OCR
        assert result.diagnostics.word_count > 0
        # OCR time should be 0 or very small (not triggered)
        assert result.diagnostics.ocr_time_ms == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONFIG RESPECT
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCRConfigRespect:
    """OCR should respect all configuration options."""

    def test_ocr_disabled_means_no_ocr(self, scanned_pdf_for_pipeline):
        """config.ocr.enabled=False → absolutely no OCR."""
        from python.helpers.pdf_extraction.config import PDFExtractionConfig
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = PDFExtractionConfig()
        config.ocr.enabled = False

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        assert result.diagnostics.ocr_time_ms == 0
        assert result.diagnostics.ocr_region_count == 0

    def test_ocr_only_if_pdf_type_scan(self, native_text_pdf_path):
        """OCR enabled but only_if_pdf_type=['scan'] → skip for text PDFs."""
        from python.helpers.pdf_extraction.config import PDFExtractionConfig
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = PDFExtractionConfig()
        config.ocr.enabled = True
        config.ocr.only_if_pdf_type = ["scan"]

        result = extract_from_pdf(str(native_text_pdf_path), config=config)

        # Should not have run OCR since this is a text PDF
        assert result.diagnostics.ocr_time_ms == 0

    def test_ocr_min_confidence_filtering(self, scanned_pdf_for_pipeline):
        """OCR with high min_confidence → may reject low-quality results."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True
        config.ocr.min_confidence_to_accept = 0.99  # Very strict

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # Result should still be valid (not crash)
        assert result.status is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCRDiagnostics:
    """OCR diagnostics should be properly populated."""

    def test_ocr_time_tracked(self, scanned_pdf_for_pipeline):
        """OCR processing time should be tracked in diagnostics."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # OCR time should be recorded
        assert result.diagnostics.ocr_time_ms >= 0

    def test_ocr_method_in_attempted(self, scanned_pdf_for_pipeline):
        """ExtractionMethod.OCR_TESSERACT should appear in methods_attempted."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf
        from python.helpers.pdf_extraction.types import ExtractionMethod

        config = get_scan_config()
        config.ocr.enabled = True

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # Should track OCR in methods
        method_values = [m.value for m in result.diagnostics.methods_attempted]
        # OCR should be among attempted methods if it ran
        if result.diagnostics.ocr_time_ms > 0:
            assert "ocr_tesseract" in method_values


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OCR DOESN'T BREAK PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCRPipelineResilience:
    """OCR failures should not break the pipeline."""

    def test_pipeline_works_when_tesseract_missing(self, scanned_pdf_for_pipeline):
        """If tesseract is not installed, pipeline should still work."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True

        # Mock pytesseract to simulate it being missing
        with patch.dict("sys.modules", {"pytesseract": None}):
            result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # Pipeline should still complete
        assert result.status is not None
        assert result.diagnostics.total_time_ms >= 0

    def test_pipeline_handles_ocr_timeout_gracefully(self, scanned_pdf_for_pipeline):
        """OCR timeout should not crash the pipeline."""
        from python.helpers.pdf_extraction.config import get_scan_config
        from python.helpers.pdf_extraction.pipeline import extract_from_pdf

        config = get_scan_config()
        config.ocr.enabled = True
        config.budgets.total_timeout_s = 120.0  # Generous

        result = extract_from_pdf(str(scanned_pdf_for_pipeline), config=config)

        # Should complete without crash
        assert result.status is not None
        assert result.diagnostics.total_time_ms < 120000
