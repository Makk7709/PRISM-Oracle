"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF EXTRACTION - CONFIG TESTS                             ║
║                                                                              ║
║  Tests that verify configuration defaults are SAFE:                          ║
║  - Heavy engines OFF by default                                              ║
║  - OCR OFF by default                                                        ║
║  - Strict timeouts                                                           ║
║  - No log leakage                                                            ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest


class TestConfigDefaults:
    """Test that default configuration is safe."""
    
    def test_config_defaults_are_safe(self):
        """
        CRITICAL: Default config must be conservative.
        
        - pdfplumber: OFF (can hang)
        - camelot: OFF (requires poppler)
        - tabula: OFF (requires java)
        - OCR: OFF (expensive)
        - Budgets: strict
        """
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        # Heavy engines OFF by default
        assert config.tables.optional_engines.engines_enabled.get("pdfplumber") is False, \
            "pdfplumber MUST be OFF by default - it can hang!"
        assert config.tables.optional_engines.engines_enabled.get("camelot") is False, \
            "camelot should be OFF by default"
        assert config.tables.optional_engines.engines_enabled.get("tabula") is False, \
            "tabula should be OFF by default"
        
        # OCR OFF by default
        assert config.ocr.enabled is False, \
            "OCR MUST be OFF by default - expensive and slow"
        
        # Geometry reconstruction ON
        assert config.tables.geometry.enabled is True, \
            "Geometry reconstruction should be ON - it's the safe default"
        
        # Default strategy is geometry
        assert config.tables.default_strategy == "geometry", \
            "Default strategy should be geometry, not engine_first"
    
    def test_budgets_are_strict(self):
        """Verify timeouts are not too permissive."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        # Total timeout should be reasonable (not infinite)
        assert config.budgets.total_timeout_s <= 60, \
            f"Total timeout {config.budgets.total_timeout_s}s is too permissive"
        assert config.budgets.total_timeout_s >= 10, \
            f"Total timeout {config.budgets.total_timeout_s}s is too strict"
        
        # Per-page timeout
        assert config.budgets.per_page_timeout_s <= 10, \
            f"Per-page timeout {config.budgets.per_page_timeout_s}s is too permissive"
        
        # Engine timeout
        assert config.budgets.per_engine_timeout_s <= 15, \
            f"Engine timeout {config.budgets.per_engine_timeout_s}s is too permissive"
        
        # Page limit
        assert config.budgets.max_pages <= 100, \
            f"Max pages {config.budgets.max_pages} is too high"
        
        # Circuit breaker active
        assert config.budgets.circuit_breaker.max_timeouts <= 5, \
            "Circuit breaker should trip after few timeouts"
    
    def test_security_defaults(self):
        """Verify security settings prevent log leakage."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.security.never_log_user_content is True, \
            "MUST never log user content"
        assert config.security.never_log_raw_pdf_text is True, \
            "MUST never log raw PDF text"
        assert config.security.max_output_chars_preview == 0, \
            "No previews in logs by default"
        assert config.observability.redact_text_in_logs is True, \
            "Must redact text in logs"
    
    def test_strict_mode_enabled(self):
        """Verify strict mode is ON by default."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.strict_mode is True, \
            "Strict mode should be ON by default"
        assert config.verbosity == "silent", \
            "Verbosity should be silent by default"


class TestConfigPresets:
    """Test preset configurations."""
    
    def test_default_config_preset(self):
        """Default preset should match default constructor."""
        from python.helpers.pdf_extraction import (
            PDFExtractionConfig,
            get_default_config
        )
        
        preset = get_default_config()
        manual = PDFExtractionConfig()
        
        # Should have same safety settings
        assert preset.ocr.enabled == manual.ocr.enabled
        assert preset.tables.optional_engines.engines_enabled == \
               manual.tables.optional_engines.engines_enabled
    
    def test_thorough_config_enables_camelot(self):
        """Thorough preset enables camelot but with extended timeout."""
        from python.helpers.pdf_extraction import get_thorough_config
        
        config = get_thorough_config()
        
        assert config.is_engine_enabled("camelot") is True, \
            "Thorough config should enable camelot"
        assert config.budgets.total_timeout_s > 25, \
            "Thorough config should have extended timeout"
        
        # But pdfplumber still OFF
        assert config.is_engine_enabled("pdfplumber") is False, \
            "pdfplumber should still be OFF even in thorough mode"
    
    def test_scan_config_enables_ocr(self):
        """Scan preset enables OCR."""
        from python.helpers.pdf_extraction import get_scan_config
        
        config = get_scan_config()
        
        assert config.ocr.enabled is True, \
            "Scan config should enable OCR"
        assert "scan" in config.ocr.only_if_pdf_type, \
            "OCR should target scan PDFs"
    
    def test_fast_config_has_tight_budgets(self):
        """Fast preset has strict timeouts."""
        from python.helpers.pdf_extraction import get_fast_config, get_default_config
        
        fast = get_fast_config()
        default = get_default_config()
        
        assert fast.budgets.total_timeout_s < default.budgets.total_timeout_s, \
            "Fast config should have shorter timeout"
        assert fast.budgets.max_pages < default.budgets.max_pages, \
            "Fast config should process fewer pages"


class TestConfigMutability:
    """Test that config can be customized safely."""
    
    def test_can_enable_engine_safely(self):
        """Verify engines can be enabled without breaking defaults."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        # Enable camelot
        config.tables.optional_engines.engines_enabled["camelot"] = True
        
        assert config.is_engine_enabled("camelot") is True
        # Other engines still off
        assert config.is_engine_enabled("pdfplumber") is False
        assert config.is_engine_enabled("tabula") is False
    
    def test_can_enable_ocr_safely(self):
        """Verify OCR can be enabled."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        config.ocr.enabled = True
        
        assert config.ocr.enabled is True
        # Still targeted by default
        assert config.ocr.only_if_pdf_type == ["scan"]
    
    def test_budget_modification(self):
        """Verify budgets can be modified."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        config.budgets.total_timeout_s = 60.0
        config.budgets.max_pages = 100
        
        assert config.get_effective_timeout("total") == 60.0
        assert config.budgets.max_pages == 100


