"""
SessionEnvelope — Conteneur de metadonnees pour les rapports d'audit Evidence.

Chaque session de traitement produit une enveloppe qui alimente :
- Bloc "Identite de la session" du rapport d'audit
- Bloc "Metadonnees techniques" (champ session_id)
- Bloc "Integrite et securite" (champ integrity_hash)

Format session_id : KRV-SES-YYYYMMDD-XXXXXXX (7 hex aleatoires, uppercase)
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("session_envelope")

_HASH_NULL_SENTINEL = "\x00NULL\x00"
_HASH_SEPARATOR = "\x00"


def _generate_session_id() -> str:
    """
    Genere un identifiant de session unique.
    Format : KRV-SES-YYYYMMDD-XXXXXXX
    - Date UTC au format YYYYMMDD
    - Suffixe : 7 caracteres hex aleatoires (uuid4), uppercase
    """
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:7].upper()
    return f"KRV-SES-{date_part}-{random_part}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_evidence_version() -> str:
    """Resout la version Evidence depuis git ou VERSION.json."""
    try:
        from python.helpers import git as _git
        version = _git.get_version()
        if version and version != "unknown":
            return version
    except Exception:
        pass
    logger.warning("evidence_version could not be resolved — defaulting to 'unknown'")
    return "unknown"


def _resolve_environment_label() -> str:
    """
    Resout le label d'environnement depuis les settings.
    Fallback : chaine vide (jamais de crash).
    """
    try:
        from python.helpers.settings import get_settings as _get_settings
        settings = _get_settings()
        return settings.get("environment_label", "") or ""
    except Exception:
        logger.warning("environment_label could not be resolved from settings")
        return ""


def _encode_hash_field(value: Optional[str]) -> str:
    """Encode un champ pour le hash d'integrite. None et '' sont distincts."""
    if value is None:
        return _HASH_NULL_SENTINEL
    return value


@dataclass
class SessionEnvelope:
    """
    Enveloppe de metadonnees pour une session de traitement Evidence.

    Cycle de vie :
    1. Instanciation au debut du traitement -> started_at auto
    2. Enrichissement progressif (username, organization, query...)
    3. Finalisation en fin de traitement -> complete()
    4. Rendu dans le rapport d'audit
    """

    session_id: str = field(default_factory=_generate_session_id)
    started_at: str = field(default_factory=_utc_now_iso)
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None

    username: Optional[str] = None
    organization: Optional[str] = None
    user_profile: Optional[str] = None

    environment_label: str = field(default_factory=_resolve_environment_label)
    evidence_version: str = field(default_factory=_resolve_evidence_version)

    query: Optional[str] = None
    response_hash: Optional[str] = None
    integrity_hash: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duree en secondes (float) pour le rendu rapport."""
        if self.duration_ms is None:
            return None
        return round(self.duration_ms / 1000, 1)

    def complete(self) -> "SessionEnvelope":
        """
        Finalise l'enveloppe : horodatage de fin, duree, hash d'integrite.
        Retourne self pour chainage.
        """
        self.completed_at = _utc_now_iso()
        self.duration_ms = self._compute_duration()
        self.integrity_hash = self._compute_integrity_hash()
        return self

    def _compute_duration(self) -> Optional[int]:
        """Calcule la duree en millisecondes entre started_at et completed_at."""
        if not self.started_at or not self.completed_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            delta = end - start
            return max(0, int(delta.total_seconds() * 1000))
        except (ValueError, TypeError):
            return None

    def _compute_integrity_hash(self) -> str:
        """
        SHA-256 deterministe de session_id + query + response_hash.
        None et chaine vide sont distingues via un sentinel.
        Le separateur est un null byte (impossible dans du texte UTF-8 normal).
        """
        payload = _HASH_SEPARATOR.join([
            _encode_hash_field(self.session_id),
            _encode_hash_field(self.query),
            _encode_hash_field(self.response_hash),
        ])
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_report_table(self) -> str:
        """Rendu markdown du bloc 'Identite de la session'."""
        duration_label = "—"
        if self.duration_seconds is not None:
            duration_label = f"{self.duration_seconds} secondes"

        version_label = self.evidence_version or "—"
        if version_label == "unknown":
            version_label = "unknown (non resolu)"

        rows = [
            ("Session ID", self.session_id),
            ("Horodatage debut", self.started_at),
            ("Horodatage fin", self.completed_at or "—"),
            ("Duree de traitement", duration_label),
            ("Utilisateur", self.username or "—"),
            ("Organisation", self.organization or "—"),
            ("Profil utilisateur", self.user_profile or "—"),
            ("Environnement", self.environment_label or "—"),
            ("Version KOREV Evidence", version_label),
            ("Hash d'integrite session", self.integrity_hash or "—"),
        ]
        lines = [
            "| CHAMP | VALEUR |",
            "|---|---|",
        ]
        for label, value in rows:
            lines.append(f"| **{label}** | `{value}` |")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialisation en dictionnaire pour le bloc JSON metadonnees."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "username": self.username,
            "organization": self.organization,
            "user_profile": self.user_profile,
            "environment_label": self.environment_label,
            "evidence_version": self.evidence_version,
            "integrity_hash": self.integrity_hash,
        }
