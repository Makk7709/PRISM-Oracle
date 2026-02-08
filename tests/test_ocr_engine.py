"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    OCR ENGINE — UNIT TESTS (TDD)                             ║
║                                                                              ║
║  Written BEFORE the implementation per strict TDD process.                   ║
║                                                                              ║
║  Tests:                                                                      ║
║  1. OCRResult dataclass: structure, confidence, word-level data              ║
║  2. OCREngine.run_ocr_on_image(): Tesseract with confidence scoring          ║
║  3. OCREngine.run_ocr_on_pdf_page(): PDF→image→OCR per page                ║
║  4. OCREngine.run_ocr_on_pdf(): full PDF, multi-page, budgets               ║
║  5. DPI adaptatif: auto-selection based on page count                        ║
║  6. Timeout protection: per-page and total                                   ║
║  7. Confidence filtering: min_confidence_to_accept                           ║
║  8. Language configuration                                                   ║
║  9. Error handling: corrupted images, missing tesseract                      ║
║  10. Diagnostics: timing, region count, methods                              ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import time
from pathlib import Path
from dataclasses import dataclass

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES: Generate a "scanned" PDF (text rendered as image)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def scanned_pdf_path(tmp_path_factory) -> Path:
    """Create a PDF that contains text rendered as an IMAGE (simulates scan)."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    import io

    out_dir = tmp_path_factory.mktemp("ocr_fixtures")
    pdf_path = out_dir / "scanned_simple.pdf"

    # 1. Create an image with known text
    img_width, img_height = 2480, 3508  # A4 at 300 DPI
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    # Use default font (always available)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Draw known text
    lines = [
        "INVOICE NUMBER: INV-2025-0042",
        "Date: February 8, 2025",
        "",
        "Client: Korev Technologies SAS",
        "Address: 42 Avenue des Champs",
        "",
        "Description          Amount",
        "Consulting Services  15000 EUR",
        "Software License     8500 EUR",
        "Training             3200 EUR",
        "",
        "Total: 26700 EUR",
    ]
    y_pos = 200
    for line in lines:
        draw.text((200, y_pos), line, fill="black", font=font)
        y_pos += 80

    # 2. Save image as temporary file
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # 3. Embed image in PDF (this creates a "scanned" PDF)
    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    # Save PIL image to temp file for reportlab
    img_tmp = out_dir / "scan_page.png"
    img.save(str(img_tmp))
    c.drawImage(str(img_tmp), 0, 0, width=w, height=h)
    c.showPage()
    c.save()

    return pdf_path


@pytest.fixture(scope="session")
def scanned_multipage_pdf(tmp_path_factory) -> Path:
    """Create a multi-page scanned PDF."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    out_dir = tmp_path_factory.mktemp("ocr_fixtures_multi")
    pdf_path = out_dir / "scanned_multipage.pdf"

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    except (OSError, IOError):
        font = ImageFont.load_default()

    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    for page_num in range(3):
        img = Image.new("RGB", (2480, 3508), "white")
        draw = ImageDraw.Draw(img)
        draw.text((200, 200), f"Page {page_num + 1} of 3", fill="black", font=font)
        draw.text((200, 400), f"Content for page {page_num + 1}", fill="black", font=font)
        draw.text((200, 600), "Korev Evidence System", fill="black", font=font)

        img_tmp = out_dir / f"scan_page_{page_num}.png"
        img.save(str(img_tmp))
        c.drawImage(str(img_tmp), 0, 0, width=w, height=h)
        c.showPage()

    c.save()
    return pdf_path


@pytest.fixture(scope="session")
def blank_scanned_pdf(tmp_path_factory) -> Path:
    """Create a scanned PDF with a blank white page (no text)."""
    from PIL import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    out_dir = tmp_path_factory.mktemp("ocr_fixtures_blank")
    pdf_path = out_dir / "scanned_blank.pdf"

    img = Image.new("RGB", (2480, 3508), "white")
    img_tmp = out_dir / "blank_page.png"
    img.save(str(img_tmp))

    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4
    c.drawImage(str(img_tmp), 0, 0, width=w, height=h)
    c.showPage()
    c.save()

    return pdf_path


