"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF EXTRACTION - TYPE DEFINITIONS                        ║
║                                                                              ║
║  Core data structures for PDF extraction pipeline.                          ║
║  All results are immutable, typed, and contain provenance info.             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional
import hashlib


# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class PDFType(str, Enum):
    """Classification of PDF based on content type."""
    TEXT = "text"          # Native text, no images/scans
    HYBRID = "hybrid"      # Mix of text and image content
    SCAN = "scan"          # Primarily scanned/image-based
    UNKNOWN = "unknown"    # Could not classify


class ExtractionMethod(str, Enum):
    """Method used to extract content."""
    PYMUPDF_TEXT = "pymupdf_text"
    PYMUPDF_GEOMETRY = "pymupdf_geometry"
    PDFPLUMBER = "pdfplumber"
    CAMELOT_LATTICE = "camelot_lattice"
    CAMELOT_STREAM = "camelot_stream"
    TABULA_LATTICE = "tabula_lattice"
    TABULA_STREAM = "tabula_stream"
    OCR_TESSERACT = "ocr_tesseract"
    OCR_EASYOCR = "ocr_easyocr"
    FALLBACK_GEOMETRY = "fallback_geometry"


class ExtractionStatus(str, Enum):
    """Status of an extraction operation."""
    SUCCESS = "success"
    PARTIAL = "partial"          # Some content extracted, not all
    TIMEOUT = "timeout"          # Operation timed out
    ERROR = "error"              # Unrecoverable error
    SKIPPED = "skipped"          # Intentionally skipped (e.g., engine disabled)
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker tripped


# ═══════════════════════════════════════════════════════════════════════════════
# BOUNDING BOX & WORD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BBox:
    """Bounding box coordinates (PDF units)."""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2
    
    def overlaps(self, other: "BBox", threshold: float = 0.0) -> bool:
        """Check if this bbox overlaps with another."""
        overlap_x = max(0, min(self.x1, other.x1) - max(self.x0, other.x0))
        overlap_y = max(0, min(self.y1, other.y1) - max(self.y0, other.y0))
        overlap_area = overlap_x * overlap_y
        min_area = min(self.width * self.height, other.width * other.height)
        if min_area == 0:
            return False
        return (overlap_area / min_area) >= threshold


@dataclass(frozen=True)
class Word:
    """A word with position information."""
    text: str
    bbox: BBox
    page: int
    confidence: float = 1.0  # 0-1, 1.0 for native text
    
    def __hash__(self):
        return hash((self.text, self.page, self.bbox.x0, self.bbox.y0))


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Cell:
    """A single table cell."""
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    bbox: Optional[BBox] = None
    is_header: bool = False
    confidence: float = 1.0


