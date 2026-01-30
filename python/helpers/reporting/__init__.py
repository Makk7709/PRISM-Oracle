"""
Reporting module for long-form report generation.

- ReportJob: Manages report generation jobs
- ReportAssembler: Chunks and assembles reports
- EvidenceNativeReport: Evidence-native report generation
- Exporters: MD, PDF, HTML export
"""

from .report_job import (
    ReportJob,
    ReportStatus,
    ReportSection,
    ReportConfig,
    get_report_manager,
    create_report_job,
)

from .report_assembler import (
    ReportAssembler,
    ChunkGenerator,
    SectionOutline,
)

from .evidence_native import (
    # Enums
    Criticality,
    ValidationMode,
    GovernanceStatus,
    ConfidenceBadge,
    ImpactLevel,
    Probability,
    # Data classes
    DecisionGovernance,
    ClientContext,
    Scope,
    Source,
    Hypothesis,
    Risk,
    Alternative,
    Decision,
    Action,
    VerificationCommand,
    Limit,
    # Main classes
    EvidenceNativeReport,
    GenericReportTransformer,
    ReportValidator,
    ValidationResult,
)

__all__ = [
    # Report Job
    "ReportJob",
    "ReportStatus",
    "ReportSection",
    "ReportConfig",
    "get_report_manager",
    "create_report_job",
    # Report Assembler
    "ReportAssembler",
    "ChunkGenerator",
    "SectionOutline",
    # Evidence Native
    "Criticality",
    "ValidationMode",
    "GovernanceStatus",
    "ConfidenceBadge",
    "ImpactLevel",
    "Probability",
    "DecisionGovernance",
    "ClientContext",
    "Scope",
    "Source",
    "Hypothesis",
    "Risk",
    "Alternative",
    "Decision",
    "Action",
    "VerificationCommand",
    "Limit",
    "EvidenceNativeReport",
    "GenericReportTransformer",
    "ReportValidator",
    "ValidationResult",
]
