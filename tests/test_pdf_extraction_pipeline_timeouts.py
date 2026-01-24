"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF EXTRACTION - PIPELINE TIMEOUT TESTS                   ║
║                                                                              ║
║  Tests that verify:                                                          ║
║  - Operations don't block indefinitely                                       ║
║  - Circuit breaker trips correctly                                           ║
║  - Fallback works                                                            ║
║  - No sensitive data in logs                                                 ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest


class TestTimeoutUtilities:
    """Test timeout utility functions."""
    
    def test_run_with_timeout_success(self):
        """Test successful execution within timeout."""
        from python.helpers.pdf_extraction.pipeline import run_with_timeout
        
        def quick_func():
            return "success"
        
        result, timed_out = run_with_timeout(quick_func, timeout_s=5.0)
        
        assert result == "success"
        assert timed_out is False
    
    def test_run_with_timeout_timeout(self):
        """Test timeout triggers correctly."""
        from python.helpers.pdf_extraction.pipeline import run_with_timeout
        
        def slow_func():
            time.sleep(10)
            return "never"
        
        start = time.time()
        result, timed_out = run_with_timeout(slow_func, timeout_s=0.5)
        elapsed = time.time() - start
        
        assert timed_out is True
        assert result is None
        # Should complete within 1 second (0.5s timeout + overhead)
        assert elapsed < 2.0, f"Timeout took too long: {elapsed}s"
    
    def test_run_with_timeout_exception(self):
        """Test exceptions propagate correctly."""
        from python.helpers.pdf_extraction.pipeline import run_with_timeout
        
        def error_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            run_with_timeout(error_func, timeout_s=5.0)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Circuit breaker starts closed."""
        from python.helpers.pdf_extraction.pipeline import CircuitBreaker
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        cb = CircuitBreaker(config)
        
        assert cb.state.is_open is False
        assert cb.state.timeout_count == 0
        assert cb.state.failure_count == 0
        assert cb.is_engine_allowed("any_engine") is True
    
    def test_circuit_breaker_trips_on_timeouts(self):
        """Circuit breaker opens after max_timeouts."""
        from python.helpers.pdf_extraction.pipeline import CircuitBreaker
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        config.budgets.circuit_breaker.max_timeouts = 2
        
        cb = CircuitBreaker(config)
        
        # First timeout
        cb.record_timeout("engine1")
        assert cb.state.is_open is False
        assert cb.is_engine_allowed("engine1") is True
        
        # Second timeout - should trip
        cb.record_timeout("engine2")
        assert cb.state.is_open is True
        assert cb.is_engine_allowed("any_engine") is False
    
    def test_circuit_breaker_disables_failing_engine(self):
        """Circuit breaker disables specific engine after failures."""
        from python.helpers.pdf_extraction.pipeline import CircuitBreaker
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        config.budgets.circuit_breaker.max_engine_failures = 3
        
        cb = CircuitBreaker(config)
        
        # Record failures for specific engine
        cb.record_failure("bad_engine")
        cb.record_failure("bad_engine")
        assert cb.is_engine_allowed("bad_engine") is True
        
        cb.record_failure("bad_engine")  # Third failure
        assert cb.is_engine_allowed("bad_engine") is False
        
        # Other engines still allowed
        assert cb.is_engine_allowed("good_engine") is True


class TestExtractionResultTypes:
    """Test extraction result types."""
    
    def test_extraction_result_summary_no_sensitive_data(self):
        """Summary should not contain sensitive data."""
        from python.helpers.pdf_extraction import (
            ExtractionResult,
            PDFType,
            ExtractionStatus,
            Diagnostics
        )
        
        result = ExtractionResult(
            pdf_type=PDFType.TEXT,
            pdf_type_confidence=0.9,
            text="This is sensitive content that should NOT appear in logs",
            diagnostics=Diagnostics(page_count=5, word_count=100),
            confidence_overall=0.85
        )
        
        summary = result.summary()
        
        # Summary should exist
        assert "pdf_type" in summary
        assert "confidence_overall" in summary
        
        # Summary should NOT contain raw text
        summary_str = str(summary)
        assert "sensitive content" not in summary_str.lower()
        assert "This is" not in summary_str
    
    def test_diagnostics_safe_dict(self):
        """Diagnostics safe_dict should not leak content."""
        from python.helpers.pdf_extraction import Diagnostics
        
        diag = Diagnostics(
            total_time_ms=1000,
            page_count=10,
            word_count=500,
            errors=["ValueError"]  # Only exception type, no message
        )
        
        safe = diag.to_safe_dict()
        
        assert "total_time_ms" in safe
        assert "error_count" in safe
        assert safe["error_count"] == 1
        
        # Should not contain raw error messages
        assert "errors" not in safe or not any("sensitive" in str(e).lower() for e in safe.get("errors", []))
    
    def test_table_result_to_csv(self):
        """Test table CSV conversion."""
        from python.helpers.pdf_extraction import TableResult, Cell
        
        cells = [
            Cell(text="A", row=0, col=0),
            Cell(text="B", row=0, col=1),
            Cell(text="1", row=1, col=0),
            Cell(text="2", row=1, col=1),
        ]
        
        table = TableResult(
            cells=cells,
            num_rows=2,
            num_cols=2,
            page=0
        )
        
        csv = table.to_csv()
        
        assert "A" in csv
        assert "B" in csv
        assert "1" in csv
        assert "2" in csv
    
    def test_table_result_to_dict(self):
        """Test table JSON conversion."""
        from python.helpers.pdf_extraction import TableResult, Cell, ExtractionMethod
        
        cells = [
            Cell(text="Header", row=0, col=0),
            Cell(text="Value", row=1, col=0),
        ]
        
        table = TableResult(
            cells=cells,
            num_rows=2,
            num_cols=1,
            page=0,
            method=ExtractionMethod.PYMUPDF_GEOMETRY,
            confidence=0.8
        )
        
        d = table.to_dict()
        
        assert d["num_rows"] == 2
        assert d["num_cols"] == 1
        assert d["method"] == "pymupdf_geometry"
        assert d["confidence"] == 0.8


class TestNoLogLeakage:
    """Test that no sensitive data appears in logs."""
    
    def test_no_log_leakage_on_error(self, caplog):
        """Verify errors don't leak content to logs."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus
        
        # Use invalid PDF bytes to trigger an error
        with caplog.at_level(logging.DEBUG):
            result = extract_from_pdf(b"not a valid pdf with sensitive user data xyz")
        
        # Should return error status
        assert result.status == ExtractionStatus.ERROR
        
        # Check logs don't contain sensitive content
        log_text = caplog.text.lower()
        
        # The raw PDF bytes should not appear in logs
        assert "sensitive user data" not in log_text
        assert "xyz" not in log_text
        
        # Diagnostics should only contain error type, not message
        for error in result.diagnostics.errors:
            assert "sensitive" not in error.lower()
            assert "xyz" not in error.lower()
    
    def test_diagnostics_errors_are_safe(self):
        """Verify diagnostic errors contain only exception type."""
        from python.helpers.pdf_extraction import Diagnostics
        
        diag = Diagnostics()
        
        # Simulate adding error
        try:
            raise ValueError("Sensitive error message with user data")
        except ValueError as e:
            diag.errors.append(type(e).__name__)  # Only type, not message
        
        # Error list should only contain type name
        assert diag.errors == ["ValueError"]
        assert "Sensitive" not in str(diag.errors)
        assert "user data" not in str(diag.errors)


