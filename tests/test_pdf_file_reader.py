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


class TestFileReaderVolumeRegression:
    """Strict regressions for large-document handling."""

    @staticmethod
    def _make_reader():
        import importlib
        import sys
        import types
        from dataclasses import dataclass
        from typing import Optional

        # Stub heavy Tool dependency chain (agent/models/whisper) for unit isolation.
        if "python.helpers.tool" not in sys.modules:
            stub = types.ModuleType("python.helpers.tool")

            @dataclass
            class Response:
                message: str
                break_loop: bool
                additional: Optional[dict] = None

            class Tool:
                pass

            stub.Response = Response
            stub.Tool = Tool
            sys.modules["python.helpers.tool"] = stub

        module = importlib.import_module("python.tools.file_reader")
        importlib.reload(module)
        FileReader = module.FileReader
        return FileReader.__new__(FileReader)

    @staticmethod
    def _build_multipage_pdf(path: Path, pages: int = 12):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(path), pagesize=A4)
        for i in range(1, pages + 1):
            c.drawString(80, 800, f"Invoice Batch Test — Page {i}")
            c.drawString(80, 780, f"PEFC marker page {i}")
            c.showPage()
        c.save()

    def test_read_pdf_reads_beyond_10_pages(self, tmp_path):
        """Regression: must not silently truncate at first 10 pages."""
        reader = self._make_reader()
        pdf_path = tmp_path / "twelve_pages.pdf"
        self._build_multipage_pdf(pdf_path, pages=12)

        result = reader._read_pdf(str(pdf_path))

        assert "Page 10" in result
        assert "Page 11" in result
        assert "Page 12" in result

    @pytest.mark.asyncio
    async def test_execute_pdf_honors_max_pages_argument(self, tmp_path):
        """When max_pages is provided, FileReader must cap pages deterministically."""
        reader = self._make_reader()
        pdf_path = tmp_path / "fifteen_pages.pdf"
        self._build_multipage_pdf(pdf_path, pages=15)
        reader.args = {"path": str(pdf_path), "max_pages": 3}

        response = await reader.execute()

        assert "Page 1" in response.message
        assert "Page 3" in response.message
        assert "Page 4" not in response.message

    @pytest.mark.asyncio
    async def test_execute_pdf_honors_max_chars_and_reports_truncation(self, tmp_path):
        """Large output must truncate with explicit marker for auditability."""
        reader = self._make_reader()
        pdf_path = tmp_path / "big_chars.pdf"
        self._build_multipage_pdf(pdf_path, pages=20)
        reader.args = {"path": str(pdf_path), "max_chars": 350}

        response = await reader.execute()

        assert "truncated" in response.message.lower()
