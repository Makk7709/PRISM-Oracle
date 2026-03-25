"""
Document workload heuristics for model routing.

Goal:
- Detect high-complexity document tasks (many PDFs, batch classification,
  invoice sorting, exhaustive extraction requirements).
- Route utility calls to a stronger model when needed.
"""

import os
import re
from typing import Any, List, Optional, Tuple


_DOC_HEAVY_KEYWORDS = (
    "pdf",
    "facture",
    "invoice",
    "pefc",
    "classifier",
    "classer",
    "trier",
    "batch",
    "pages",
    "toutes les pages",
    "volumineux",
)


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def is_document_heavy_request(message: str, attachments: Optional[List[str]] = None) -> bool:
    """
    Detect document-heavy requests likely to suffer with a lightweight utility model.

    Heuristics (fail-open for quality):
    - many attached files (default: >= 6)
    - multiple PDFs + doc-heavy keywords in prompt
    - explicit large-volume markers in text (e.g. "80 pdf")
    """
    attachments = attachments or []
    min_attachments = _env_int("EVIDENCE_DOC_HEAVY_MIN_ATTACHMENTS", 6)
    min_pdfs = _env_int("EVIDENCE_DOC_HEAVY_MIN_PDFS", 3)

    pdf_attachments = [a for a in attachments if a.lower().endswith(".pdf")]
    if len(attachments) >= min_attachments:
        return True
    if len(pdf_attachments) >= min_pdfs and contains_doc_keywords(message):
        return True

    # Explicit size markers: "80 pdf", "60 factures", etc.
    msg = (message or "").lower()
    if re.search(
        r"\b([3-9]\d|[1-9]\d{2,})\s*(pdfs?|factures?|invoices?|documents?)\b",
        msg,
    ):
        return True

    return False


def contains_doc_keywords(message: str) -> bool:
    msg = (message or "").lower()
    return any(k in msg for k in _DOC_HEAVY_KEYWORDS)


def select_utility_model_config(
    utility_model_config: Any,
    chat_model_config: Any,
    message: str,
    attachments: Optional[List[str]] = None,
) -> Tuple[Any, str]:
    """
    Return model config used for utility calls + routing reason.

    Routing policy:
    - document-heavy request => prefer chat model (higher quality)
    - otherwise keep utility model
    """
    if is_document_heavy_request(message=message, attachments=attachments):
        return chat_model_config, "document_heavy_route_to_chat_model"
    return utility_model_config, "default_utility_model"

