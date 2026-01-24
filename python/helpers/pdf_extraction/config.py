"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF EXTRACTION - ROLLS-ROYCE CONFIG                       ║
║                                                                              ║
║  Centralized, typed configuration for robust PDF extraction.                 ║
║  Defaults are conservative: safe, fast, non-blocking.                        ║
║                                                                              ║
║  Key Principles:                                                             ║
║  - No infinite loops or unbounded operations                                 ║
║  - Circuit breaker prevents cascade failures                                 ║
║  - Heavy engines (pdfplumber, OCR) OFF by default                            ║
║  - Geometry reconstruction as safe default                                   ║
║  - All operations timeboxed                                                  ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Literal


# ═══════════════════════════════════════════════════════════════════════════════
# B) BUDGET CONFIG - Anti-freeze protection
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CircuitBreakerConfig:
    """
    Circuit breaker settings to prevent cascade failures.
    
    When too many timeouts/failures occur, heavy engines are disabled
    automatically to maintain overall throughput.
    """
    max_timeouts: int = 2
    """If N timeouts occur, disable heavy engines for this document."""
    
    max_engine_failures: int = 3
    """If an engine fails N times across documents, disable it temporarily."""
    
    failure_cooldown_s: float = 60.0
    """Seconds before re-enabling a failed engine."""


@dataclass
class BudgetConfig:
    """
    Resource budgets to prevent blocking.
    
    All heavy operations MUST respect these limits.
    No operation should ever run unbounded.
    """
    total_timeout_s: float = 25.0
    """Maximum total time per document (seconds)."""
    
    per_page_timeout_s: float = 4.0
    """Maximum time for any heavy step per page (seconds)."""
    
    per_engine_timeout_s: float = 6.0
    """Maximum time for external engines: pdfplumber/camelot/tabula/ocr (seconds)."""
    
    max_pages: int = 40
    """Hard cap on pages to process. Beyond this, truncate with warning."""
    
    max_table_regions_per_page: int = 4
    """Maximum table regions to process per page."""
    
    max_cells_per_table: int = 3000
    """Maximum cells per table. Beyond this, mark as too complex."""
    
    max_backtracks: int = 1
    """Maximum strategy retries (e.g., geometry -> engine -> geometry)."""
    
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    """Circuit breaker configuration."""


# ═══════════════════════════════════════════════════════════════════════════════
# C) PDF CLASSIFICATION CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassificationHeuristics:
    """Heuristics for classifying PDF type."""
    min_chars_per_page_for_text_pdf: int = 150
    """Minimum chars/page to consider as text PDF."""
    
    min_word_count_per_page: int = 40
    """Minimum words/page for text classification."""
    
    image_area_ratio_scan_threshold: float = 0.55
    """If images cover > N% of page area, likely a scan."""
    
    max_empty_text_pages_ratio: float = 0.35
    """If > N% pages have no text, likely a scan."""


@dataclass
class ClassificationConfidenceThresholds:
    """Confidence thresholds for classification."""
    confident: float = 0.75
    """Above this, classification is confident."""
    
    uncertain: float = 0.45
    """Below this, flag for human review."""


@dataclass
class PDFClassificationConfig:
    """Configuration for PDF type classification."""
    enabled: bool = True
    """Enable automatic classification."""
    
    heuristics: ClassificationHeuristics = field(default_factory=ClassificationHeuristics)
    """Classification heuristics."""
    
    confidence_thresholds: ClassificationConfidenceThresholds = field(
        default_factory=ClassificationConfidenceThresholds
    )
    """Confidence thresholds."""


# ═══════════════════════════════════════════════════════════════════════════════
# D) TEXT EXTRACTION CONFIG (PyMuPDF)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BlockMergeConfig:
    """Configuration for merging text blocks."""
    enabled: bool = True
    """Enable block merging for better reading order."""
    
    y_tolerance: float = 2.0
    """Y-coordinate tolerance for same-line detection (points)."""
    
    x_gap_tolerance: float = 3.0
    """X-gap tolerance for word grouping (points)."""


