"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PDF EXTRACTION MODULE                                     ║
║                                                                              ║
║  Robust, non-blocking PDF extraction for KOREV Evidence.                       ║
║                                                                              ║
║  Quick Start:                                                                ║
║  ```python                                                                   ║
║  from python.helpers.pdf_extraction import extract_from_pdf                  ║
║                                                                              ║
║  result = extract_from_pdf("document.pdf")                                   ║
║  for table in result.tables:                                                 ║
║      print(table.to_csv())                                                   ║
║  ```                                                                         ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# Types
from .types import (
    # Enums
    PDFType,
    ExtractionMethod,
    ExtractionStatus,
    # Data structures
    BBox,
    Word,
    Cell,
    TableResult,
    # Results
    Diagnostics,
    OutputArtifacts,
    ExtractionResult,
    ExtractionContext,
    CircuitBreakerState,
    TimingInfo,
)

# Config
from .config import (
    # Main config
    PDFExtractionConfig,
    # Sub-configs
    BudgetConfig,
    CircuitBreakerConfig,
    PDFClassificationConfig,
    TextExtractionConfig,
    TableExtractionConfig,
    GeometryReconstructionConfig,
    OptionalEnginesConfig,
    OCRConfig,
    OutputConfig,
    ObservabilityConfig,
    SecurityConfig,
    # Presets
    get_default_config,
    get_thorough_config,
    get_scan_config,
    get_fast_config,
)

# Pipeline
from .pipeline import (
    extract_from_pdf,
    extract_from_pdf_async,
)


__all__ = [
    # Types
    "PDFType",
    "ExtractionMethod",
    "ExtractionStatus",
    "BBox",
    "Word",
    "Cell",
    "TableResult",
    "Diagnostics",
    "OutputArtifacts",
    "ExtractionResult",
    "ExtractionContext",
    "CircuitBreakerState",
    "TimingInfo",
    # Config
    "PDFExtractionConfig",
    "BudgetConfig",
    "CircuitBreakerConfig",
    "PDFClassificationConfig",
    "TextExtractionConfig",
    "TableExtractionConfig",
    "GeometryReconstructionConfig",
    "OptionalEnginesConfig",
    "OCRConfig",
    "OutputConfig",
    "ObservabilityConfig",
    "SecurityConfig",
    "get_default_config",
    "get_thorough_config",
    "get_scan_config",
    "get_fast_config",
    # Pipeline
    "extract_from_pdf",
    "extract_from_pdf_async",
]
