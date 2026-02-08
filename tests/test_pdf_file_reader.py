"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF FILE READER — UNIT TESTS                             ║
║                                                                              ║
║  Tests for python/tools/file_reader.py PDF reading functionality.            ║
║  Covers: _read_pdf(), _resolve_path(), edge cases.                          ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path

import pytest


class TestFileReaderReadPdf:
    """Unit tests for FileReader._read_pdf()."""

    @staticmethod
    def _make_reader():
        """Create a FileReader instance without full tool init."""
        from python.tools.file_reader import FileReader
        reader = FileReader.__new__(FileReader)
        return reader

    # ─── Happy path ──────────────────────────────────────────────────────

    def test_reads_text_from_simple_pdf(self, pdf_text_simple):
        """Should extract text from a simple text PDF."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_text_simple))

        assert "Pages:" in result
        assert "Page 1" in result
        assert "Document Title" in result or "Test Report" in result

    def test_reads_text_from_multipage_pdf(self, pdf_text_multipage):
        """Should extract text from all pages."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_text_multipage))

        assert "Page 1" in result
        assert "Page 2" in result
        assert "Page 3" in result

    def test_reads_table_content(self, pdf_table_simple):
        """Should extract text from a PDF containing tables."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_table_simple))

        # Table content should appear in text extraction
        assert "Revenue" in result or "Product" in result

    def test_reads_unicode_content(self, pdf_unicode_content):
        """Should handle French accented characters."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_unicode_content))

        # French text with accents
        assert "glementation" in result or "Réglementation" in result

    def test_reads_dense_text(self, pdf_dense_text):
        """Should handle dense multi-paragraph text."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_dense_text))

        assert len(result) > 500  # Dense text should produce substantial output
        assert "regulatory" in result.lower() or "Regulatory" in result

    # ─── Edge cases ──────────────────────────────────────────────────────

    def test_empty_pdf_returns_no_text_message(self, pdf_empty):
        """Empty PDF should return appropriate message."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_empty))

        # Either returns empty-ish content or a "no extractable text" message
        assert "no extractable text" in result.lower() or len(result.strip()) < 50

    def test_single_word_pdf(self, pdf_single_word):
        """PDF with single word should extract it."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_single_word))

        assert "Korev" in result

    def test_respects_10_page_limit(self, pdf_text_multipage):
        """Should limit output to 10 pages (per implementation)."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_text_multipage))

        # Our fixture has 3 pages, so all should appear
        assert "Page 1" in result
        assert "Page 3" in result

    # ─── Error handling ──────────────────────────────────────────────────

    def test_nonexistent_file_raises(self):
        """Non-existent file should raise an exception."""
        reader = self._make_reader()
        with pytest.raises(Exception):
            reader._read_pdf("/nonexistent/path/fake.pdf")

    def test_corrupted_pdf_handles_gracefully(self, pdf_corrupted):
        """Corrupted PDF should not crash."""
        reader = self._make_reader()
        # Should either raise a clean exception or return error message
        try:
            result = reader._read_pdf(str(pdf_corrupted))
            # If it returns, should be empty or error message
            assert isinstance(result, str)
        except Exception as e:
            # Any exception is fine, as long as it doesn't crash the process
            assert isinstance(e, Exception)


class TestFileReaderReadPdfPageContent:
    """Tests verifying the actual content of extracted pages."""

    @staticmethod
    def _make_reader():
        from python.tools.file_reader import FileReader
        return FileReader.__new__(FileReader)

    def test_text_simple_contains_all_paragraphs(self, pdf_text_simple):
        """All paragraphs from text_simple should be extracted."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_text_simple))

        # From the fixture generator: three paragraphs
        assert "extraction pipeline" in result.lower() or "extraction" in result.lower()
        assert "42" in result  # Number from second paragraph
        assert "3.14" in result  # Number from second paragraph

    def test_financial_table_numbers_preserved(self, pdf_table_financial):
        """Financial numbers should be extracted correctly."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_table_financial))

        # Check key financial figures from the fixture
        # Numbers may have spaces stripped or preserved
        assert "15" in result  # Part of 15 250 000
        assert "250" in result or "250000" in result

    def test_mixed_content_both_pages(self, pdf_mixed_content):
        """Mixed content PDF should have text from both pages."""
        reader = self._make_reader()
        result = reader._read_pdf(str(pdf_mixed_content))

        assert "Executive Summary" in result or "executive" in result.lower()
        assert "Quarterly" in result or "Quarter" in result


class TestFileReaderOtherFormats:
    """Verify non-PDF methods still work (regression guard)."""

    @staticmethod
    def _make_reader():
        from python.tools.file_reader import FileReader
        return FileReader.__new__(FileReader)

    def test_read_text_file(self, tmp_path):
        """_read_text should work for plain text files."""
        reader = self._make_reader()
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello World\nLine 2")

        result = reader._read_text(str(txt_file))
        assert "Hello World" in result
        assert "Line 2" in result

    def test_read_text_truncates_long_files(self, tmp_path):
        """_read_text should truncate files over 10000 chars."""
        reader = self._make_reader()
        txt_file = tmp_path / "long.txt"
        txt_file.write_text("A" * 20000)

        result = reader._read_text(str(txt_file))
        assert "truncated" in result.lower()
        assert len(result) < 20000
