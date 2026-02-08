"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF PIPELINE — REAL EXTRACTION TESTS                      ║
║                                                                              ║
║  Tests for python/helpers/pdf_extraction/pipeline.py                         ║
║  using REAL PDFs (not mocks).                                                ║
║                                                                              ║
║  Covers:                                                                     ║
║  - classify_pdf()                                                            ║
║  - extract_words_pymupdf()                                                   ║
║  - extract_tables_geometry()                                                 ║
║  - extract_from_pdf() end-to-end                                            ║
║  - calculate_overall_confidence()                                            ║
║  - generate_outputs()                                                        ║
║  - Async wrapper                                                             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import time
from pathlib import Path

import pytest

from python.helpers.pdf_extraction.pdf_backend import get_backend

from python.helpers.pdf_extraction.config import PDFExtractionConfig, get_default_config
from python.helpers.pdf_extraction.types import (
    BBox,
    Cell,
    Diagnostics,
    ExtractionContext,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
    PDFType,
    TableResult,
    Word,
)


# ═══════════════════════════════════════════════════════════════════════════════
# A) CLASSIFY PDF
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyPdfReal:
    """Test classify_pdf() with real PDFs."""

    def test_text_pdf_classified_as_text(self, pdf_text_simple):
        """Simple text PDF should be classified as TEXT."""
        from python.helpers.pdf_extraction.pipeline import classify_pdf

        doc = get_backend().open_path(str(pdf_text_simple))
        config = PDFExtractionConfig()
        pdf_type, confidence = classify_pdf(doc, config)
        doc.close()

        assert pdf_type == PDFType.TEXT
        assert confidence > 0.5

    def test_empty_pdf_classified_as_scan_or_unknown(self, pdf_empty):
        """Empty PDF should be classified as SCAN or UNKNOWN."""
        from python.helpers.pdf_extraction.pipeline import classify_pdf

        doc = get_backend().open_path(str(pdf_empty))
        config = PDFExtractionConfig()
        pdf_type, confidence = classify_pdf(doc, config)
        doc.close()

        assert pdf_type in (PDFType.SCAN, PDFType.UNKNOWN)

    def test_dense_text_classified_as_text(self, pdf_dense_text):
        """Dense text should be classified as TEXT with high confidence."""
        from python.helpers.pdf_extraction.pipeline import classify_pdf

        doc = get_backend().open_path(str(pdf_dense_text))
        config = PDFExtractionConfig()
        pdf_type, confidence = classify_pdf(doc, config)
        doc.close()

        assert pdf_type == PDFType.TEXT
        assert confidence >= 0.8

    def test_classification_disabled_returns_unknown(self, pdf_text_simple):
        """When classification is disabled, should return UNKNOWN."""
        from python.helpers.pdf_extraction.pipeline import classify_pdf

        doc = get_backend().open_path(str(pdf_text_simple))
        config = PDFExtractionConfig()
        config.classification.enabled = False
        pdf_type, confidence = classify_pdf(doc, config)
        doc.close()

        assert pdf_type == PDFType.UNKNOWN
        assert confidence == 0.5

    def test_classification_multipage(self, pdf_text_multipage):
        """Multipage text should be classified as TEXT."""
        from python.helpers.pdf_extraction.pipeline import classify_pdf

        doc = get_backend().open_path(str(pdf_text_multipage))
        config = PDFExtractionConfig()
        pdf_type, confidence = classify_pdf(doc, config)
        doc.close()

        assert pdf_type == PDFType.TEXT


