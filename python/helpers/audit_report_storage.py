"""
SESSION 9+10 — Stockage du rapport d'audit (MD + PDF) + retention.

Point d'entree unique pour persister le rapport d'audit Evidence sur disque.
Le rapport est stocke dans le meme dossier que chat.json, ce qui garantit :
  - meme ACL que chat.json (authorization via use_context)
  - suppression automatique au chat_remove (delete_dir sur le dossier)

Fichiers generes :
  - tmp/chats/{ctxid}/audit_report.md
  - tmp/chats/{ctxid}/audit_report.pdf  (si WeasyPrint disponible)

SESSION 10 — Politique de retention :
  - purge_expired_reports() supprime les dossiers de chat dont les rapports
    datent de plus de EVIDENCE_RETENTION_DAYS (defaut 1825 = 5 ans).
  - Appelee periodiquement par le job_loop (garde journaliere).

Fail-safe : toute exception est absorbee — la reponse est toujours livree.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import List, Optional

logger = logging.getLogger("audit_report_storage")

AUDIT_REPORT_MD = "audit_report.md"
AUDIT_REPORT_PDF = "audit_report.pdf"
DEFAULT_RETENTION_DAYS = 1825  # 5 years


def resolve_chat_folder(context_id: str) -> str:
    """Resolve the chat folder path for a context ID.

    Deferred import to avoid pulling in the full agent dependency chain
    (persist_chat -> agent -> models -> whisper).
    """
    from python.helpers.persist_chat import get_chat_folder_path
    return get_chat_folder_path(context_id)


def store_audit_report(
    context_id: str,
    report_markdown: str,
    *,
    generate_pdf: bool = True,
    folder_override: Optional[str] = None,
) -> Optional[str]:
    """Persist the audit report to the chat folder.

    Args:
        context_id: The chat context ID.
        report_markdown: Full audit report as markdown.
        generate_pdf: Whether to also generate a PDF version.
        folder_override: If set, write to this folder instead of resolving
            from context_id. Useful for testing.

    Returns the path to the stored MD file, or None on failure.
    """
    if not context_id or not report_markdown:
        return None

    t0 = time.monotonic()
    try:
        folder = folder_override or resolve_chat_folder(context_id)
        md_path = os.path.join(folder, AUDIT_REPORT_MD)

        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        logger.info("Audit report stored: %s", md_path)

        if generate_pdf:
            _generate_pdf(folder, report_markdown)

        _emit_metrics(True, time.monotonic() - t0, len(report_markdown))
        return md_path

    except Exception as exc:
        logger.error("store_audit_report failed (non-blocking): %s", exc)
        _emit_metrics(False, time.monotonic() - t0, 0)
        return None


def _emit_metrics(success: bool, elapsed_s: float, size_bytes: int) -> None:
    """Best-effort observability metrics for audit report generation."""
    try:
        from python.observability.runtime import ObservabilityMetrics
        m = ObservabilityMetrics.get()
        if success:
            m.incr("audit_reports_generated_total")
            m.incr("audit_report_generation_ms_total", int(elapsed_s * 1000))
            m.incr("audit_report_size_bytes_total", size_bytes)
        else:
            m.incr("audit_reports_failed_total")
    except Exception:
        pass


def _generate_pdf(folder: str, report_markdown: str) -> None:
    """Best-effort PDF generation alongside the MD file."""
    try:
        from python.helpers.evidence_pdf_engine import markdown_to_pdf

        pdf_path = os.path.join(folder, AUDIT_REPORT_PDF)
        markdown_to_pdf(
            content=report_markdown,
            output_path=pdf_path,
            title="Rapport d'audit Evidence",
            header_right="Audit Report",
        )
        logger.info("Audit PDF generated: %s", pdf_path)
    except Exception as exc:
        logger.warning("PDF generation failed (non-blocking): %s", exc)


def _get_chats_base_dir() -> str:
    """Base directory containing all chat folders."""
    return os.path.join("tmp", "chats")


def purge_expired_reports(
    *,
    max_age_days: Optional[int] = None,
    chats_dir_override: Optional[str] = None,
) -> List[str]:
    """Delete chat folders whose audit reports are older than max_age_days.

    Only deletes folders that actually contain an audit report (audit_report.md).
    This preserves chats that never generated an audit report.

    Returns list of deleted folder paths.
    """
    if max_age_days is None:
        max_age_days = int(os.environ.get("EVIDENCE_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)))

    chats_dir = chats_dir_override or _get_chats_base_dir()
    if not os.path.isdir(chats_dir):
        return []

    now = time.time()
    max_age_seconds = max_age_days * 86400
    deleted: List[str] = []

    try:
        for entry in os.listdir(chats_dir):
            folder = os.path.join(chats_dir, entry)
            if not os.path.isdir(folder):
                continue

            report_path = os.path.join(folder, AUDIT_REPORT_MD)
            if not os.path.isfile(report_path):
                continue

            mtime = os.path.getmtime(report_path)
            age_seconds = now - mtime
            if age_seconds > max_age_seconds:
                try:
                    shutil.rmtree(folder)
                    deleted.append(folder)
                    logger.info("Retention purge: deleted %s (age: %d days)",
                                folder, int(age_seconds / 86400))
                except Exception as exc:
                    logger.warning("Retention purge failed for %s: %s", folder, exc)
    except Exception as exc:
        logger.error("purge_expired_reports scan failed: %s", exc)

    if deleted:
        _emit_metrics_purge(len(deleted))

    return deleted


def _emit_metrics_purge(count: int) -> None:
    try:
        from python.observability.runtime import ObservabilityMetrics
        m = ObservabilityMetrics.get()
        m.incr("audit_reports_purged_total", count)
    except Exception:
        pass
