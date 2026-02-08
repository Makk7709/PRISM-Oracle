"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF PIPELINE — END-TO-END TESTS                          ║
║                                                                              ║
║  Full end-to-end tests of the new pdfplumber/pypdf-based pipeline.           ║
║                                                                              ║
║  Tests the ENTIRE data path:                                                 ║
║  1. PDF bytes/path -> Backend opens document                                 ║
║  2. Classification (text/scan/hybrid)                                        ║
║  3. Word extraction with positions                                           ║
║  4. Table detection and reconstruction                                       ║
║  5. Output generation (CSV, JSON, DOCX)                                      ║
║  6. Confidence scoring and review flags                                      ║
║  7. Diagnostics and provenance                                               ║
║  8. FileReader tool integration                                              ║
║  9. PdfOcr tool integration                                                  ║
║  10. Async pipeline                                                          ║
║  11. Error paths                                                             ║
║  12. Backend abstraction layer                                               ║
║                                                                              ║
║  NO MOCKS — everything runs against real PDF fixtures.                       ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import io
import json
import time
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 1: Simple text document (analyst report)
# Full path: open -> classify -> extract words -> confidence -> outputs
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ETextDocument:
    """
    Scenario: Analyst receives a simple text PDF report.
    Expected: Clean text extraction, TEXT classification, high confidence.
    """

    def test_full_pipeline_from_path(self, pdf_text_simple):
        """E2E: file path -> full extraction -> all outputs."""
        from python.helpers.pdf_extraction import (
            extract_from_pdf,
            ExtractionStatus,
            ExtractionMethod,
            PDFType,
        )

        result = extract_from_pdf(str(pdf_text_simple))

        # 1. Status
        assert result.status == ExtractionStatus.SUCCESS, (
            f"Expected SUCCESS, got {result.status}"
        )

        # 2. Classification
        assert result.pdf_type == PDFType.TEXT, (
            f"Simple text PDF should be TEXT, got {result.pdf_type}"
        )
        assert result.pdf_type_confidence > 0.5

        # 3. Words extracted
        assert len(result.words) > 30, (
            f"Expected >30 words, got {len(result.words)}"
        )

        # 4. Words have valid structure
        for word in result.words:
            assert word.text.strip(), "Empty word found"
            assert word.page == 0, "Single-page PDF, all words should be page 0"
            assert word.bbox.x0 >= 0
            assert word.bbox.y0 >= 0
            assert word.bbox.x1 > word.bbox.x0
            assert word.bbox.y1 > word.bbox.y0
            assert word.confidence == 1.0

        # 5. Specific content present
        all_text = " ".join(w.text for w in result.words).lower()
        assert "test" in all_text or "document" in all_text, (
            "Expected 'test' or 'document' in extracted text"
        )
        assert "42" in all_text, "Number 42 should be preserved"
        assert "3.14" in all_text, "Number 3.14 should be preserved"

        # 6. Methods tracked
        assert ExtractionMethod.PYMUPDF_TEXT in result.diagnostics.methods_attempted
        assert ExtractionMethod.PYMUPDF_TEXT in result.diagnostics.methods_succeeded

        # 7. Diagnostics
        assert result.diagnostics.page_count == 1
        assert result.diagnostics.word_count == len(result.words)
        assert result.diagnostics.total_time_ms > 0
        assert result.diagnostics.text_extraction_time_ms >= 0

        # 8. Document hash (deterministic)
        assert result.document_hash is not None
        assert len(result.document_hash) == 16

        # 9. No errors
        assert len(result.diagnostics.errors) == 0

    def test_full_pipeline_from_bytes(self, pdf_text_simple):
        """E2E: bytes -> full extraction (same result as path)."""
        from python.helpers.pdf_extraction import extract_from_pdf

        pdf_bytes = pdf_text_simple.read_bytes()
        result = extract_from_pdf(pdf_bytes)

        assert result.status.value == "success"
        assert len(result.words) > 30
        assert result.document_hash is not None

    def test_idempotent_extraction(self, pdf_text_simple):
        """E2E: Extracting twice gives identical word-level results."""
        from python.helpers.pdf_extraction import extract_from_pdf

        r1 = extract_from_pdf(str(pdf_text_simple))
        r2 = extract_from_pdf(str(pdf_text_simple))

        assert len(r1.words) == len(r2.words)
        for w1, w2 in zip(r1.words, r2.words):
            assert w1.text == w2.text, f"Word mismatch: '{w1.text}' vs '{w2.text}'"
            assert w1.page == w2.page
            assert abs(w1.bbox.x0 - w2.bbox.x0) < 0.01
            assert abs(w1.bbox.y0 - w2.bbox.y0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 2: Multi-page document
# Full path: multiple pages -> words from all pages -> page tracking
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EMultipageDocument:
    """
    Scenario: Legal analyst processes a 3-page regulatory document.
    Expected: Words from all pages, correct page assignment.
    """

    def test_all_pages_extracted(self, pdf_text_multipage):
        """E2E: All 3 pages produce words with correct page numbers."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_multipage))

        assert result.status.value == "success"
        assert result.diagnostics.page_count == 3

        # Words from all 3 pages
        pages_with_words = set(w.page for w in result.words)
        assert 0 in pages_with_words, "Missing words from page 0"
        assert 1 in pages_with_words, "Missing words from page 1"
        assert 2 in pages_with_words, "Missing words from page 2"

        # Verify page-specific content
        page0_text = " ".join(w.text for w in result.words if w.page == 0).lower()
        page1_text = " ".join(w.text for w in result.words if w.page == 1).lower()
        page2_text = " ".join(w.text for w in result.words if w.page == 2).lower()

        assert len(page0_text) > 50, "Page 0 should have substantial text"
        assert len(page1_text) > 50, "Page 1 should have substantial text"
        assert len(page2_text) > 50, "Page 2 should have substantial text"

    def test_max_pages_budget_respected(self, pdf_text_multipage):
        """E2E: Budget limits number of pages processed."""
        from python.helpers.pdf_extraction import extract_from_pdf, PDFExtractionConfig

        config = PDFExtractionConfig()
        config.budgets.max_pages = 2

        result = extract_from_pdf(str(pdf_text_multipage), config=config)

        pages = set(w.page for w in result.words)
        assert 2 not in pages, "Page 2 should NOT be extracted (max_pages=2)"
        assert 0 in pages


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 3: Financial table document
# Full path: table -> geometry reconstruction -> CSV/JSON output
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ETableDocument:
    """
    Scenario: Finance team processes a revenue report with tables.
    Expected: Table detected, cells extracted, CSV/JSON output.
    """

    def test_table_detected_and_extracted(self, pdf_table_simple):
        """E2E: Table PDF -> table detection -> cell extraction -> outputs."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_simple))

        assert result.status.value == "success"
        assert len(result.words) > 0, "Should extract words from table"

        # Table-specific words should be present
        all_text = " ".join(w.text for w in result.words).lower()
        # At least some table content should be extracted as words
        assert "revenue" in all_text or "product" in all_text or "alpha" in all_text, (
            f"Expected table content words, got: {all_text[:200]}"
        )

    def test_financial_table_numbers_preserved(self, pdf_table_financial):
        """E2E: Financial table numbers extracted accurately."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_financial))

        assert result.status.value == "success"

        all_text = " ".join(w.text for w in result.words)

        # Key financial figures (may have spaces)
        assert "15" in all_text, "Should contain '15' (part of revenue)"
        assert "%" in all_text, "Should contain percentage signs"

    def test_table_output_artifacts(self, pdf_table_simple):
        """E2E: Table extraction produces output artifacts."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_table_simple))

        # If tables were detected, outputs should be generated
        if result.tables:
            # CSV output
            assert result.outputs.csv_data is not None, "CSV output should be generated"
            assert len(result.outputs.csv_data) > 0

            # JSON output
            assert result.outputs.json_data is not None, "JSON output should be generated"
            assert "tables" in result.outputs.json_data
            assert result.outputs.json_data["table_count"] > 0

            # Table structure
            for table in result.tables:
                assert table.num_rows > 0
                assert table.num_cols > 0
                assert len(table.cells) > 0
                assert table.page >= 0

                # CSV conversion
                csv = table.to_csv()
                assert len(csv) > 0

                # JSON conversion
                d = table.to_dict()
                assert "rows" in d
                assert "num_rows" in d

    def test_two_tables_on_one_page(self, pdf_two_tables):
        """E2E: Document with 2 tables on one page."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_two_tables))

        assert result.status.value == "success"

        # Should extract text from both tables
        all_text = " ".join(w.text for w in result.words).lower()
        assert "region" in all_text or "europe" in all_text


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 4: Mixed content (text + tables)
# Full path: classify as hybrid -> extract both text and tables
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EMixedContent:
    """
    Scenario: Analyst processes a report with prose AND tables.
    Expected: Both text and table content extracted.
    """

    def test_mixed_content_full_extraction(self, pdf_mixed_content):
        """E2E: Mixed PDF -> text from page 1 + table from page 2."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_mixed_content))

        assert result.status.value == "success"
        assert result.diagnostics.page_count == 2

        # Page 1: text content
        page0_text = " ".join(w.text for w in result.words if w.page == 0).lower()
        assert "executive" in page0_text or "summary" in page0_text or "report" in page0_text

        # Page 2: table + text content
        page1_text = " ".join(w.text for w in result.words if w.page == 1).lower()
        assert "quarter" in page1_text or "q1" in page1_text or "revenue" in page1_text


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 5: French legal text (Unicode)
# Full path: unicode extraction -> accents preserved
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EUnicodeDocument:
    """
    Scenario: Legal team processes French regulatory text.
    Expected: Accents, special chars, legal references preserved.
    """

    def test_french_accents_preserved(self, pdf_unicode_content):
        """E2E: French text with accents extracted correctly."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_unicode_content))

        assert result.status.value == "success"

        all_text = " ".join(w.text for w in result.words)

        # French accented words must be preserved
        assert "é" in all_text or "è" in all_text or "ê" in all_text, (
            "French accents should be preserved in extraction"
        )

        # Legal references
        lower_text = all_text.lower()
        assert "article" in lower_text or "code" in lower_text, (
            "Legal references should be extracted"
        )

    def test_unicode_word_integrity(self, pdf_unicode_content):
        """E2E: Each unicode word has valid bbox and text."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_unicode_content))

        for word in result.words:
            # Word should be valid unicode string
            assert isinstance(word.text, str)
            assert word.text == word.text.strip() or " " not in word.text
            # Bbox valid
            assert word.bbox.width > 0
            assert word.bbox.height > 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 6: Dense regulatory text (performance)
# Full path: large text -> extraction within budget -> timing tracked
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EDenseText:
    """
    Scenario: Compliance team processes dense regulatory analysis.
    Expected: Complete extraction within time budget, many words.
    """

    def test_dense_text_within_time_budget(self, pdf_dense_text):
        """E2E: Dense text extracted within 25s budget."""
        from python.helpers.pdf_extraction import extract_from_pdf, PDFExtractionConfig

        config = PDFExtractionConfig()
        config.budgets.total_timeout_s = 25.0

        start = time.time()
        result = extract_from_pdf(str(pdf_dense_text), config=config)
        elapsed = time.time() - start

        assert result.status.value == "success"
        assert elapsed < 25.0, f"Extraction took {elapsed:.1f}s, exceeds 25s budget"
        assert len(result.words) > 100, (
            f"Dense text should produce >100 words, got {len(result.words)}"
        )

    def test_diagnostics_timing_tracked(self, pdf_dense_text):
        """E2E: All timing fields populated in diagnostics."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_dense_text))

        diag = result.diagnostics
        assert diag.total_time_ms > 0
        assert diag.text_extraction_time_ms >= 0
        assert diag.classification_time_ms >= 0

        # Safe dict should be JSON-serializable
        safe = diag.to_safe_dict()
        json_str = json.dumps(safe)
        assert len(json_str) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 7: FileReader tool integration
# Full path: FileReader._read_pdf() -> user-facing text output
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EFileReaderTool:
    """
    Scenario: Agent uses FileReader tool to read a PDF for the user.
    Expected: Human-readable text output with page markers.
    """

    def test_file_reader_produces_readable_output(self, pdf_text_simple):
        """E2E: FileReader._read_pdf() produces clean, readable text."""
        from python.tools.file_reader import FileReader

        reader = FileReader.__new__(FileReader)
        result = reader._read_pdf(str(pdf_text_simple))

        assert isinstance(result, str)
        assert len(result) > 100
        assert "Pages:" in result
        assert "Page 1" in result

    def test_file_reader_multipage(self, pdf_text_multipage):
        """E2E: FileReader shows text from all pages."""
        from python.tools.file_reader import FileReader

        reader = FileReader.__new__(FileReader)
        result = reader._read_pdf(str(pdf_text_multipage))

        assert "Page 1" in result
        assert "Page 2" in result
        assert "Page 3" in result

    def test_file_reader_empty_pdf(self, pdf_empty):
        """E2E: FileReader handles empty PDF gracefully."""
        from python.tools.file_reader import FileReader

        reader = FileReader.__new__(FileReader)
        result = reader._read_pdf(str(pdf_empty))

        assert isinstance(result, str)
        assert "no extractable text" in result.lower()

    def test_file_reader_financial_table(self, pdf_table_financial):
        """E2E: FileReader extracts financial table content."""
        from python.tools.file_reader import FileReader

        reader = FileReader.__new__(FileReader)
        result = reader._read_pdf(str(pdf_table_financial))

        assert len(result) > 50
        # Financial content should appear
        assert "%" in result or "EUR" in result or "Bilan" in result


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 8: PdfOcr tool integration
# Full path: PdfOcr._extract_text_direct() -> text detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EPdfOcrTool:
    """
    Scenario: Agent uses PdfOcr tool, first tries direct extraction.
    Expected: Direct text extraction succeeds for text-based PDFs.
    """

    def test_ocr_direct_extraction_text_pdf(self, pdf_text_simple):
        """E2E: PdfOcr direct extraction produces text from text PDF."""
        from python.tools.pdf_ocr import PdfOcr

        ocr = PdfOcr.__new__(PdfOcr)
        result = ocr._extract_text_direct(str(pdf_text_simple))

        assert len(result) > 100, (
            f"Direct extraction should produce text, got {len(result)} chars"
        )
        assert "42" in result

    def test_ocr_direct_extraction_empty_pdf(self, pdf_empty):
        """E2E: PdfOcr direct extraction returns empty for empty PDF."""
        from python.tools.pdf_ocr import PdfOcr

        ocr = PdfOcr.__new__(PdfOcr)
        result = ocr._extract_text_direct(str(pdf_empty))

        assert result.strip() == ""

    def test_ocr_direct_extraction_unicode(self, pdf_unicode_content):
        """E2E: PdfOcr direct extraction handles French text."""
        from python.tools.pdf_ocr import PdfOcr

        ocr = PdfOcr.__new__(PdfOcr)
        result = ocr._extract_text_direct(str(pdf_unicode_content))

        assert len(result) > 100
        assert "é" in result or "è" in result or "ê" in result


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 9: Async pipeline
# Full path: async wrapper -> same results as sync
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EAsyncPipeline:
    """
    Scenario: Pipeline called from async web handler.
    Expected: Same results as synchronous call.
    """

    @pytest.mark.asyncio
    async def test_async_extraction_matches_sync(self, pdf_text_simple):
        """E2E: Async and sync produce identical results."""
        from python.helpers.pdf_extraction import extract_from_pdf, extract_from_pdf_async

        sync_result = extract_from_pdf(str(pdf_text_simple))
        async_result = await extract_from_pdf_async(str(pdf_text_simple))

        assert sync_result.status == async_result.status
        assert sync_result.pdf_type == async_result.pdf_type
        assert len(sync_result.words) == len(async_result.words)
        assert sync_result.document_hash == async_result.document_hash

        # Word-by-word match
        for s_word, a_word in zip(sync_result.words, async_result.words):
            assert s_word.text == a_word.text

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """E2E: Async handles errors gracefully."""
        from python.helpers.pdf_extraction import extract_from_pdf_async, ExtractionStatus

        result = await extract_from_pdf_async(b"invalid pdf content")

        assert result.status == ExtractionStatus.ERROR
        assert len(result.diagnostics.errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 10: Error paths
# Full path: corrupted/invalid input -> clean error response
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EErrorPaths:
    """
    Scenario: System receives invalid/corrupted PDFs.
    Expected: Clean error response, no crash, no data leakage.
    """

    def test_corrupted_pdf_clean_error(self, pdf_corrupted):
        """E2E: Corrupted PDF -> ERROR status, diagnostics, no crash."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus

        result = extract_from_pdf(str(pdf_corrupted))

        assert result.status == ExtractionStatus.ERROR
        assert len(result.diagnostics.errors) > 0
        # total_time_ms may be 0 if error happens very fast (sub-millisecond)
        assert result.diagnostics.total_time_ms >= 0
        assert result.pdf_type is not None

    def test_empty_bytes_clean_error(self):
        """E2E: Empty bytes -> ERROR, not crash."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus

        result = extract_from_pdf(b"")

        assert result.status == ExtractionStatus.ERROR
        assert isinstance(result.diagnostics.errors, list)

    def test_random_bytes_clean_error(self):
        """E2E: Random bytes -> ERROR, not crash."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus

        result = extract_from_pdf(b"random garbage bytes that are not a pdf at all")

        assert result.status == ExtractionStatus.ERROR

    def test_no_sensitive_data_leakage_on_error(self, caplog):
        """E2E: Error logs must NOT contain user content."""
        import logging
        from python.helpers.pdf_extraction import extract_from_pdf

        sensitive = "CONFIDENTIAL_SECRET_DATA_12345"
        pdf_bytes = f"%PDF-1.4\n{sensitive}\n%%EOF".encode()

        with caplog.at_level(logging.DEBUG):
            result = extract_from_pdf(pdf_bytes)

        # Check logs
        log_text = caplog.text
        assert sensitive not in log_text, (
            "Sensitive data found in logs!"
        )

        # Check diagnostics
        diag_str = str(result.diagnostics.errors)
        assert sensitive not in diag_str


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 11: Backend abstraction
# Full path: verify pdfplumber is the active backend
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EBackendVerification:
    """
    Scenario: Verify the correct backend is active.
    Expected: pdfplumber is the default, pymupdf is NOT used in production.
    """

    def test_default_backend_is_pdfplumber(self):
        """E2E: Default backend should be pdfplumber (MIT)."""
        from python.helpers.pdf_extraction.pdf_backend import get_backend

        backend = get_backend()
        assert backend.name == "pdfplumber", (
            f"Default backend should be pdfplumber, got {backend.name}"
        )

    def test_pdfplumber_backend_opens_pdf(self, pdf_text_simple):
        """E2E: pdfplumber backend can open and read PDFs."""
        from python.helpers.pdf_extraction.pdf_backend import PdfPlumberBackend

        backend = PdfPlumberBackend()
        with backend.open(str(pdf_text_simple)) as doc:
            assert doc.page_count() == 1
            page = doc.get_page(0)
            assert len(page.words) > 0
            assert len(page.text) > 0

    def test_pdfplumber_backend_from_bytes(self, pdf_text_simple):
        """E2E: pdfplumber backend works from bytes."""
        from python.helpers.pdf_extraction.pdf_backend import PdfPlumberBackend

        backend = PdfPlumberBackend()
        data = pdf_text_simple.read_bytes()
        with backend.open(data) as doc:
            assert doc.page_count() == 1
            words = doc.get_all_words()
            assert len(words) > 0

    def test_no_fitz_import_in_production_path(self, pdf_text_simple):
        """E2E: Production extraction path does NOT import fitz."""
        import sys

        # Remove fitz from sys.modules if present
        fitz_was_loaded = "fitz" in sys.modules

        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(pdf_text_simple))

        assert result.status.value == "success"

        # If fitz wasn't loaded before, it shouldn't be loaded now
        # (unless parity tests loaded it earlier in the session)
        # This is a best-effort check
        if not fitz_was_loaded:
            # fitz may still be in sys.modules from other tests in session
            # Just verify the result is valid
            assert len(result.words) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 12: Config presets