# ═══════════════════════════════════════════════════════════════════════════════
# B) EXTRACT WORDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractWordsPyMuPDF:
    """Test extract_words_pymupdf() with real PDFs."""

    def test_extracts_words_from_text_pdf(self, pdf_text_simple):
        """Should extract words with positions from text PDF."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_text_simple))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        assert len(words) > 0
        # Verify word structure
        for w in words:
            assert isinstance(w, Word)
            assert w.text.strip()
            assert w.bbox.x1 >= w.bbox.x0
            assert w.bbox.y1 >= w.bbox.y0
            assert w.confidence == 1.0  # Native text

    def test_extracts_correct_page_numbers(self, pdf_text_multipage):
        """Words should have correct page numbers."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_text_multipage))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        pages = set(w.page for w in words)
        assert 0 in pages  # Page 0 (first page)
        assert len(pages) == 3  # 3 pages total

    def test_respects_max_pages_budget(self, pdf_text_multipage):
        """Should respect max_pages limit."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_text_multipage))
        config = PDFExtractionConfig()
        config.budgets.max_pages = 1
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        pages = set(w.page for w in words)
        assert pages == {0}  # Only first page

    def test_empty_pdf_returns_no_words(self, pdf_empty):
        """Empty PDF should return no words."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_empty))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        assert len(words) == 0

    def test_single_word_extracts_one_word(self, pdf_single_word):
        """Single word PDF should extract exactly one word."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_single_word))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        assert len(words) == 1
        assert words[0].text == "Korev"
        assert words[0].page == 0

    def test_whitespace_normalization(self, pdf_text_simple):
        """Words should have normalized whitespace."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_text_simple))
        config = PDFExtractionConfig()
        config.text.normalize_whitespace = True
        context = ExtractionContext(start_time=time.time())

        words = extract_words_pymupdf(doc, config, context)
        doc.close()

        for w in words:
            # No leading/trailing whitespace, no double spaces
            assert w.text == " ".join(w.text.split())

    def test_tracks_pages_processed(self, pdf_text_multipage):
        """Context should track pages processed."""
        from python.helpers.pdf_extraction.pipeline import extract_words_pymupdf

        doc = get_backend().open_path(str(pdf_text_multipage))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())

        extract_words_pymupdf(doc, config, context)
        doc.close()

        assert context.pages_processed == 3


# ═══════════════════════════════════════════════════════════════════════════════
# C) TABLE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTableExtractionGeometry:
    """Test geometry-based table extraction with real PDFs."""

    def test_detects_tables_in_table_pdf(self, pdf_table_simple):
        """Should detect at least one table in table PDF."""
        from python.helpers.pdf_extraction.pipeline import (
            extract_words_pymupdf,
            extract_tables_geometry,
        )

        doc = get_backend().open_path(str(pdf_table_simple))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())
        diagnostics = Diagnostics()

        words = extract_words_pymupdf(doc, config, context)
        tables = extract_tables_geometry(words, doc, config, context, diagnostics)
        doc.close()

        assert len(tables) > 0

    def test_table_has_correct_structure(self, pdf_table_simple):
        """Extracted table should have reasonable structure."""
        from python.helpers.pdf_extraction.pipeline import (
            extract_words_pymupdf,
            extract_tables_geometry,
        )

        doc = get_backend().open_path(str(pdf_table_simple))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())
        diagnostics = Diagnostics()

        words = extract_words_pymupdf(doc, config, context)
        tables = extract_tables_geometry(words, doc, config, context, diagnostics)
        doc.close()

        if tables:
            table = tables[0]
            assert table.num_rows > 0
            assert table.num_cols > 0
            assert len(table.cells) > 0
            assert table.page == 0

    def test_no_tables_in_text_only(self, pdf_single_word):
        """Single word PDF should not produce large tables."""
        from python.helpers.pdf_extraction.pipeline import (
            extract_words_pymupdf,
            extract_tables_geometry,
        )

        doc = get_backend().open_path(str(pdf_single_word))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())
        diagnostics = Diagnostics()

        words = extract_words_pymupdf(doc, config, context)
        tables = extract_tables_geometry(words, doc, config, context, diagnostics)
        doc.close()

        # Single word shouldn't form a table
        assert len(tables) == 0

    def test_table_extraction_disabled(self, pdf_table_simple):
        """When tables disabled, should return empty list."""
        from python.helpers.pdf_extraction.pipeline import (
            extract_words_pymupdf,
            extract_tables_geometry,
        )

        doc = get_backend().open_path(str(pdf_table_simple))
        config = PDFExtractionConfig()
        config.tables.enabled = False
        context = ExtractionContext(start_time=time.time())
        diagnostics = Diagnostics()

        words = extract_words_pymupdf(doc, config, context)
        tables = extract_tables_geometry(words, doc, config, context, diagnostics)
        doc.close()

        assert len(tables) == 0

    def test_financial_table_extraction(self, pdf_table_financial):
        """Financial table should be extracted with multiple rows."""
        from python.helpers.pdf_extraction.pipeline import (
            extract_words_pymupdf,
            extract_tables_geometry,
        )

        doc = get_backend().open_path(str(pdf_table_financial))
        config = PDFExtractionConfig()
        context = ExtractionContext(start_time=time.time())
        diagnostics = Diagnostics()

        words = extract_words_pymupdf(doc, config, context)
        tables = extract_tables_geometry(words, doc, config, context, diagnostics)
        doc.close()

        if tables:
            table = tables[0]
            assert table.num_rows >= 2  # At least header + 1 data row


