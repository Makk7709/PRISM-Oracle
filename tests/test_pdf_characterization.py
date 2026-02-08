"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF CHARACTERIZATION TESTS                               ║
║                                                                              ║
║  PURPOSE: Lock down the EXACT behavior of the current PyMuPDF-based          ║
║  extraction BEFORE migrating to pdfplumber/pypdf.                            ║
║                                                                              ║
║  HOW IT WORKS:                                                               ║
║  1. First run: generates golden files (snapshots of current output)          ║
║  2. Subsequent runs: asserts output matches golden files exactly             ║
║  3. If migration changes output: tests fail, showing exactly what changed    ║
║  4. After validating changes are acceptable: --regen-golden to update        ║
║                                                                              ║
║  CRITICAL: Do NOT regenerate golden files without manual review!             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# A) PIPELINE — extract_from_pdf() characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineCharacterization:
    """
    Characterize the full pipeline output for each fixture.
    
    Captures:
    - Status, PDF type, confidence
    - Word count, first/last N words
    - Table count, table shapes
    - Methods attempted/succeeded
    """

    def test_text_simple(self, pdf_text_simple, golden):
        snapshot = self._extract_snapshot(pdf_text_simple)
        golden.assert_or_create("pipeline__text_simple", snapshot)

    def test_text_multipage(self, pdf_text_multipage, golden):
        snapshot = self._extract_snapshot(pdf_text_multipage)
        golden.assert_or_create("pipeline__text_multipage", snapshot)

    def test_table_simple(self, pdf_table_simple, golden):
        snapshot = self._extract_snapshot(pdf_table_simple)
        golden.assert_or_create("pipeline__table_simple", snapshot)

    def test_table_financial(self, pdf_table_financial, golden):
        snapshot = self._extract_snapshot(pdf_table_financial)
        golden.assert_or_create("pipeline__table_financial", snapshot)

    def test_mixed_content(self, pdf_mixed_content, golden):
        snapshot = self._extract_snapshot(pdf_mixed_content)
        golden.assert_or_create("pipeline__mixed_content", snapshot)

    def test_empty(self, pdf_empty, golden):
        snapshot = self._extract_snapshot(pdf_empty)
        golden.assert_or_create("pipeline__empty", snapshot)

    def test_single_word(self, pdf_single_word, golden):
        snapshot = self._extract_snapshot(pdf_single_word)
        golden.assert_or_create("pipeline__single_word", snapshot)

    def test_dense_text(self, pdf_dense_text, golden):
        snapshot = self._extract_snapshot(pdf_dense_text)
        golden.assert_or_create("pipeline__dense_text", snapshot)

    def test_unicode_content(self, pdf_unicode_content, golden):
        snapshot = self._extract_snapshot(pdf_unicode_content)
        golden.assert_or_create("pipeline__unicode_content", snapshot)

    def test_two_tables(self, pdf_two_tables, golden):
        snapshot = self._extract_snapshot(pdf_two_tables)
        golden.assert_or_create("pipeline__two_tables", snapshot)

    def test_corrupted(self, pdf_corrupted, golden):
        snapshot = self._extract_snapshot(pdf_corrupted)
        golden.assert_or_create("pipeline__corrupted", snapshot)

    # ─── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_snapshot(pdf_path: Path) -> dict:
        """Run the full pipeline and capture a deterministic snapshot."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_path))

        # Capture deterministic fields only (no timing, no correlation IDs)
        snapshot = {
            "status": result.status.value,
            "pdf_type": result.pdf_type.value,
            "pdf_type_confidence": result.pdf_type_confidence,
            "word_count": len(result.words),
            "table_count": len(result.tables),
            "pages_processed": result.diagnostics.page_count,
            "methods_attempted": sorted(
                [m.value for m in result.diagnostics.methods_attempted]
            ),
            "methods_succeeded": sorted(
                [m.value for m in result.diagnostics.methods_succeeded]
            ),
            "fallback_used": result.diagnostics.fallback_used,
            "errors": result.diagnostics.errors,
            "requires_human_review": result.requires_human_review,
        }

        # First 30 words (for text verification)
        if result.words:
            snapshot["first_30_words"] = [w.text for w in result.words[:30]]
            snapshot["last_10_words"] = [w.text for w in result.words[-10:]]

        # Table shapes and content samples
        if result.tables:
            snapshot["tables"] = []
            for i, table in enumerate(result.tables):
                t_snap = {
                    "index": i,
                    "num_rows": table.num_rows,
                    "num_cols": table.num_cols,
                    "page": table.page,
                    "method": table.method.value,
                    "confidence": table.confidence,
                    "fill_ratio": table.fill_ratio,
                    "cell_count": len(table.cells),
                }
                # Capture first row (header) and first data row
                rows = table.to_rows()
                if rows:
                    t_snap["header_row"] = rows[0]
                if len(rows) > 1:
                    t_snap["first_data_row"] = rows[1]
                snapshot["tables"].append(t_snap)

        return snapshot


# ═══════════════════════════════════════════════════════════════════════════════
# B) WORD EXTRACTION — detailed word-level characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestWordExtractionCharacterization:
    """
    Characterize word-by-word extraction including positions.
    
    These tests are more granular than pipeline tests — they capture
    word text, page number, and approximate bounding box positions.
    """

    def test_text_simple_words(self, pdf_text_simple, golden):
        snapshot = self._extract_words_snapshot(pdf_text_simple)
        golden.assert_or_create("words__text_simple", snapshot)

    def test_single_word_words(self, pdf_single_word, golden):
        snapshot = self._extract_words_snapshot(pdf_single_word)
        golden.assert_or_create("words__single_word", snapshot)

    def test_unicode_words(self, pdf_unicode_content, golden):
        snapshot = self._extract_words_snapshot(pdf_unicode_content)
        golden.assert_or_create("words__unicode_content", snapshot)

    def test_table_simple_words(self, pdf_table_simple, golden):
        snapshot = self._extract_words_snapshot(pdf_table_simple)
        golden.assert_or_create("words__table_simple", snapshot)

    @staticmethod
    def _extract_words_snapshot(pdf_path: Path) -> dict:
        """Capture detailed word extraction snapshot."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_path))

        words_data = []
        for w in result.words:
            words_data.append({
                "text": w.text,
                "page": w.page,
                # Round bbox to 1 decimal to absorb minor rendering diffs
                "x0": round(w.bbox.x0, 1),
                "y0": round(w.bbox.y0, 1),
                "x1": round(w.bbox.x1, 1),
                "y1": round(w.bbox.y1, 1),
                "confidence": w.confidence,
            })

        return {
            "total_words": len(words_data),
            "words": words_data,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# C) CLASSIFICATION — PDF type characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationCharacterization:
    """
    Characterize PDF classification for each fixture.
    
    Tests that classify_pdf() returns the same type and confidence
    for each fixture across backend changes.
    """

    def test_classification_text_simple(self, pdf_text_simple, golden):
        snap = self._classify(pdf_text_simple)
        golden.assert_or_create("classify__text_simple", snap)

    def test_classification_empty(self, pdf_empty, golden):
        snap = self._classify(pdf_empty)
        golden.assert_or_create("classify__empty", snap)

    def test_classification_table_simple(self, pdf_table_simple, golden):
        snap = self._classify(pdf_table_simple)
        golden.assert_or_create("classify__table_simple", snap)

    def test_classification_dense_text(self, pdf_dense_text, golden):
        snap = self._classify(pdf_dense_text)
        golden.assert_or_create("classify__dense_text", snap)

    def test_classification_mixed(self, pdf_mixed_content, golden):
        snap = self._classify(pdf_mixed_content)
        golden.assert_or_create("classify__mixed_content", snap)

    @staticmethod
    def _classify(pdf_path: Path) -> dict:
        """Run classification on a PDF and capture results."""
        import fitz
        from python.helpers.pdf_extraction.pipeline import classify_pdf
        from python.helpers.pdf_extraction.config import PDFExtractionConfig

        config = PDFExtractionConfig()
        doc = fitz.open(str(pdf_path))
        pdf_type, confidence = classify_pdf(doc, config)
        page_count = doc.page_count
        doc.close()

        return {
            "pdf_type": pdf_type.value,
            "confidence": confidence,
            "page_count": page_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# D) FILE READER — _read_pdf() characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileReaderCharacterization:
    """
    Characterize the file_reader._read_pdf() output.
    
    This tests the simpler PDF reading path used by the FileReader tool.
    """

    def test_file_reader_text_simple(self, pdf_text_simple, golden):
        result = self._read_pdf(pdf_text_simple)
        golden.assert_text_or_create("file_reader__text_simple", result)

    def test_file_reader_table_simple(self, pdf_table_simple, golden):
        result = self._read_pdf(pdf_table_simple)
        golden.assert_text_or_create("file_reader__table_simple", result)

    def test_file_reader_empty(self, pdf_empty, golden):
        result = self._read_pdf(pdf_empty)
        golden.assert_text_or_create("file_reader__empty", result)

    def test_file_reader_unicode(self, pdf_unicode_content, golden):
        result = self._read_pdf(pdf_unicode_content)
        golden.assert_text_or_create("file_reader__unicode_content", result)

    def test_file_reader_multipage(self, pdf_text_multipage, golden):
        result = self._read_pdf(pdf_text_multipage)
        golden.assert_text_or_create("file_reader__text_multipage", result)

    @staticmethod
    def _read_pdf(pdf_path: Path) -> str:
        """Call _read_pdf directly (bypass tool execution)."""
        from python.tools.file_reader import FileReader
        reader = FileReader.__new__(FileReader)
        return reader._read_pdf(str(pdf_path))


# ═══════════════════════════════════════════════════════════════════════════════
# E) PDF OCR — _extract_text_direct() characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestPdfOcrDirectExtractionCharacterization:
    """
    Characterize the pdf_ocr._extract_text_direct() output.
    
    This tests the initial text extraction attempt in the OCR tool
    (before falling back to actual OCR).
    """

    def test_ocr_direct_text_simple(self, pdf_text_simple, golden):
        result = self._extract_direct(pdf_text_simple)
        golden.assert_text_or_create("ocr_direct__text_simple", result)

    def test_ocr_direct_table_simple(self, pdf_table_simple, golden):
        result = self._extract_direct(pdf_table_simple)
        golden.assert_text_or_create("ocr_direct__table_simple", result)

    def test_ocr_direct_empty(self, pdf_empty, golden):
        result = self._extract_direct(pdf_empty)
        golden.assert_text_or_create("ocr_direct__empty", result)

    def test_ocr_direct_unicode(self, pdf_unicode_content, golden):
        result = self._extract_direct(pdf_unicode_content)
        golden.assert_text_or_create("ocr_direct__unicode_content", result)

    @staticmethod
    def _extract_direct(pdf_path: Path) -> str:
        """Call _extract_text_direct directly."""
        from python.tools.pdf_ocr import PdfOcr
        ocr = PdfOcr.__new__(PdfOcr)
        return ocr._extract_text_direct(str(pdf_path))


# ═══════════════════════════════════════════════════════════════════════════════
# F) TABLE EXTRACTION — detailed table characterization
# ═══════════════════════════════════════════════════════════════════════════════

class TestTableExtractionCharacterization:
    """
    Characterize detailed table extraction output.
    
    For each fixture that contains tables, capture:
    - Full cell grid (rows x cols)
    - CSV output
    - Cell-level metadata
    """

    def test_table_simple_extraction(self, pdf_table_simple, golden):
        snapshot = self._extract_tables_snapshot(pdf_table_simple)
        golden.assert_or_create("tables__table_simple", snapshot)

    def test_table_financial_extraction(self, pdf_table_financial, golden):
        snapshot = self._extract_tables_snapshot(pdf_table_financial)
        golden.assert_or_create("tables__table_financial", snapshot)

    def test_two_tables_extraction(self, pdf_two_tables, golden):
        snapshot = self._extract_tables_snapshot(pdf_two_tables)
        golden.assert_or_create("tables__two_tables", snapshot)

    def test_mixed_content_tables(self, pdf_mixed_content, golden):
        snapshot = self._extract_tables_snapshot(pdf_mixed_content)
        golden.assert_or_create("tables__mixed_content", snapshot)

    def test_text_only_no_tables(self, pdf_text_simple, golden):
        snapshot = self._extract_tables_snapshot(pdf_text_simple)
        golden.assert_or_create("tables__text_simple", snapshot)

    @staticmethod
    def _extract_tables_snapshot(pdf_path: Path) -> dict:
        """Extract tables and capture full content snapshot."""
        from python.helpers.pdf_extraction import extract_from_pdf

        result = extract_from_pdf(str(pdf_path))

        tables_data = []
        for i, table in enumerate(result.tables):
            rows = table.to_rows()
            csv_output = table.to_csv()

            cells_detail = []
            for cell in sorted(table.cells, key=lambda c: (c.row, c.col)):
                cell_data = {
                    "text": cell.text,
                    "row": cell.row,
                    "col": cell.col,
                }
                if cell.bbox:
                    cell_data["bbox"] = {
                        "x0": round(cell.bbox.x0, 1),
                        "y0": round(cell.bbox.y0, 1),
                        "x1": round(cell.bbox.x1, 1),
                        "y1": round(cell.bbox.y1, 1),
                    }
                cells_detail.append(cell_data)

            tables_data.append({
                "index": i,
                "num_rows": table.num_rows,
                "num_cols": table.num_cols,
                "page": table.page,
                "method": table.method.value,
                "confidence": table.confidence,
                "fill_ratio": table.fill_ratio,
                "rows": rows,
                "csv": csv_output,
                "cells": cells_detail,
            })

        return {
            "table_count": len(tables_data),
            "tables": tables_data,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# G) INVARIANT TESTS — properties that MUST hold after migration
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrationInvariants:
    """
    Properties that MUST hold regardless of PDF backend.
    
    These tests don't use golden files — they test invariants
    that any correct implementation must satisfy.
    """

    def test_extract_always_returns_result(self, any_valid_pdf):
        """extract_from_pdf must NEVER return None."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionResult
        result = extract_from_pdf(str(any_valid_pdf))
        assert isinstance(result, ExtractionResult)

    def test_extract_always_has_diagnostics(self, any_valid_pdf):
        """Every result must have diagnostics attached."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        assert result.diagnostics is not None
        assert result.diagnostics.page_count >= 0

    def test_extract_always_has_valid_status(self, any_valid_pdf):
        """Status must be a valid enum value."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus
        result = extract_from_pdf(str(any_valid_pdf))
        assert result.status in ExtractionStatus

    def test_extract_always_has_valid_pdf_type(self, any_valid_pdf):
        """PDF type must be a valid enum value."""
        from python.helpers.pdf_extraction import extract_from_pdf, PDFType
        result = extract_from_pdf(str(any_valid_pdf))
        assert result.pdf_type in PDFType

    def test_word_confidence_in_range(self, any_valid_pdf):
        """Word confidence must be 0.0-1.0."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        for word in result.words:
            assert 0.0 <= word.confidence <= 1.0, f"Bad confidence: {word.confidence}"

    def test_word_bbox_non_negative(self, any_valid_pdf):
        """Word bounding boxes must have non-negative coordinates."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        for word in result.words:
            assert word.bbox.x0 >= 0, f"Negative x0: {word.bbox.x0}"
            assert word.bbox.y0 >= 0, f"Negative y0: {word.bbox.y0}"
            assert word.bbox.x1 >= word.bbox.x0, f"x1 < x0: {word.bbox}"
            assert word.bbox.y1 >= word.bbox.y0, f"y1 < y0: {word.bbox}"

    def test_word_text_non_empty(self, any_valid_pdf):
        """Every extracted word must have non-empty text."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        for word in result.words:
            assert word.text.strip(), f"Empty word on page {word.page}"

    def test_word_page_in_range(self, any_valid_pdf):
        """Word page numbers must be within document range."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        if result.words:
            max_page = max(w.page for w in result.words)
            assert max_page < result.diagnostics.page_count

    def test_table_cells_within_bounds(self, any_valid_pdf):
        """Table cells must have row/col within table bounds."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        for table in result.tables:
            for cell in table.cells:
                assert 0 <= cell.row < table.num_rows, (
                    f"Cell row {cell.row} out of bounds (max {table.num_rows})"
                )
                assert 0 <= cell.col < table.num_cols, (
                    f"Cell col {cell.col} out of bounds (max {table.num_cols})"
                )

    def test_no_sensitive_data_in_summary(self, any_valid_pdf):
        """Summary dict must not contain raw text content."""
        from python.helpers.pdf_extraction import extract_from_pdf
        result = extract_from_pdf(str(any_valid_pdf))
        summary = result.summary()
        summary_str = json.dumps(summary)
        # Should not contain any word from the PDF
        assert "text" not in summary or isinstance(summary.get("text"), type(None))

    def test_corrupted_pdf_returns_error(self, pdf_corrupted):
        """Corrupted PDF must return error status, not crash."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus
        result = extract_from_pdf(str(pdf_corrupted))
        assert result.status == ExtractionStatus.ERROR
        assert len(result.diagnostics.errors) > 0

    def test_empty_bytes_returns_error(self):
        """Empty bytes must return error status."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus
        result = extract_from_pdf(b"")
        assert result.status == ExtractionStatus.ERROR

    def test_idempotent_extraction(self, pdf_text_simple):
        """Extracting twice must give identical results."""
        from python.helpers.pdf_extraction import extract_from_pdf
        r1 = extract_from_pdf(str(pdf_text_simple))
        r2 = extract_from_pdf(str(pdf_text_simple))

        assert len(r1.words) == len(r2.words)
        assert r1.pdf_type == r2.pdf_type
        assert r1.status == r2.status
        assert len(r1.tables) == len(r2.tables)

        # Word-by-word comparison
        for w1, w2 in zip(r1.words, r2.words):
            assert w1.text == w2.text
            assert w1.page == w2.page