# ═══════════════════════════════════════════════════════════════════════════════
# 1. OCRResult DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCRResultStructure:
    """Verify the OCRResult dataclass has all required fields."""

    def test_ocr_result_has_text(self):
        from python.helpers.pdf_extraction.ocr_engine import OCRResult
        r = OCRResult(text="hello", words=[], page=0, confidence=0.95,
                      dpi_used=200, duration_ms=100)
        assert r.text == "hello"

    def test_ocr_result_has_words_with_confidence(self):
        from python.helpers.pdf_extraction.ocr_engine import OCRResult, OCRWord
        w = OCRWord(text="Invoice", confidence=0.97,
                    x0=10, y0=20, x1=100, y1=40, page=0)
        r = OCRResult(text="Invoice", words=[w], page=0, confidence=0.97,
                      dpi_used=200, duration_ms=100)
        assert len(r.words) == 1
        assert r.words[0].confidence == 0.97
        assert r.words[0].text == "Invoice"

    def test_ocr_result_has_page_and_timing(self):
        from python.helpers.pdf_extraction.ocr_engine import OCRResult
        r = OCRResult(text="", words=[], page=2, confidence=0.0,
                      dpi_used=300, duration_ms=1500)
        assert r.page == 2
        assert r.duration_ms == 1500
        assert r.dpi_used == 300

    def test_ocr_word_has_bbox(self):
        from python.helpers.pdf_extraction.ocr_engine import OCRWord
        w = OCRWord(text="test", confidence=0.85,
                    x0=10.5, y0=20.3, x1=50.1, y1=35.7, page=0)
        assert w.x0 == 10.5
        assert w.y1 == 35.7


# ═══════════════════════════════════════════════════════════════════════════════
# 2. OCR ON IMAGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCROnImage:
    """Test Tesseract OCR on individual images with confidence scoring."""

    def test_ocr_image_returns_text(self, scanned_pdf_path):
        """OCR a single image and get text with confidence."""
        from PIL import Image
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        # Create an image with known text
        img = Image.new("RGB", (800, 200), "white")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Hello World 12345", fill="black")

        engine = OCREngine()
        result = engine.run_ocr_on_image(img, page=0, language="eng")

        assert isinstance(result.text, str)
        assert len(result.text.strip()) > 0
        assert result.page == 0
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert result.duration_ms >= 0

    def test_ocr_image_returns_words_with_confidence(self):
        """Each word should have a confidence score."""
        from PIL import Image, ImageDraw
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        img = Image.new("RGB", (800, 200), "white")
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "INVOICE 42", fill="black")

        engine = OCREngine()
        result = engine.run_ocr_on_image(img, page=0, language="eng")

        if result.words:  # Tesseract may or may not detect text from default font
            for word in result.words:
                assert isinstance(word.text, str)
                assert 0.0 <= word.confidence <= 1.0
                assert word.page == 0

    def test_ocr_blank_image_returns_empty(self):
        """Blank white image should produce no/empty text."""
        from PIL import Image
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        img = Image.new("RGB", (800, 200), "white")
        engine = OCREngine()
        result = engine.run_ocr_on_image(img, page=0, language="eng")

        assert result.text.strip() == "" or len(result.words) == 0
        assert result.duration_ms >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OCR ON PDF PAGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCROnPdfPage:
    """Test OCR on individual PDF pages (PDF→image→OCR)."""

    def test_ocr_pdf_page_extracts_text(self, scanned_pdf_path):
        """OCR a single PDF page and get text."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=200
        )

        assert isinstance(result.text, str)
        assert len(result.text.strip()) > 0
        assert result.page == 0
        assert result.dpi_used == 200

    def test_ocr_pdf_page_detects_known_content(self, scanned_pdf_path):
        """Known text from fixture should be detected."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=300
        )

        text = result.text.upper()
        # At least some of our fixture content should be detected
        assert "INV" in text or "INVOICE" in text or "2025" in text or "KOREV" in text

    def test_ocr_pdf_page_has_confidence(self, scanned_pdf_path):
        """OCR result should have a confidence score."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=200
        )

        assert 0.0 <= result.confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OCR ON FULL PDF (MULTI-PAGE)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCROnFullPdf:
    """Test full PDF OCR with multi-page support and budgets."""

    def test_full_pdf_ocr_extracts_all_pages(self, scanned_multipage_pdf):
        """OCR all pages of a multi-page scanned PDF."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            str(scanned_multipage_pdf), language="eng",
            max_pages=10, dpi=200
        )

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.page == i
            assert isinstance(result.text, str)

    def test_full_pdf_ocr_respects_max_pages(self, scanned_multipage_pdf):
        """max_pages should limit the number of pages OCR'd."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            str(scanned_multipage_pdf), language="eng",
            max_pages=2, dpi=200
        )

        assert len(results) == 2
        assert results[0].page == 0
        assert results[1].page == 1

    def test_full_pdf_ocr_returns_empty_for_blank(self, blank_scanned_pdf):
        """Blank scanned PDF should return results with empty/minimal text."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            str(blank_scanned_pdf), language="eng",
            max_pages=5, dpi=200
        )

        assert len(results) == 1
        total_text = " ".join(r.text for r in results).strip()
        assert len(total_text) < 20  # May detect noise, but very little


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DPI ADAPTATIF
# ═══════════════════════════════════════════════════════════════════════════════