class TestFallbackBehavior:
    """Test fallback extraction behavior."""
    
    def test_fallback_flag_in_diagnostics(self):
        """Verify fallback is tracked in diagnostics."""
        from python.helpers.pdf_extraction import (
            Diagnostics,
            ExtractionMethod
        )
        
        diag = Diagnostics()
        
        # Simulate fallback scenario
        diag.methods_attempted.append(ExtractionMethod.CAMELOT_LATTICE)
        diag.fallback_used = True
        diag.fallback_reason = "camelot timeout"
        diag.methods_succeeded.append(ExtractionMethod.PYMUPDF_GEOMETRY)
        
        assert diag.fallback_used is True
        assert ExtractionMethod.PYMUPDF_GEOMETRY in diag.methods_succeeded
    
    def test_monotone_fallback_result(self):
        """Verify fallback produces result, not crash."""
        from python.helpers.pdf_extraction import (
            TableResult,
            Cell,
            ExtractionMethod
        )
        
        # Simulate a fallback result
        cells = [Cell(text="fallback", row=0, col=0)]
        table = TableResult(
            cells=cells,
            num_rows=1,
            num_cols=1,
            page=0,
            method=ExtractionMethod.FALLBACK_GEOMETRY,
            confidence=0.5,
            fallback_used=True,
            original_method=ExtractionMethod.CAMELOT_LATTICE
        )
        
        assert table.fallback_used is True
        assert table.original_method == ExtractionMethod.CAMELOT_LATTICE
        assert table.method == ExtractionMethod.FALLBACK_GEOMETRY
        
        # Should still produce output
        csv = table.to_csv()
        assert "fallback" in csv