class TestConfigHelpers:
    """Test config helper methods."""
    
    def test_is_engine_enabled(self):
        """Test engine enabled check."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.is_engine_enabled("nonexistent") is False
        assert config.is_engine_enabled("pdfplumber") is False
        
        config.tables.optional_engines.engines_enabled["pdfplumber"] = True
        assert config.is_engine_enabled("pdfplumber") is True
    
    def test_get_effective_timeout(self):
        """Test timeout retrieval."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.get_effective_timeout("total") == config.budgets.total_timeout_s
        assert config.get_effective_timeout("page") == config.budgets.per_page_timeout_s
        assert config.get_effective_timeout("engine") == config.budgets.per_engine_timeout_s
        # Unknown defaults to per_page
        assert config.get_effective_timeout("unknown") == config.budgets.per_page_timeout_s


class TestGeometryConfig:
    """Test geometry reconstruction configuration."""
    
    def test_geometry_defaults(self):
        """Verify geometry config has reasonable defaults."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        geo = config.tables.geometry
        
        # Column detection
        assert geo.column_detection.x_cluster_eps > 0
        assert geo.column_detection.max_columns <= 20
        
        # Row detection
        assert geo.row_detection.y_cluster_eps > 0
        assert geo.row_detection.max_rows <= 500
        
        # Quality checks
        assert 0 < geo.quality_checks.min_fill_ratio < 1
        assert 0 < geo.quality_checks.min_consistent_columns_ratio < 1
    
    def test_postprocessing_defaults(self):
        """Verify postprocessing is enabled by default."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        post = config.tables.geometry.postprocessing
        
        assert post.merge_multiline_cells is True
        assert post.strip_currency_spacing is True
        assert post.fix_common_erp_artifacts is True


class TestOCRConfig:
    """Test OCR configuration."""
    
    def test_ocr_is_targeted_not_blind(self):
        """Verify OCR is targeted, not full-page blind."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.ocr.region_detection.enabled is True, \
            "Region detection should be ON - no blind OCR"
        assert config.ocr.region_detection.max_regions <= 5, \
            "Should limit OCR regions"
    
    def test_ocr_confidence_thresholds(self):
        """Verify OCR has confidence thresholds."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.ocr.min_confidence_to_accept > 0.5, \
            "Should require decent confidence to accept OCR"
        assert config.ocr.force_human_review_below > 0.5, \
            "Should flag low-confidence OCR for review"


class TestOutputConfig:
    """Test output configuration."""
    
    def test_output_formats_enabled(self):
        """Verify output formats are configurable."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert config.output.return_csv is True
        assert config.output.return_json_cells is True
        assert config.output.return_docx is True
    
    def test_provenance_included(self):
        """Verify provenance info is included."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        prov = config.output.include_provenance
        
        assert prov.page_number is True
        assert prov.extraction_method is True
        assert prov.confidence is True


class TestObservabilityConfig:
    """Test observability configuration."""
    
    def test_events_defined(self):
        """Verify events are defined for observability."""
        from python.helpers.pdf_extraction import PDFExtractionConfig
        
        config = PDFExtractionConfig()
        
        assert len(config.observability.events) > 0
        assert "pdf_classified" in config.observability.events
        assert "table_detected" in config.observability.events
        assert "engine_timeout" in config.observability.events
        assert "doc_done" in config.observability.events