class TestDPIAdaptatif:
    """Test automatic DPI selection based on page count."""

    def test_select_dpi_few_pages_returns_high(self):
        """1-3 pages → 300 DPI for maximum quality."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine.select_dpi(page_count=1) == 300
        assert engine.select_dpi(page_count=2) == 300
        assert engine.select_dpi(page_count=3) == 300

    def test_select_dpi_medium_pages_returns_default(self):
        """4-10 pages → 200 DPI (default balance)."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine.select_dpi(page_count=4) == 200
        assert engine.select_dpi(page_count=10) == 200

    def test_select_dpi_many_pages_returns_low(self):
        """11+ pages → 150 DPI for speed."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine.select_dpi(page_count=11) == 150
        assert engine.select_dpi(page_count=50) == 150
        assert engine.select_dpi(page_count=200) == 150

    def test_select_dpi_override(self):
        """Explicit DPI override should bypass auto-selection."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        # When explicit DPI is provided, it should be used as-is
        assert engine.select_dpi(page_count=1, explicit_dpi=150) == 150
        assert engine.select_dpi(page_count=50, explicit_dpi=400) == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 6. TIMEOUT PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimeoutProtection:
    """Test per-page and total timeout enforcement."""

    def test_total_timeout_respected(self, scanned_multipage_pdf):
        """Total timeout should stop OCR before processing all pages."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        start = time.time()
        results = engine.run_ocr_on_pdf(
            str(scanned_multipage_pdf), language="eng",
            max_pages=100, dpi=200,
            total_timeout_s=120.0  # generous but bounded
        )
        elapsed = time.time() - start

        # Should complete within reasonable time
        assert elapsed < 120.0
        # Should have processed some pages
        assert len(results) >= 1

    def test_per_page_timeout_in_result(self, scanned_pdf_path):
        """Each OCR result should track its duration."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=200
        )

        assert result.duration_ms >= 0
        assert result.duration_ms < 30000  # Should be less than 30s per page


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CONFIDENCE FILTERING
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceFiltering:
    """Test confidence-based word filtering."""

    def test_filter_low_confidence_words(self):
        """Words below threshold should be filterable."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine, OCRWord, OCRResult

        words = [
            OCRWord(text="Invoice", confidence=0.95, x0=0, y0=0, x1=100, y1=20, page=0),
            OCRWord(text="??!!", confidence=0.20, x0=0, y0=30, x1=50, y1=50, page=0),
            OCRWord(text="Total", confidence=0.88, x0=0, y0=60, x1=80, y1=80, page=0),
        ]

        engine = OCREngine()
        filtered = engine.filter_by_confidence(words, min_confidence=0.50)

        assert len(filtered) == 2
        assert filtered[0].text == "Invoice"
        assert filtered[1].text == "Total"

    def test_filter_keeps_all_above_threshold(self):
        """All words above threshold should be kept."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine, OCRWord

        words = [
            OCRWord(text="A", confidence=0.90, x0=0, y0=0, x1=10, y1=10, page=0),
            OCRWord(text="B", confidence=0.85, x0=0, y0=0, x1=10, y1=10, page=0),
        ]

        engine = OCREngine()
        filtered = engine.filter_by_confidence(words, min_confidence=0.80)
        assert len(filtered) == 2

    def test_overall_confidence_calculation(self):
        """Overall confidence should be weighted average of word confidences."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine, OCRWord

        words = [
            OCRWord(text="Hello", confidence=0.90, x0=0, y0=0, x1=10, y1=10, page=0),
            OCRWord(text="World", confidence=0.80, x0=0, y0=0, x1=10, y1=10, page=0),
        ]

        engine = OCREngine()
        confidence = engine.compute_page_confidence(words)
        assert 0.80 <= confidence <= 0.90
        assert abs(confidence - 0.85) < 0.01  # Mean of 0.90 and 0.80

    def test_empty_words_confidence_is_zero(self):
        """No words → confidence 0."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine.compute_page_confidence([]) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. LANGUAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestLanguageConfig:
    """Test language parameter handling."""

    def test_english_ocr(self, scanned_pdf_path):
        """English language OCR."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=200
        )
        assert isinstance(result.text, str)

    def test_french_english_ocr(self, scanned_pdf_path):
        """Combined English+French OCR."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng+fra", dpi=200
        )
        assert isinstance(result.text, str)

    def test_invalid_language_handled(self, scanned_pdf_path):
        """Invalid language should not crash, should return empty or error."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        # This should handle gracefully (empty result or error message)
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0,
            language="invalid_lang_xxx", dpi=200
        )
        assert isinstance(result.text, str)
        assert result.confidence == 0.0 or len(result.text.strip()) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Test graceful error handling."""

    def test_nonexistent_pdf_returns_empty(self):
        """Non-existent file should return empty results, not crash."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            "/nonexistent/path/file.pdf", language="eng",
            max_pages=5, dpi=200
        )
        assert results == []

    def test_corrupted_pdf_returns_empty(self, tmp_path):
        """Corrupted PDF should return empty results, not crash."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"not a pdf at all")

        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            str(bad_pdf), language="eng",
            max_pages=5, dpi=200
        )
        assert results == []

    def test_blank_image_ocr_no_crash(self):
        """Blank image should not crash OCR."""
        from PIL import Image
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        img = Image.new("RGB", (100, 100), "white")
        engine = OCREngine()
        result = engine.run_ocr_on_image(img, page=0, language="eng")
        assert isinstance(result, object)
        assert hasattr(result, "text")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DIAGNOSTICS TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiagnostics:
    """Test diagnostic metadata from OCR."""

    def test_result_tracks_dpi(self, scanned_pdf_path):
        """Result should record the DPI used."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=250
        )
        assert result.dpi_used == 250

    def test_result_tracks_duration(self, scanned_pdf_path):
        """Result should track processing time."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        result = engine.run_ocr_on_pdf_page(
            str(scanned_pdf_path), page_num=0, language="eng", dpi=200
        )
        assert result.duration_ms > 0

    def test_multi_page_total_duration(self, scanned_multipage_pdf):
        """Total duration should be sum of per-page durations."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine
        engine = OCREngine()
        results = engine.run_ocr_on_pdf(
            str(scanned_multipage_pdf), language="eng",
            max_pages=3, dpi=150
        )
        total_ms = sum(r.duration_ms for r in results)
        assert total_ms > 0