@dataclass
class TextExtractionConfig:
    """
    Configuration for text extraction using PyMuPDF.
    
    PyMuPDF is always the primary engine - fast, reliable, no external deps.
    """
    engine: Literal["pymupdf"] = "pymupdf"
    """Text extraction engine (only pymupdf supported)."""
    
    extract_words: bool = True
    """Extract words with bounding boxes."""
    
    preserve_ligatures: bool = False
    """Preserve ligatures (fi, fl, etc.) vs expand them."""
    
    normalize_whitespace: bool = True
    """Normalize multiple spaces/tabs to single space."""
    
    keep_bbox: bool = True
    """Keep bounding box info for each word."""
    
    page_rotation_correction: bool = True
    """Auto-correct page rotation if detected."""
    
    sort_words_reading_order: bool = True
    """Sort words in reading order (top-to-bottom, left-to-right)."""
    
    block_merge: BlockMergeConfig = field(default_factory=BlockMergeConfig)
    """Block merge settings."""


# ═══════════════════════════════════════════════════════════════════════════════
# E) TABLE EXTRACTION CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

# E.1) Geometry Reconstruction (PyMuPDF-only) - DEFAULT SAFE PATH
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColumnDetectionConfig:
    """Column detection settings for geometry reconstruction."""
    method: Literal["cluster_x", "anchors"] = "cluster_x"
    """Method: cluster_x (DBSCAN-like) or anchors (header-based)."""
    
    x_cluster_eps: float = 7.0
    """X-coordinate clustering epsilon (points). Tuned conservative."""
    
    min_column_gap_px: float = 14.0
    """Minimum gap between columns (points)."""
    
    max_columns: int = 16
    """Maximum columns to detect. Beyond this, skip table."""


@dataclass
class RowDetectionConfig:
    """Row detection settings for geometry reconstruction."""
    y_cluster_eps: float = 6.0
    """Y-coordinate clustering epsilon (points)."""
    
    min_row_gap_px: float = 10.0
    """Minimum gap between rows (points)."""
    
    max_rows: int = 200
    """Maximum rows to detect. Beyond this, skip table."""


@dataclass
class CellAssignmentConfig:
    """Cell assignment settings."""
    method: Literal["bbox_intersection", "nearest_center"] = "bbox_intersection"
    """Assignment method."""
    
    overlap_threshold: float = 0.25
    """Minimum overlap ratio for cell assignment."""


@dataclass
class HeaderDetectionConfig:
    """Header detection settings."""
    enabled: bool = True
    """Enable automatic header detection."""
    
    max_header_rows: int = 3
    """Maximum rows that can be headers."""


@dataclass
class GeometryPostprocessingConfig:
    """Postprocessing settings for geometry reconstruction."""
    merge_multiline_cells: bool = True
    """Merge cells split across lines."""
    
    join_token_separator: str = " "
    """Separator when joining tokens."""
    
    strip_currency_spacing: bool = True
    """Remove extra spaces in currency values (e.g., '1 000' -> '1000')."""
    
    fix_common_erp_artifacts: bool = True
    """Fix common ERP export artifacts."""


@dataclass
class GeometryQualityChecksConfig:
    """Quality check thresholds for geometry reconstruction."""
    min_fill_ratio: float = 0.35
    """Minimum % of cells with content. Below this = low confidence."""
    
    max_jagged_rows_ratio: float = 0.25
    """Maximum % of rows with inconsistent column count."""
    
    min_consistent_columns_ratio: float = 0.70
    """Minimum % of rows with same column count."""


@dataclass
class GeometryReconstructionConfig:
    """
    Configuration for PyMuPDF-only geometry reconstruction.
    
    This is the DEFAULT and SAFE path. Uses only word positions
    to reconstruct table structure. No external dependencies,
    no blocking, fast execution.
    """
    enabled: bool = True
    """Enable geometry reconstruction."""
    
    column_detection: ColumnDetectionConfig = field(default_factory=ColumnDetectionConfig)
    """Column detection settings."""
    
    row_detection: RowDetectionConfig = field(default_factory=RowDetectionConfig)
    """Row detection settings."""
    
    cell_assignment: CellAssignmentConfig = field(default_factory=CellAssignmentConfig)
    """Cell assignment settings."""
    
    header_detection: HeaderDetectionConfig = field(default_factory=HeaderDetectionConfig)
    """Header detection settings."""
    
    postprocessing: GeometryPostprocessingConfig = field(
        default_factory=GeometryPostprocessingConfig
    )
    """Postprocessing settings."""
    
    quality_checks: GeometryQualityChecksConfig = field(
        default_factory=GeometryQualityChecksConfig
    )
    """Quality check thresholds."""