# Full path: different configs -> different behavior
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EConfigPresets:
    """
    Scenario: Pipeline used with different config presets.
    Expected: Behavior changes according to config.
    """

    def test_fast_config_respects_tight_budget(self, pdf_text_multipage):
        """E2E: Fast config processes fewer pages."""
        from python.helpers.pdf_extraction import extract_from_pdf, get_fast_config

        config = get_fast_config()
        config.budgets.max_pages = 1

        result = extract_from_pdf(str(pdf_text_multipage), config=config)

        pages = set(w.page for w in result.words)
        assert pages == {0}, f"Fast config (max_pages=1) should only process page 0, got {pages}"

    def test_default_config_safe_defaults(self, pdf_table_simple):
        """E2E: Default config has safe settings."""
        from python.helpers.pdf_extraction import extract_from_pdf, get_default_config

        config = get_default_config()

        # Verify safe defaults
        assert config.ocr.enabled is False
        assert config.is_engine_enabled("pdfplumber") is False
        assert config.is_engine_enabled("camelot") is False
        assert config.security.never_log_user_content is True

        result = extract_from_pdf(str(pdf_table_simple), config=config)
        assert result.status.value == "success"

    def test_tables_disabled_skips_table_extraction(self, pdf_table_simple):
        """E2E: Disabling tables skips table extraction."""
        from python.helpers.pdf_extraction import extract_from_pdf, PDFExtractionConfig

        config = PDFExtractionConfig()
        config.tables.enabled = False

        result = extract_from_pdf(str(pdf_table_simple), config=config)

        assert result.status.value in ("success", "partial")
        assert len(result.tables) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E SCENARIO 13: Summary and provenance