@dataclass
class TableResult:
    """Result of table extraction."""
    cells: list[Cell]
    num_rows: int
    num_cols: int
    page: int
    bbox: Optional[BBox] = None
    method: ExtractionMethod = ExtractionMethod.PYMUPDF_GEOMETRY
    confidence: float = 0.0
    
    # Quality metrics
    fill_ratio: float = 0.0        # % of cells with content
    jagged_rows_ratio: float = 0.0 # % of rows with inconsistent col count
    has_header: bool = False
    header_rows: int = 0
    
    # Provenance
    extraction_time_ms: int = 0
    fallback_used: bool = False
    original_method: Optional[ExtractionMethod] = None
    
    def to_rows(self) -> list[list[str]]:
        """Convert cells to row-major 2D list."""
        if not self.cells:
            return []
        rows: list[list[str]] = [[""] * self.num_cols for _ in range(self.num_rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.num_rows and 0 <= cell.col < self.num_cols:
                rows[cell.row][cell.col] = cell.text
        return rows
    
    def to_csv(self, delimiter: str = ",") -> str:
        """Convert table to CSV string."""
        import csv
        import io
        rows = self.to_rows()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerows(rows)
        return output.getvalue()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "rows": self.to_rows(),
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "page": self.page,
            "bbox": {"x0": self.bbox.x0, "y0": self.bbox.y0, 
                     "x1": self.bbox.x1, "y1": self.bbox.y1} if self.bbox else None,
            "method": self.method.value,
            "confidence": self.confidence,
            "fill_ratio": self.fill_ratio,
            "has_header": self.has_header,
            "header_rows": self.header_rows,
        }


# DIAGNOSTICS & PROVENANCE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TimingInfo:
    """Timing information for a single operation."""
    operation: str
    duration_ms: int
    status: ExtractionStatus
    page: Optional[int] = None
    engine: Optional[str] = None


@dataclass
class CircuitBreakerState:
    """State of the circuit breaker."""
    is_open: bool = False
    timeout_count: int = 0
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    disabled_engines: list[str] = field(default_factory=list)


@dataclass
class Diagnostics:
    """Diagnostic information for an extraction run."""
    # Timings
    total_time_ms: int = 0
    classification_time_ms: int = 0
    text_extraction_time_ms: int = 0
    table_extraction_time_ms: int = 0
    ocr_time_ms: int = 0
    output_generation_time_ms: int = 0
    
    # Counts
    page_count: int = 0
    word_count: int = 0
    table_count: int = 0
    ocr_region_count: int = 0
    
    # Status
    methods_attempted: list[ExtractionMethod] = field(default_factory=list)
    methods_succeeded: list[ExtractionMethod] = field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    
    # Errors (no sensitive content)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Circuit breaker
    circuit_breaker: CircuitBreakerState = field(default_factory=CircuitBreakerState)
    
    # Per-operation timings
    timings: list[TimingInfo] = field(default_factory=list)
    
    def add_timing(self, operation: str, duration_ms: int, 
                   status: ExtractionStatus, page: Optional[int] = None,
                   engine: Optional[str] = None):
        """Add a timing entry."""
        self.timings.append(TimingInfo(
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            page=page,
            engine=engine
        ))
    
    def to_safe_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict (no sensitive info)."""
        return {
            "total_time_ms": self.total_time_ms,
            "classification_time_ms": self.classification_time_ms,
            "text_extraction_time_ms": self.text_extraction_time_ms,
            "table_extraction_time_ms": self.table_extraction_time_ms,
            "ocr_time_ms": self.ocr_time_ms,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "table_count": self.table_count,
            "methods_attempted": [m.value for m in self.methods_attempted],
            "methods_succeeded": [m.value for m in self.methods_succeeded],
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "circuit_breaker_open": self.circuit_breaker.is_open,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OutputArtifacts:
    """Generated output files/data."""
    csv_data: Optional[str] = None          # CSV string
    json_data: Optional[dict] = None        # JSON-serializable dict
    docx_bytes: Optional[bytes] = None      # DOCX binary
    
    # File paths if saved
    csv_path: Optional[str] = None
    json_path: Optional[str] = None
    docx_path: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionResult:
    """
    Complete result of PDF extraction.
    
    This is the main return type of the extraction pipeline.
    Contains all extracted content, metadata, and diagnostics.
    """
    # Classification
    pdf_type: PDFType
    pdf_type_confidence: float
    
    # Extracted content
    text: Optional[str] = None              # Full text (if requested)
    words: list[Word] = field(default_factory=list)
    tables: list[TableResult] = field(default_factory=list)
    
    # Output artifacts
    outputs: OutputArtifacts = field(default_factory=OutputArtifacts)
    
    # Diagnostics (safe, no sensitive content)
    diagnostics: Diagnostics = field(default_factory=Diagnostics)
    
    # Quality indicators
    confidence_overall: float = 0.0         # 0-1 aggregate confidence
    requires_human_review: bool = False     # True if low confidence
    review_reasons: list[str] = field(default_factory=list)
    
    # Document hash (for tracing, not content)
    document_hash: Optional[str] = None
    
    # Status
    status: ExtractionStatus = ExtractionStatus.SUCCESS
    
    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Compute SHA-256 hash of document."""
        return hashlib.sha256(data).hexdigest()[:16]
    
    def is_successful(self) -> bool:
        """Check if extraction was successful or partial."""
        return self.status in (ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL)
    
    def summary(self) -> dict[str, Any]:
        """Return a summary dict for logging (no sensitive content)."""
        return {
            "status": self.status.value,
            "pdf_type": self.pdf_type.value,
            "pdf_type_confidence": round(self.pdf_type_confidence, 2),
            "confidence_overall": round(self.confidence_overall, 2),
            "requires_human_review": self.requires_human_review,
            "page_count": self.diagnostics.page_count,
            "table_count": len(self.tables),
            "word_count": len(self.words),
            "total_time_ms": self.diagnostics.total_time_ms,
            "fallback_used": self.diagnostics.fallback_used,
            "document_hash": self.document_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION CONTEXT (runtime state)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionContext:
    """
    Runtime context for extraction.
    Tracks state, budgets, and circuit breaker across operations.
    """
    # Budget tracking
    start_time: float = 0.0
    elapsed_ms: int = 0
    pages_processed: int = 0
    backtracks_used: int = 0
    
    # Circuit breaker state
    circuit_breaker: CircuitBreakerState = field(default_factory=CircuitBreakerState)
    
    # Correlation ID for logs
    correlation_id: Optional[str] = None
    
    def is_budget_exhausted(self, total_timeout_s: float) -> bool:
        """Check if total budget is exhausted."""
        import time
        elapsed = (time.time() - self.start_time) * 1000
        return elapsed >= (total_timeout_s * 1000)
    
    def remaining_budget_ms(self, total_timeout_s: float) -> int:
        """Get remaining time budget in ms."""
        import time
        elapsed = (time.time() - self.start_time) * 1000
        remaining = (total_timeout_s * 1000) - elapsed
        return max(0, int(remaining))