# E.2) Optional Engines - BOUNDED, OPT-IN
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PdfplumberConfig:
    """
    pdfplumber configuration.
    
    WARNING: pdfplumber can hang on complex PDFs!
    Only enable if you need it and have proper timeouts.
    """
    table_settings_profile: Literal["strict", "balanced"] = "strict"
    """Settings profile. 'strict' is more conservative."""
    
    max_tables_per_page: int = 2
    """Maximum tables to extract per page."""


@dataclass
class CamelotConfig:
    """Camelot configuration."""
    flavor_order: list[str] = field(default_factory=lambda: ["lattice", "stream"])
    """Order to try flavors. Lattice first if lines exist."""
    
    line_scale: int = 40
    """Line detection scale."""
    
    strip_text: str = "\n"
    """Characters to strip from cells."""


@dataclass
class TabulaConfig:
    """Tabula configuration."""
    lattice: bool = True
    """Try lattice mode."""
    
    stream: bool = True
    """Try stream mode."""


@dataclass
class EngineSelectionConfig:
    """Rules for when to use optional engines."""
    only_if_pdf_type_in: list[str] = field(default_factory=lambda: ["text", "hybrid"])
    """Only use engines if PDF type is in this list."""
    
    require_detected_lines_for_lattice: bool = True
    """Require detected lines before trying lattice mode."""


@dataclass
class OptionalEnginesConfig:
    """
    Configuration for optional table extraction engines.
    
    CRITICAL: All engines run under strict timeouts!
    If an engine times out, fallback to geometry reconstruction.
    
    Default state: pdfplumber OFF, camelot OFF, tabula OFF.
    These are OPT-IN for specific use cases.
    """
    engines_enabled: dict[str, bool] = field(default_factory=lambda: {
        "pdfplumber": False,  # OFF by default - known to hang
        "camelot": False,     # OFF by default - requires poppler
        "tabula": False,      # OFF by default - requires java
    })
    """Which engines are enabled. ALL OFF by default."""
    
    pdfplumber: PdfplumberConfig = field(default_factory=PdfplumberConfig)
    """pdfplumber-specific settings."""
    
    camelot: CamelotConfig = field(default_factory=CamelotConfig)
    """Camelot-specific settings."""
    
    tabula: TabulaConfig = field(default_factory=TabulaConfig)
    """Tabula-specific settings."""
    
    engine_selection: EngineSelectionConfig = field(default_factory=EngineSelectionConfig)
    """Rules for engine selection."""


@dataclass
class TableExtractionConfig:
    """
    Master configuration for table extraction.
    
    Strategy:
    1. Always try geometry reconstruction first (fast, safe)
    2. If quality is low AND optional engines enabled, try them (bounded)
    3. If all fail, return best-effort geometry result
    """
    enabled: bool = True
    """Enable table extraction."""
    
    default_strategy: Literal["geometry", "engine_first"] = "geometry"
    """Default strategy. 'geometry' is the safe default."""
    
    geometry: GeometryReconstructionConfig = field(
        default_factory=GeometryReconstructionConfig
    )
    """Geometry reconstruction config (PyMuPDF-only)."""
    
    optional_engines: OptionalEnginesConfig = field(
        default_factory=OptionalEnginesConfig
    )
    """Optional engine configs (bounded, opt-in)."""


