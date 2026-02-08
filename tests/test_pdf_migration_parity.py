"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF MIGRATION PARITY TESTS                                ║
║                                                                              ║
║  PURPOSE: Verify that PdfPlumberBackend produces equivalent results          ║
║  to PyMuPDFBackend on all test fixtures.                                     ║
║                                                                              ║
║  These tests run BOTH backends on the same PDFs and compare:                 ║
║  - Page count (must be identical)                                            ║
║  - Text content (90%+ word overlap)                                          ║
║  - Word count (within 15% tolerance)                                         ║
║  - Word positions (approximate — different engines have slight offsets)       ║
║  - Page dimensions (must be identical)                                       ║
║                                                                              ║
║  PASS CRITERIA:                                                              ║
║  - These tests passing = safe to switch backend                              ║
║  - These tests failing = investigate before switching                        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pathlib import Path

import pytest

from python.helpers.pdf_extraction.pdf_backend import (
    PDFBackend,
    PDFDocument,
    PDFWord,
    PyMuPDFBackend,
    PdfPlumberBackend,
)
from tests.fixtures.pdf_generator import list_fixtures, get_fixture_path

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

_VALID_FIXTURES = [f for f in list_fixtures() if f != "corrupted"]


@pytest.fixture(scope="module")
def pymupdf_backend() -> PyMuPDFBackend:
    return PyMuPDFBackend()


@pytest.fixture(scope="module")
def pdfplumber_backend() -> PdfPlumberBackend:
    return PdfPlumberBackend()


