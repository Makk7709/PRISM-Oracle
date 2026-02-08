"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              markdown_pdf SHIM — VALIDATION TESTS                            ║
║                                                                              ║
║  Verifies that our MIT-licensed markdown_pdf shim correctly replaces the     ║
║  AGPL-licensed markdown-pdf package for browser-use compatibility.           ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import tempfile
from pathlib import Path

import pytest


class TestShimImport:
    """Verify the shim is importable with the correct API."""

    def test_import_markdown_pdf(self):
        from markdown_pdf import MarkdownPdf, Section
        assert MarkdownPdf is not None
        assert Section is not None

    def test_section_accepts_content(self):
        from markdown_pdf import Section
        s = Section("# Title\n\nBody text.")
        assert s.content == "# Title\n\nBody text."

    def test_section_default_empty(self):
        from markdown_pdf import Section
        s = Section()
        assert s.content == ""


class TestPdfGeneration:
    """Verify the shim generates valid PDF files."""

    def test_simple_markdown_to_pdf(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section("# Hello\n\nWorld"))
        out = tmp_path / "test.pdf"
        mp.save(out)
        assert out.exists()
        assert out.stat().st_size > 100
        # Verify it's a real PDF
        header = out.read_bytes()[:5]
        assert header == b"%PDF-"

    def test_empty_content_generates_pdf(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section(""))
        out = tmp_path / "empty.pdf"
        mp.save(out)
        assert out.exists()
        assert out.stat().st_size > 50

    def test_multiple_sections(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section("# Section 1\n\nContent A"))
        mp.add_section(Section("## Section 2\n\nContent B"))
        mp.add_section(Section("### Section 3\n\nContent C"))
        out = tmp_path / "multi.pdf"
        mp.save(out)
        assert out.exists()
        assert out.stat().st_size > 200

    def test_bold_italic_code(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section(
            "**Bold** and *italic* and `code` text.\n\n"
            "A paragraph with **nested *emphasis***."
        ))
        out = tmp_path / "styled.pdf"
        mp.save(out)
        assert out.exists()

    def test_horizontal_rule(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section("Above\n\n---\n\nBelow"))
        out = tmp_path / "hr.pdf"
        mp.save(out)
        assert out.exists()

    def test_creates_parent_dirs(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section("Content"))
        out = tmp_path / "deep" / "nested" / "dir" / "file.pdf"
        mp.save(out)
        assert out.exists()

    def test_unicode_content(self, tmp_path):
        from markdown_pdf import MarkdownPdf, Section
        mp = MarkdownPdf()
        mp.add_section(Section("# Résumé Exécutif\n\nL'intérêt général prévaut."))
        out = tmp_path / "french.pdf"
        mp.save(out)
        assert out.exists()
        assert out.stat().st_size > 100


class TestBrowserUseCompatibility:
    """Verify the shim works as a drop-in for browser-use's PdfFile."""

    def test_browser_use_file_system_imports(self):
        """browser_use.filesystem.file_system should import without errors."""
        from browser_use.filesystem.file_system import PdfFile, FileSystem
        assert PdfFile is not None
        assert FileSystem is not None

    def test_browser_use_pdf_file_writes(self, tmp_path):
        """PdfFile.sync_to_disk_sync should produce a valid PDF."""
        from browser_use.filesystem.file_system import PdfFile
        pdf = PdfFile(name="report")
        pdf.content = "# Quarterly Report\n\nRevenue: **€2.3M**\n\nGrowth: +12%"
        pdf.sync_to_disk_sync(tmp_path)
        result = tmp_path / "report.pdf"
        assert result.exists()
        assert result.read_bytes()[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_browser_use_pdf_file_async(self, tmp_path):
        """PdfFile.sync_to_disk (async) should also work."""
        from browser_use.filesystem.file_system import PdfFile
        pdf = PdfFile(name="async_report")
        pdf.content = "# Async Test\n\nContent here."
        await pdf.sync_to_disk(tmp_path)
        result = tmp_path / "async_report.pdf"
        assert result.exists()


class TestNoAgplDependency:
    """Verify PyMuPDF (AGPL) is NOT loaded."""

    def test_fitz_not_importable(self):
        """fitz (PyMuPDF) should NOT be importable after uninstall."""
        import importlib
        import importlib.util
        spec = importlib.util.find_spec("fitz")
        assert spec is None, "fitz (PyMuPDF AGPL) should NOT be installed!"

    def test_pymupdf_not_importable(self):
        """pymupdf should NOT be importable."""
        import importlib
        import importlib.util
        spec = importlib.util.find_spec("pymupdf")
        assert spec is None, "pymupdf (AGPL) should NOT be installed!"

    def test_pymupdf4llm_not_importable(self):
        """pymupdf4llm should NOT be importable."""
        import importlib
        import importlib.util
        spec = importlib.util.find_spec("pymupdf4llm")
        assert spec is None, "pymupdf4llm (AGPL) should NOT be installed!"
