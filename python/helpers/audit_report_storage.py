"""
SESSION 9 — Stockage du rapport d'audit (MD + PDF).

Point d'entree unique pour persister le rapport d'audit Evidence sur disque.
Le rapport est stocke dans le meme dossier que chat.json, ce qui garantit :
  - meme ACL que chat.json (authorization via use_context)
  - suppression automatique au chat_remove (delete_dir sur le dossier)

Fichiers generes :
  - tmp/chats/{ctxid}/audit_report.md
  - tmp/chats/{ctxid}/audit_report.pdf  (si WeasyPrint disponible)

Fail-safe : toute exception est absorbee — la reponse est toujours livree.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("audit_report_storage")

AUDIT_REPORT_MD = "audit_report.md"
AUDIT_REPORT_PDF = "audit_report.pdf"


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

    try:
        folder = folder_override or resolve_chat_folder(context_id)
        md_path = os.path.join(folder, AUDIT_REPORT_MD)

        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        logger.info("Audit report stored: %s", md_path)

        if generate_pdf:
            _generate_pdf(folder, report_markdown)

        return md_path

    except Exception as exc:
        logger.error("store_audit_report failed (non-blocking): %s", exc)
        return None


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