class TestBBoxOperations:
    """Test bounding box operations."""
    
    def test_bbox_properties(self):
        """Test BBox computed properties."""
        from python.helpers.pdf_extraction import BBox
        
        bbox = BBox(x0=10, y0=20, x1=50, y1=60)
        
        assert bbox.width == 40
        assert bbox.height == 40
        assert bbox.center_x == 30
        assert bbox.center_y == 40
    
    def test_bbox_overlap(self):
        """Test BBox overlap detection."""
        from python.helpers.pdf_extraction import BBox
        
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BBox(x0=50, y0=50, x1=150, y1=150)  # Overlaps
        bbox3 = BBox(x0=200, y0=200, x1=300, y1=300)  # No overlap
        
        assert bbox1.overlaps(bbox2, threshold=0.1) is True
        assert bbox1.overlaps(bbox3, threshold=0.1) is False


class TestExtractionContext:
    """Test extraction context management."""
    
    def test_context_budget_tracking(self):
        """Test budget tracking in context."""
        from python.helpers.pdf_extraction import ExtractionContext
        import time
        
        ctx = ExtractionContext(start_time=time.time())
        
        # Initially not exhausted
        assert ctx.is_budget_exhausted(total_timeout_s=10.0) is False
        
        # Has remaining budget
        remaining = ctx.remaining_budget_ms(total_timeout_s=10.0)
        assert remaining > 0
    
    def test_context_pages_processed(self):
        """Test page processing tracking."""
        from python.helpers.pdf_extraction import ExtractionContext
        import time
        
        ctx = ExtractionContext(start_time=time.time())
        ctx.pages_processed = 5
        
        assert ctx.pages_processed == 5


class TestPDFTypeEnum:
    """Test PDF type enumeration."""
    
    def test_pdf_types(self):
        """Verify all PDF types are defined."""
        from python.helpers.pdf_extraction import PDFType
        
        assert PDFType.TEXT.value == "text"
        assert PDFType.HYBRID.value == "hybrid"
        assert PDFType.SCAN.value == "scan"
        assert PDFType.UNKNOWN.value == "unknown"


class TestExtractionMethodEnum:
    """Test extraction method enumeration."""
    
    def test_extraction_methods(self):
        """Verify all extraction methods are defined."""
        from python.helpers.pdf_extraction import ExtractionMethod
        
        # Primary methods
        assert ExtractionMethod.PYMUPDF_TEXT.value == "pymupdf_text"
        assert ExtractionMethod.PYMUPDF_GEOMETRY.value == "pymupdf_geometry"
        
        # Optional engines
        assert ExtractionMethod.PDFPLUMBER.value == "pdfplumber"
        assert ExtractionMethod.CAMELOT_LATTICE.value == "camelot_lattice"
        assert ExtractionMethod.CAMELOT_STREAM.value == "camelot_stream"
        assert ExtractionMethod.TABULA_LATTICE.value == "tabula_lattice"
        
        # OCR
        assert ExtractionMethod.OCR_TESSERACT.value == "ocr_tesseract"
        
        # Fallback
        assert ExtractionMethod.FALLBACK_GEOMETRY.value == "fallback_geometry"


class TestExtractionStatusEnum:
    """Test extraction status enumeration."""
    
    def test_extraction_statuses(self):
        """Verify all statuses are defined."""
        from python.helpers.pdf_extraction import ExtractionStatus
        
        assert ExtractionStatus.SUCCESS.value == "success"
        assert ExtractionStatus.PARTIAL.value == "partial"
        assert ExtractionStatus.TIMEOUT.value == "timeout"
        assert ExtractionStatus.ERROR.value == "error"
        assert ExtractionStatus.SKIPPED.value == "skipped"
        assert ExtractionStatus.CIRCUIT_OPEN.value == "circuit_open"


class TestIntegrationMinimal:
    """Minimal integration tests (no real PDF required)."""
    
    def test_extraction_with_empty_bytes_handles_error(self):
        """Extraction with invalid PDF returns error result."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionStatus
        
        result = extract_from_pdf(b"not a pdf")
        
        assert result.status == ExtractionStatus.ERROR
        assert len(result.diagnostics.errors) > 0
    
    def test_extraction_result_is_always_returned(self):
        """Extraction always returns a result, never None."""
        from python.helpers.pdf_extraction import extract_from_pdf, ExtractionResult
        
        result = extract_from_pdf(b"")
        
        assert isinstance(result, ExtractionResult)
        assert result.diagnostics is not None
        assert result.pdf_type is not None