# ═══════════════════════════════════════════════════════════════════════════════
# F) OCR CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OCRRegionDetectionConfig:
    """Configuration for OCR region detection."""
    enabled: bool = True
    """Enable automatic region detection."""
    
    strategy: Literal["table_like_blocks", "manual_regions"] = "table_like_blocks"
    """Region detection strategy."""
    
    max_regions: int = 3
    """Maximum regions to OCR per page."""


@dataclass
class OCRConfig:
    """
    Configuration for OCR.
    
    OCR is DISABLED by default. It's expensive, slow, and often unnecessary.
    Only enable for scanned PDFs when text extraction fails.
    
    When enabled, OCR is:
    - Targeted to specific regions (not full-page blind OCR)
    - Timeboxed
    - Confidence-scored
    """
    enabled: bool = False
    """Enable OCR. OFF by default - expensive and slow."""
    
    only_if_pdf_type: list[str] = field(default_factory=lambda: ["scan"])
    """Only run OCR if PDF type is in this list."""
    
    region_detection: OCRRegionDetectionConfig = field(
        default_factory=OCRRegionDetectionConfig
    )
    """Region detection settings."""
    
    ocr_engine: Literal["tesseract", "easyocr"] = "tesseract"
    """OCR engine to use."""
    
    min_confidence_to_accept: float = 0.80
    """Minimum confidence to accept OCR result."""
    
    force_human_review_below: float = 0.70
    """Force human review if confidence below this."""


# ═══════════════════════════════════════════════════════════════════════════════
# G) OUTPUT CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DocxOutputConfig:
    """DOCX output settings."""
    table_style: str = "Table Grid"
    """Word table style name."""
    
    header_bold: bool = True
    """Bold header rows."""
    
    font_name: str = "Calibri"
    """Font name."""
    
    font_size_pt: int = 10
    """Font size in points."""


@dataclass
class ProvenanceConfig:
    """What provenance info to include in output."""
    page_number: bool = True
    bbox: bool = True
    extraction_method: bool = True
    pdf_type: bool = True
    confidence: bool = True


@dataclass
class OutputConfig:
    """Configuration for output generation."""
    return_csv: bool = True
    """Generate CSV output."""
    
    return_json_cells: bool = True
    """Generate JSON output with cell data."""
    
    return_docx: bool = True
    """Generate DOCX output."""
    
    docx: DocxOutputConfig = field(default_factory=DocxOutputConfig)
    """DOCX-specific settings."""
    
    include_provenance: ProvenanceConfig = field(default_factory=ProvenanceConfig)
    """Provenance info to include."""


# ═══════════════════════════════════════════════════════════════════════════════
# H) OBSERVABILITY CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ObservabilityConfig:
    """
    Configuration for observability and logging.
    
    All logs are SAFE - no user content, no raw text, only metrics.
    """
    enabled: bool = True
    """Enable observability."""
    
    structured_logs: bool = True
    """Use structured (JSON) logging."""
    
    include_timings: bool = True
    """Include timing information."""
    
    include_counts: bool = True
    """Include count metrics."""
    
    redact_text_in_logs: bool = True
    """Redact any text content in logs."""
    
    correlation_id_header: str = "X-Correlation-ID"
    """HTTP header for correlation ID."""
    
    events: list[str] = field(default_factory=lambda: [
        "pdf_classified",
        "text_extracted",
        "table_detected",
        "table_built",
        "engine_timeout",
        "fallback_used",
        "doc_done",
    ])
    """Events to emit."""


# ═══════════════════════════════════════════════════════════════════════════════
# I) SECURITY CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SecurityConfig:
    """
    Security configuration.
    
    CRITICAL: No user content in logs, ever.
    """
    never_log_user_content: bool = True
    """Never log user-provided content."""
    
    never_log_raw_pdf_text: bool = True
    """Never log raw text from PDFs."""
    
    store_only_hashes: bool = True
    """Store document hashes only, not content."""
    
    max_output_chars_preview: int = 0
    """Max chars to preview in logs. 0 = no previews."""