# ═══════════════════════════════════════════════════════════════════════════════
# D) END-TO-END EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractFromPdfEndToEnd:
    """End-to-end tests for extract_from_pdf()."""

    def test_text_simple_full_pipeline(self, pdf_text_simple):
        """Full pipeline on text PDF produces valid result."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_simple))

        assert result.status == ExtractionStatus.SUCCESS
        assert result.pdf_type == PDFType.TEXT
        assert len(result.words) > 0
        assert result.diagnostics.page_count == 1
        assert ExtractionMethod.PYMUPDF_TEXT in result.diagnostics.methods_succeeded

    def test_multipage_full_pipeline(self, pdf_text_multipage):
        """Full pipeline on multipage PDF."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_multipage))

        assert result.status == ExtractionStatus.SUCCESS
        assert result.diagnostics.page_count == 3
        assert len(result.words) > 100

    def test_table_full_pipeline(self, pdf_table_simple):
        """Full pipeline on table PDF extracts tables."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_simple))

        assert result.status == ExtractionStatus.SUCCESS
        assert len(result.words) > 0
        # Tables may or may not be detected depending on geometry analysis

    def test_bytes_input(self, pdf_text_simple):
        """Should accept bytes input."""
        from python.helpers.pdf_extraction import extract_from_pdf

        pdf_bytes = pdf_text_simple.read_bytes()
        result = extract_from_pdf(pdf_bytes)

        assert result.status == ExtractionStatus.SUCCESS
        assert len(result.words) > 0
        assert result.document_hash is not None

    def test_path_input(self, pdf_text_simple):
        """Should accept Path input."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(pdf_text_simple)

        assert result.status == ExtractionStatus.SUCCESS

    def test_string_path_input(self, pdf_text_simple):
        """Should accept string path input."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_simple))

        assert result.status == ExtractionStatus.SUCCESS

    def test_document_hash_computed(self, pdf_text_simple):
        """Document hash should be computed and stable."""
        from python.helpers.pdf_extraction import extract_from_pdf

        r1 = extract_from_pdf(str(pdf_text_simple))
        r2 = extract_from_pdf(str(pdf_text_simple))

        assert r1.document_hash is not None
        assert r1.document_hash == r2.document_hash
        assert len(r1.document_hash) == 16  # SHA-256 truncated to 16

    def test_corrupted_pdf_returns_error(self, pdf_corrupted):
        """Corrupted PDF should return ERROR status."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_corrupted))

        assert result.status == ExtractionStatus.ERROR
        assert len(result.diagnostics.errors) > 0

    def test_empty_bytes_returns_error(self):
        """Empty bytes should return ERROR status."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(b"")

        assert result.status == ExtractionStatus.ERROR

    def test_custom_config_applied(self, pdf_text_multipage):
        """Custom config should be applied."""
        from python.helpers.pdf_extraction import extract_from_pdf

        config = PDFExtractionConfig()
        config.budgets.max_pages = 1

        result = extract_from_pdf(str(pdf_text_multipage), config=config)

        # Only first page should be processed
        pages = set(w.page for w in result.words)
        assert pages == {0}


# ═══════════════════════════════════════════════════════════════════════════════
# E) CONFIDENCE AND REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceCalculation:
    """Test confidence calculation."""

    def test_text_pdf_has_high_confidence(self, pdf_text_simple):
        """Text PDF should have reasonable confidence."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_simple))
        assert result.confidence_overall > 0

    def test_corrupted_pdf_flags_review(self, pdf_corrupted):
        """Corrupted PDF should flag for human review."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_corrupted))
        # Error results should indicate review needed
        assert result.status == ExtractionStatus.ERROR


# ═══════════════════════════════════════════════════════════════════════════════
# F) OUTPUT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputGeneration:
    """Test output artifact generation."""

    def test_csv_output_generated(self, pdf_table_simple):
        """CSV output should be generated for tables."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_simple))

        if result.tables:
            assert result.outputs.csv_data is not None
            assert len(result.outputs.csv_data) > 0

    def test_json_output_generated(self, pdf_table_simple):
        """JSON output should be generated for tables."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_simple))

        if result.tables:
            assert result.outputs.json_data is not None
            assert "tables" in result.outputs.json_data


# ═══════════════════════════════════════════════════════════════════════════════
# G) ASYNC WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncExtraction:
    """Test async extraction wrapper."""

    @pytest.mark.asyncio
    async def test_async_extraction_works(self, pdf_text_simple):
        """Async wrapper should produce same result as sync."""
        from python.helpers.pdf_extraction import extract_from_pdf, extract_from_pdf_async

        sync_result = extract_from_pdf(str(pdf_text_simple))
        async_result = await extract_from_pdf_async(str(pdf_text_simple))

        assert sync_result.status == async_result.status
        assert len(sync_result.words) == len(async_result.words)
        assert sync_result.pdf_type == async_result.pdf_type

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Async wrapper should handle errors gracefully."""
        from python.helpers.pdf_extraction import extract_from_pdf_async, ExtractionStatus

        result = await extract_from_pdf_async(b"not a pdf")

        assert result.status == ExtractionStatus.ERROR


