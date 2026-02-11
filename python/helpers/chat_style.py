"""
Chat personalization — style instructions for symbiose homme-IA.

Generates a style block injected at the start of the system prompt.
Parameters: tutoiement/vouvoiement, ton, humanisation, verbosité.

Spec: docs/SPEC_CHAT_PERSONALIZATION.md
Rules: R2 (options prédéfinies), R4 (rétrocompatibilité)
"""

import re
from typing import Any

# Valid values (R2 — predefined only)
_VALID_TONE = {"formel", "cordial", "direct", "bienveillant"}
_VALID_HUMANIZATION = {"minimal", "modere", "eleve"}
_VALID_VERBOSITY = {"concise", "equilibre", "detaille"}
_VALID_PERSONA = {"homme", "femme", "ia"}

_MAX_AI_NAME_LEN = 30
_SAFE_AI_NAME_RE = r"[^a-zA-Z0-9\u00c0-\u00ff\s\-']"

# Instruction templates (no user-controllable format)
_ADDRESS_TU = (
    "Adresse l'utilisateur en le tutoyant (tu, ton, ta, tes)."
)
_ADDRESS_VOUS = (
    "Adresse l'utilisateur en le vouvoyant (vous, votre, vos)."
)

_TONE_INSTRUCTIONS = {
    "formel": "Utilise un ton professionnel et distant.",
    "cordial": "Utilise un ton chaleureux et respectueux.",
    "direct": "Utilise un ton direct, sans formules superflues.",
    "bienveillant": "Utilise un ton empathique et encourageant.",
}

_HUMANIZATION_INSTRUCTIONS = {
    "minimal": "Réponses factuelles, peu de reformulations.",
    "modere": "Reformulations naturelles, transitions fluides.",
    "eleve": "Langage très naturel, variété d'expressions, transitions humaines.",
}

_VERBOSITY_INSTRUCTIONS = {
    "concise": "Réponses courtes, à l'essentiel.",
    "equilibre": "Longueur moyenne, équilibrée.",
    "detaille": "Explications complètes et détaillées.",
}

_PERSONA_INSTRUCTIONS = {
    "homme": "Tu t'exprimes au masculin (ex: je suis ravi, content).",
    "femme": "Tu t'exprimes au feminin (ex: je suis ravie, contente).",
    "ia": "Expression neutre, sans genre explicite.",
}


def _sanitize_ai_name(value: str) -> str:
    """R2bis: strip, remove dangerous chars, max 30."""
    if not value or not isinstance(value, str):
        return ""
    s = re.sub(_SAFE_AI_NAME_RE, "", value.strip())
    return s[: _MAX_AI_NAME_LEN]


def build_style_instruction(settings: dict[str, Any] | None) -> str:
    """
    Build the chat style instruction block from settings.

    R4: If settings is None or empty, returns default (vouvoiement, cordial, modere, equilibre).
    R2: Invalid values fall back to defaults.

    Returns:
        A non-empty string to prepend to the system prompt.
    """
    if not settings:
        settings = {}

    address_tu = settings.get("chat_address_tu", False)
    tone = settings.get("chat_tone", "cordial")
    humanization = settings.get("chat_humanization", "modere")
    verbosity = settings.get("chat_verbosity", "equilibre")
    persona = settings.get("chat_persona", "ia")
    ai_name_raw = settings.get("chat_ai_name", "")

    # Fallback invalid values (R2, R4)
    if tone not in _VALID_TONE:
        tone = "cordial"
    if humanization not in _VALID_HUMANIZATION:
        humanization = "modere"
    if verbosity not in _VALID_VERBOSITY:
        verbosity = "equilibre"
    if persona not in _VALID_PERSONA:
        persona = "ia"

    ai_name = _sanitize_ai_name(ai_name_raw)

    address_line = _ADDRESS_TU if address_tu else _ADDRESS_VOUS
    tone_line = _TONE_INSTRUCTIONS[tone]
    human_line = _HUMANIZATION_INSTRUCTIONS[humanization]
    verb_line = _VERBOSITY_INSTRUCTIONS[verbosity]
    persona_line = _PERSONA_INSTRUCTIONS[persona]

    lines = [
        "## STYLE DE COMMUNICATION — Symbiose homme-IA",
        "",
        f"- **Adresse :** {address_line}",
        f"- **Ton :** {tone_line}",
        f"- **Humanisation :** {human_line}",
        f"- **Verbosité :** {verb_line}",
        f"- **Persona :** {persona_line}",
    ]
    if ai_name:
        lines.append(f"- **Nom :** Tu te présentes sous le nom « {ai_name} » lorsque pertinent.")
    lines.append("")

    return "\n".join(lines)