# ═══════════════════════════════════════════════════════════════════════════════
# A) ROOT CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PDFExtractionConfig:
    """
    Root configuration for PDF extraction.
    
    This is the "Rolls-Royce" config - everything is typed, documented,
    and has safe defaults.
    
    Default behavior:
    - Text extraction via PyMuPDF (fast, safe)
    - Table extraction via geometry reconstruction (fast, safe)
    - No optional engines (pdfplumber/camelot/tabula OFF)
    - No OCR (OFF)
    - Strict timeouts on everything
    - Circuit breaker prevents cascade failures
    - No user content in logs
    
    Example usage:
    ```python
    from python.helpers.pdf_extraction.config import PDFExtractionConfig
    
    # Use defaults (safe)
    config = PDFExtractionConfig()
    
    # Enable camelot for better table detection
    config = PDFExtractionConfig()
    config.tables.optional_engines.engines_enabled["camelot"] = True
    
    # Enable OCR for scanned PDFs
    config = PDFExtractionConfig()
    config.ocr.enabled = True
    ```
    """
    enabled: bool = True
    """Enable PDF extraction."""
    
    strict_mode: bool = True
    """Strict mode: always provide proof + score, never promises."""
    
    verbosity: Literal["silent", "normal", "debug"] = "silent"
    """Log verbosity level."""
    
    # Sub-configs
    budgets: BudgetConfig = field(default_factory=BudgetConfig)
    """Resource budgets (timeouts, limits)."""
    
    classification: PDFClassificationConfig = field(
        default_factory=PDFClassificationConfig
    )
    """PDF classification config."""
    
    text: TextExtractionConfig = field(default_factory=TextExtractionConfig)
    """Text extraction config."""
    
    tables: TableExtractionConfig = field(default_factory=TableExtractionConfig)
    """Table extraction config."""
    
    ocr: OCRConfig = field(default_factory=OCRConfig)
    """OCR config."""
    
    output: OutputConfig = field(default_factory=OutputConfig)
    """Output format config."""
    
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    """Observability/logging config."""
    
    security: SecurityConfig = field(default_factory=SecurityConfig)
    """Security config."""
    
    def is_engine_enabled(self, engine: str) -> bool:
        """Check if an optional engine is enabled."""
        return self.tables.optional_engines.engines_enabled.get(engine, False)
    
    def get_effective_timeout(self, operation: str) -> float:
        """Get effective timeout for an operation."""
        if operation == "total":
            return self.budgets.total_timeout_s
        elif operation == "page":
            return self.budgets.per_page_timeout_s
        elif operation == "engine":
            return self.budgets.per_engine_timeout_s
        else:
            return self.budgets.per_page_timeout_s


# ═══════════════════════════════════════════════════════════════════════════════
# PRESET CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_config() -> PDFExtractionConfig:
    """
    Get the default "Rolls-Royce" configuration.
    
    This is the safest, fastest configuration:
    - Only PyMuPDF (no external engines)
    - No OCR
    - Strict timeouts
    """
    return PDFExtractionConfig()


def get_thorough_config() -> PDFExtractionConfig:
    """
    Get a more thorough configuration.
    
    Enables camelot for better table detection, but still bounded.
    Use when you need higher accuracy and can afford more time.
    """
    config = PDFExtractionConfig()
    config.budgets.total_timeout_s = 45.0
    config.budgets.per_engine_timeout_s = 10.0
    config.tables.optional_engines.engines_enabled["camelot"] = True
    return config


def get_scan_config() -> PDFExtractionConfig:
    """
    Get configuration optimized for scanned PDFs.
    
    Enables OCR, extends timeouts.
    """
    config = PDFExtractionConfig()
    config.budgets.total_timeout_s = 60.0
    config.budgets.per_page_timeout_s = 8.0
    config.ocr.enabled = True
    config.ocr.only_if_pdf_type = ["scan", "hybrid"]
    return config


def get_fast_config() -> PDFExtractionConfig:
    """
    Get a fast configuration for high-throughput scenarios.
    
    Tighter timeouts, fewer pages.
    """
    config = PDFExtractionConfig()
    config.budgets.total_timeout_s = 10.0
    config.budgets.per_page_timeout_s = 2.0
    config.budgets.max_pages = 20
    config.output.return_docx = False  # Skip DOCX generation
    return config