# ═══════════════════════════════════════════════════════════════════════════════
# A) PAGE COUNT PARITY (must be exact)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPageCountParity:
    """Page counts must be IDENTICAL between backends."""

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_page_count_matches(self, fixture_name, pymupdf_backend, pdfplumber_backend):
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_count = old_doc.page_count()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_count = new_doc.page_count()

        assert old_count == new_count, (
            f"{fixture_name}: page count mismatch — "
            f"PyMuPDF={old_count}, PdfPlumber={new_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# B) PAGE DIMENSIONS PARITY (must be exact or very close)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPageDimensionsParity:
    """Page dimensions must match closely between backends."""

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_page_dimensions_match(self, fixture_name, pymupdf_backend, pdfplumber_backend):
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            with pdfplumber_backend.open(str(pdf_path)) as new_doc:
                for i in range(old_doc.page_count()):
                    old_page = old_doc.get_page(i)
                    new_page = new_doc.get_page(i)

                    assert abs(old_page.width - new_page.width) < 1.0, (
                        f"{fixture_name} page {i}: width mismatch — "
                        f"PyMuPDF={old_page.width:.1f}, PdfPlumber={new_page.width:.1f}"
                    )
                    assert abs(old_page.height - new_page.height) < 1.0, (
                        f"{fixture_name} page {i}: height mismatch — "
                        f"PyMuPDF={old_page.height:.1f}, PdfPlumber={new_page.height:.1f}"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# C) TEXT CONTENT PARITY (90%+ word overlap)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTextContentParity:
    """Text content must have high word overlap between backends."""

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_text_word_overlap(self, fixture_name, pymupdf_backend, pdfplumber_backend):
        """At least 90% of words from PyMuPDF should appear in PdfPlumber output."""
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_text = old_doc.get_full_text()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_text = new_doc.get_full_text()

        old_words = set(old_text.lower().split())
        new_words = set(new_text.lower().split())

        if not old_words:
            # Empty PDF — both should be empty
            assert not new_words, (
                f"{fixture_name}: PyMuPDF found no words but PdfPlumber found {len(new_words)}"
            )
            return

        overlap = len(old_words & new_words) / len(old_words)
        assert overlap >= 0.90, (
            f"{fixture_name}: only {overlap:.1%} word overlap "
            f"(PyMuPDF={len(old_words)} words, PdfPlumber={len(new_words)} words, "
            f"common={len(old_words & new_words)})\n"
            f"Missing in PdfPlumber: {sorted(old_words - new_words)[:20]}"
        )

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_per_page_text_present(self, fixture_name, pymupdf_backend, pdfplumber_backend):
        """Every page with text in PyMuPDF should have text in PdfPlumber."""
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            with pdfplumber_backend.open(str(pdf_path)) as new_doc:
                for i in range(old_doc.page_count()):
                    old_page = old_doc.get_page(i)
                    new_page = new_doc.get_page(i)

                    old_has_text = len(old_page.text.strip()) > 0
                    new_has_text = len(new_page.text.strip()) > 0

                    if old_has_text:
                        assert new_has_text, (
                            f"{fixture_name} page {i}: PyMuPDF has text but PdfPlumber doesn't"
                        )


# ═══════════════════════════════════════════════════════════════════════════════
# D) WORD COUNT PARITY (within tolerance)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWordCountParity:
    """Word counts should be within 15% tolerance."""

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_total_word_count_within_tolerance(
        self, fixture_name, pymupdf_backend, pdfplumber_backend
    ):
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_words = old_doc.get_all_words()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_words = new_doc.get_all_words()

        old_count = len(old_words)
        new_count = len(new_words)

        if old_count == 0:
            assert new_count == 0, (
                f"{fixture_name}: PyMuPDF found 0 words but PdfPlumber found {new_count}"
            )
            return

        ratio = new_count / old_count
        assert 0.85 <= ratio <= 1.15, (
            f"{fixture_name}: word count ratio {ratio:.2f} out of tolerance "
            f"(PyMuPDF={old_count}, PdfPlumber={new_count})"
        )

    @pytest.mark.parametrize("fixture_name", _VALID_FIXTURES)
    def test_per_page_word_count_within_tolerance(
        self, fixture_name, pymupdf_backend, pdfplumber_backend
    ):
        """Per-page word counts should be within 20% tolerance."""
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            with pdfplumber_backend.open(str(pdf_path)) as new_doc:
                for i in range(old_doc.page_count()):
                    old_page = old_doc.get_page(i)
                    new_page = new_doc.get_page(i)

                    old_count = len(old_page.words)
                    new_count = len(new_page.words)

                    if old_count == 0:
                        assert new_count <= 5, (
                            f"{fixture_name} page {i}: empty page has {new_count} words"
                        )
                        continue

                    ratio = new_count / old_count
                    assert 0.80 <= ratio <= 1.20, (
                        f"{fixture_name} page {i}: word count ratio {ratio:.2f} "
                        f"(PyMuPDF={old_count}, PdfPlumber={new_count})"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# E) WORD POSITION PARITY (approximate)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWordPositionParity:
    """Word positions should be approximately similar."""

    @pytest.mark.parametrize("fixture_name", ["text_simple", "single_word", "table_simple"])
    def test_first_word_position_approximate(
        self, fixture_name, pymupdf_backend, pdfplumber_backend
    ):
        """First word on first page should be in approximately the same position."""
        pdf_path = get_fixture_path(fixture_name)

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_page = old_doc.get_page(0)

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_page = new_doc.get_page(0)

        if not old_page.words or not new_page.words:
            return  # Skip if no words

        old_first = old_page.words[0]
        new_first = new_page.words[0]

        # Same text (case-insensitive)
        assert old_first.text.lower() == new_first.text.lower(), (
            f"{fixture_name}: first word mismatch — "
            f"PyMuPDF='{old_first.text}', PdfPlumber='{new_first.text}'"
        )

        # Position within 20 points (different engines have offset)
        assert abs(old_first.x0 - new_first.x0) < 20, (
            f"{fixture_name}: x0 offset too large "
            f"(PyMuPDF={old_first.x0:.1f}, PdfPlumber={new_first.x0:.1f})"
        )
        assert abs(old_first.y0 - new_first.y0) < 20, (
            f"{fixture_name}: y0 offset too large "
            f"(PyMuPDF={old_first.y0:.1f}, PdfPlumber={new_first.y0:.1f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# F) SPECIFIC CONTENT PARITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpecificContentParity:
    """Verify specific content is preserved across backends."""

    def test_numbers_preserved(self, pymupdf_backend, pdfplumber_backend):
        """Numbers in text_simple should be in both backends."""
        pdf_path = get_fixture_path("text_simple")
        numbers = ["42", "3.14", "1000000", "100.50"]

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_text = old_doc.get_full_text()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_text = new_doc.get_full_text()

        for num in numbers:
            if num in old_text:
                assert num in new_text, (
                    f"Number '{num}' found in PyMuPDF but missing in PdfPlumber"
                )

    def test_french_accents_preserved(self, pymupdf_backend, pdfplumber_backend):
        """French accented characters must be preserved."""
        pdf_path = get_fixture_path("unicode_content")

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_text = old_doc.get_full_text()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_text = new_doc.get_full_text()

        # Key French words with accents
        accented_words = ["société", "intérêt", "activité"]
        for word in accented_words:
            if word in old_text.lower():
                assert word in new_text.lower(), (
                    f"French word '{word}' found in PyMuPDF but missing in PdfPlumber"
                )

    def test_financial_figures_preserved(self, pymupdf_backend, pdfplumber_backend):
        """Key financial figures should appear in both backends."""
        pdf_path = get_fixture_path("table_financial")

        with pymupdf_backend.open(str(pdf_path)) as old_doc:
            old_text = old_doc.get_full_text()

        with pdfplumber_backend.open(str(pdf_path)) as new_doc:
            new_text = new_doc.get_full_text()

        # Key numbers from the financial fixture
        key_figures = ["15", "250", "10.5"]
        for fig in key_figures:
            if fig in old_text:
                assert fig in new_text, (
                    f"Financial figure '{fig}' found in PyMuPDF but missing in PdfPlumber"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# G) BACKEND INTERFACE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackendInterface:
    """Test the PDFBackend abstraction layer itself."""

    def test_pymupdf_backend_name(self):
        assert PyMuPDFBackend().name == "pymupdf"

    def test_pdfplumber_backend_name(self):
        assert PdfPlumberBackend().name == "pdfplumber"

    def test_factory_returns_pymupdf(self):
        from python.helpers.pdf_extraction.pdf_backend import get_backend
        backend = get_backend("pymupdf")
        assert isinstance(backend, PyMuPDFBackend)

    def test_factory_returns_pdfplumber(self):
        from python.helpers.pdf_extraction.pdf_backend import get_backend
        backend = get_backend("pdfplumber")
        assert isinstance(backend, PdfPlumberBackend)

    def test_factory_unknown_raises(self):
        from python.helpers.pdf_extraction.pdf_backend import get_backend
        with pytest.raises(ValueError, match="Unknown PDF backend"):
            get_backend("nonexistent")

    def test_context_manager_pymupdf(self, pdf_text_simple):
        """Context manager should work for PyMuPDF."""
        backend = PyMuPDFBackend()
        with backend.open(str(pdf_text_simple)) as doc:
            assert doc.page_count() > 0

    def test_context_manager_pdfplumber(self, pdf_text_simple):
        """Context manager should work for PdfPlumber."""
        backend = PdfPlumberBackend()
        with backend.open(str(pdf_text_simple)) as doc:
            assert doc.page_count() > 0

    def test_open_bytes_pymupdf(self, pdf_text_simple):
        """Should open from bytes."""
        backend = PyMuPDFBackend()
        data = pdf_text_simple.read_bytes()
        with backend.open(data) as doc:
            assert doc.page_count() > 0

    def test_open_bytes_pdfplumber(self, pdf_text_simple):
        """Should open from bytes."""
        backend = PdfPlumberBackend()
        data = pdf_text_simple.read_bytes()
        with backend.open(data) as doc:
            assert doc.page_count() > 0

    def test_get_all_words_helper(self, pdf_text_simple):
        """get_all_words convenience method should work."""
        backend = PdfPlumberBackend()
        with backend.open(str(pdf_text_simple)) as doc:
            words = doc.get_all_words()
            assert len(words) > 0
            for w in words:
                assert isinstance(w, PDFWord)

    def test_get_full_text_helper(self, pdf_text_simple):
        """get_full_text convenience method should work."""
        backend = PdfPlumberBackend()
        with backend.open(str(pdf_text_simple)) as doc:
            text = doc.get_full_text()
            assert len(text) > 0

    def test_max_pages_limit(self, pdf_text_multipage):
        """max_pages parameter should limit extraction."""
        backend = PdfPlumberBackend()
        with backend.open(str(pdf_text_multipage)) as doc:
            all_words = doc.get_all_words()
            limited_words = doc.get_all_words(max_pages=1)

            assert len(limited_words) < len(all_words)
            assert all(w.page == 0 for w in limited_words)


# ═══════════════════════════════════════════════════════════════════════════════
# H) ERROR HANDLING PARITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorHandlingParity:
    """Both backends should handle errors similarly."""

    def test_corrupted_pdf_both_raise(self):
        """Corrupted PDF should raise in both backends."""
        pdf_path = get_fixture_path("corrupted")

        with pytest.raises(Exception):
            with PyMuPDFBackend().open(str(pdf_path)) as doc:
                doc.get_page(0)

        with pytest.raises(Exception):
            with PdfPlumberBackend().open(str(pdf_path)) as doc:
                doc.get_page(0)

    def test_empty_bytes_both_raise(self):
        """Empty bytes should raise in both backends."""
        with pytest.raises(Exception):
            PyMuPDFBackend().open_bytes(b"")

        with pytest.raises(Exception):
            PdfPlumberBackend().open_bytes(b"")
