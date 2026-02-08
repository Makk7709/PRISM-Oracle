"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF OCR TOOL — UNIT TESTS                                ║
║                                                                              ║
║  Tests for python/tools/pdf_ocr.py                                           ║
║  Covers: _extract_text_direct(), _resolve_path(), edge cases.               ║
║                                                                              ║
║  NOTE: Actual OCR (_run_ocr) is NOT tested here — it requires               ║
║  tesseract + pdf2image which may not be available in all envs.              ║
║  Only the PyMuPDF-based direct extraction path is tested.                   ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path

import pytest


class TestPdfOcrDirectExtraction:
    """Tests for PdfOcr._extract_text_direct() — the PyMuPDF path."""

    @staticmethod
    def _make_ocr():
        """Create PdfOcr instance without full tool init."""
        from python.tools.pdf_ocr import PdfOcr
        return PdfOcr.__new__(PdfOcr)

    # ─── Happy path ──────────────────────────────────────────────────────

    def test_extracts_text_from_simple_pdf(self, pdf_text_simple):
        """Should extract text from simple PDF."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_text_simple))

        assert len(result) > 100
        assert "extraction" in result.lower() or "test" in result.lower()

    def test_extracts_text_from_multipage(self, pdf_text_multipage):
        """Should extract text from all pages."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_text_multipage))

        # Should have content from multiple pages
        assert "Chapter" in result or "paragraph" in result.lower()
        assert len(result) > 500

    def test_extracts_unicode_text(self, pdf_unicode_content):
        """Should handle French accented characters."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_unicode_content))

        assert len(result) > 100
        # Check for French content
        assert "article" in result.lower() or "code" in result.lower()

    def test_extracts_table_text(self, pdf_table_simple):
        """Should extract text from table cells."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_table_simple))

        # Table cell values should appear
        assert "Product" in result or "Revenue" in result or "Alpha" in result

    # ─── Edge cases ──────────────────────────────────────────────────────

    def test_empty_pdf_returns_empty_string(self, pdf_empty):
        """Empty PDF should return empty or very short string."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_empty))

        assert len(result.strip()) == 0

    def test_single_word_pdf(self, pdf_single_word):
        """Single word PDF should extract the word."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_single_word))

        assert "Korev" in result

    def test_dense_text_produces_substantial_output(self, pdf_dense_text):
        """Dense text should produce significant output."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_dense_text))

        assert len(result) > 1000

    # ─── Error handling ──────────────────────────────────────────────────

    def test_nonexistent_file_returns_empty(self):
        """Non-existent file should return empty string (graceful fail)."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct("/nonexistent/path/fake.pdf")

        # Implementation returns "" on any exception
        assert result == ""

    def test_corrupted_pdf_returns_empty(self, pdf_corrupted):
        """Corrupted PDF should return empty string."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_corrupted))

        assert result == ""


class TestPdfOcrResolvePath:
    """Tests for PdfOcr._resolve_path()."""

    @staticmethod
    def _make_ocr():
        from python.tools.pdf_ocr import PdfOcr
        return PdfOcr.__new__(PdfOcr)

    def test_absolute_path_returned_as_is(self, pdf_text_simple):
        """Absolute paths should be returned unchanged."""
        ocr = self._make_ocr()
        result = ocr._resolve_path(str(pdf_text_simple))
        assert os.path.isabs(result)

    def test_relative_path_resolved(self, tmp_path):
        """Relative paths should be resolved against work dir or uploads."""
        ocr = self._make_ocr()
        # Just test that it returns a string without crashing
        result = ocr._resolve_path("some_file.pdf")
        assert isinstance(result, str)


class TestPdfOcrContentAccuracy:
    """Verify content accuracy of direct extraction."""

    @staticmethod
    def _make_ocr():
        from python.tools.pdf_ocr import PdfOcr
        return PdfOcr.__new__(PdfOcr)

    def test_numbers_preserved(self, pdf_text_simple):
        """Numbers in text should be preserved exactly."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_text_simple))

        assert "42" in result
        assert "3.14" in result

    def test_financial_numbers_extracted(self, pdf_table_financial):
        """Financial table numbers should be in extracted text."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_table_financial))

        # Key financial figures from fixture
        assert "15" in result  # Part of financial figures
        assert "%" in result  # Percentage signs

    def test_multipage_content_merged(self, pdf_text_multipage):
        """Text from all pages should be joined."""
        ocr = self._make_ocr()
        result = ocr._extract_text_direct(str(pdf_text_multipage))

        # Content from different pages
        assert "Chapter 1" in result or "Page 1" in result.lower()
        assert "Chapter 3" in result or "Page 3" in result.lower() or "Chapter" in result


class TestPdfOcrListUploads:
    """Tests for PdfOcr._list_uploads()."""

    @staticmethod
    def _make_ocr():
        from python.tools.pdf_ocr import PdfOcr
        return PdfOcr.__new__(PdfOcr)

    def test_returns_string_when_no_uploads(self):
        """Should return a string even when uploads dir doesn't exist."""
        ocr = self._make_ocr()
        result = ocr._list_uploads()
        assert isinstance(result, str)
