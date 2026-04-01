"""
SESSION 7B — Bloc d'audit leger pour le flux LLM classique.

Utilise par l'extension message_loop_end : pas de grille ComplianceGrid ni
PipelineTracker (reserve au flux pipeline S6+7A).

Seuil de declenchement : nombre de mots du corps de reponse (defaut 100).
Configurable via AUDIT_LIGHT_MIN_WORDS.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
def audit_light_min_words() -> int:
    raw = os.environ.get("AUDIT_LIGHT_MIN_WORDS", "100")
    try:
        return max(1, int(raw))
    except ValueError:
        return 100


def count_words(text: str) -> int:
    """Compte les tokens non-blancs (robuste markdown / ponctuation)."""
    if not text or not text.strip():
        return 0
    return len(re.findall(r"\S+", text))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_audit_light_markdown(
    *,
    session_id: str,
    model_label: str,
    completed_at_iso: str,
    evidence_version: str,
) -> str:
    """Markdown du bloc synthetique (append apres le corps utilisateur)."""
    ver = evidence_version if evidence_version != "unknown" else "unknown (non resolu)"
    lines = [
        "",
        "---",
        "",
        "## Metadonnees d'audit Evidence (vue synthetique)",
        "",
        "| Champ | Valeur |",
        "|---|---|",
        f"| Session ID | `{session_id or '—'}` |",
        f"| Modele | `{model_label}` |",
        f"| Horodatage reponse | `{completed_at_iso}` |",
        f"| Version Evidence | `{ver}` |",
        "",
        "*Bloc leger — flux conversationnel. Les reponses pipeline incluent une audit etendue (S6+7A).*",
        "",
    ]
    return "\n".join(lines)


def resolve_model_label(model_config) -> str:
    """Meme convention que ReportMetadata : provider/name ou name seul."""
    if model_config is None:
        return "unknown"
    try:
        name = getattr(model_config, "name", None) or "unknown"
        provider = getattr(model_config, "provider", None) or ""
        return f"{provider}/{name}" if provider else str(name)
    except Exception:
        return "unknown"