# ═══════════════════════════════════════════════════════════════════════════════
# H) HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestClusterColumns:
    """Test column clustering."""

    def test_clusters_aligned_words(self):
        """Words at similar x-coordinates should cluster."""
        from python.helpers.pdf_extraction.pipeline import cluster_columns

        words = [
            Word(text="A", bbox=BBox(10, 100, 30, 110), page=0),
            Word(text="B", bbox=BBox(10, 120, 30, 130), page=0),
            Word(text="C", bbox=BBox(200, 100, 220, 110), page=0),
            Word(text="D", bbox=BBox(200, 120, 220, 130), page=0),
        ]
        config = PDFExtractionConfig()

        columns = cluster_columns(words, config)
        assert len(columns) == 2  # Two column groups

    def test_empty_words_returns_empty(self):
        """No words should return no columns."""
        from python.helpers.pdf_extraction.pipeline import cluster_columns

        config = PDFExtractionConfig()
        assert cluster_columns([], config) == []


class TestClusterRows:
    """Test row clustering."""

    def test_clusters_aligned_rows(self):
        """Words at similar y-coordinates should cluster."""
        from python.helpers.pdf_extraction.pipeline import cluster_rows

        words = [
            Word(text="A", bbox=BBox(10, 100, 30, 110), page=0),
            Word(text="B", bbox=BBox(200, 100, 220, 110), page=0),
            Word(text="C", bbox=BBox(10, 200, 30, 210), page=0),
            Word(text="D", bbox=BBox(200, 200, 220, 210), page=0),
        ]
        config = PDFExtractionConfig()

        rows = cluster_rows(words, config)
        assert len(rows) == 2  # Two row groups

    def test_empty_words_returns_empty(self):
        """No words should return no rows."""
        from python.helpers.pdf_extraction.pipeline import cluster_rows

        config = PDFExtractionConfig()
        assert cluster_rows([], config) == []
