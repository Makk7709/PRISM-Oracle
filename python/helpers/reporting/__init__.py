"""
Reporting module for long-form report generation.

- ReportJob: Manages report generation jobs
- ReportAssembler: Chunks and assembles reports
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

__all__ = [
    "ReportJob",
    "ReportStatus",
    "ReportSection",
    "ReportConfig",
    "get_report_manager",
    "create_report_job",
    "ReportAssembler",
    "ChunkGenerator",
    "SectionOutline",
]