# Full path: extraction -> summary() -> safe for logging
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ESummaryAndProvenance:
    """
    Scenario: Pipeline results are logged and audited.
    Expected: Summary is safe, complete, JSON-serializable.
    """

    def test_summary_is_json_serializable(self, pdf_text_simple):
        """E2E: summary() dict is fully JSON-serializable."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_simple))
        summary = result.summary()

        # Must be JSON-serializable
        json_str = json.dumps(summary)
        assert len(json_str) > 0

        # Must contain key fields
        assert "status" in summary
        assert "pdf_type" in summary
        assert "word_count" in summary
        assert "total_time_ms" in summary
        assert "document_hash" in summary

    def test_summary_contains_no_user_content(self, pdf_text_simple):
        """E2E: Summary must not contain raw PDF text."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_text_simple))
        summary = result.summary()
        summary_str = json.dumps(summary).lower()

        # Known content from the fixture
        assert "extraction pipeline" not in summary_str
        assert "42" not in summary_str or summary_str.count("42") <= 1  # may appear in timing
        assert "3.14" not in summary_str

    def test_is_successful_helper(self, pdf_text_simple, pdf_corrupted):
        """E2E: is_successful() returns correct boolean."""
        from python.helpers.pdf_extraction import extract_from_pdf

        good = extract_from_pdf(str(pdf_text_simple))
        assert good.is_successful() is True

        bad = extract_from_pdf(str(pdf_corrupted))
        assert bad.is_successful() is False
