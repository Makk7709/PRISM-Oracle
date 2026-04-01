"""
SESSION 8 — IntegrityBlock: hashes et signature pour le rapport d'audit.

Calcule les hashes SHA-256 de la requete, la reponse et le document analyse,
plus une signature HMAC-SHA256 du log de session (phase 1, non-repudiation
differee a SESSION 10 avec RSA-2048).

IMPORTANT: HMAC-SHA256 est explicitement presente comme "phase 1" dans le
rapport. Ce n'est PAS une signature asymetrique — un auditeur ne doit pas
confondre "signature de verification" et "non-repudiation".

Fail-safe: toutes les methodes gerent les None / exceptions sans crash.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("integrity_block")

_KEY_ID_PREFIX = "KRV-SIGN-KEY"
_DEFAULT_LOG_RETENTION = "12 mois (politique Evidence standard)"
_DEFAULT_AUDIT_ACCESS = "Admin + DPO (role-based, audit logs)"


def _get_hmac_key() -> bytes:
    """Resolve the HMAC signing key from environment or generate a stable default.

    In production, EVIDENCE_HMAC_KEY should be set as an environment variable.
    In dev/test, a deterministic fallback is used (NOT suitable for production).
    """
    env_key = os.environ.get("EVIDENCE_HMAC_KEY")
    if env_key:
        return env_key.encode("utf-8")
    logger.debug("EVIDENCE_HMAC_KEY not set — using dev fallback key")
    return b"evidence-dev-hmac-key-not-for-production"


def _get_key_id() -> str:
    """Format: KRV-SIGN-KEY-001 (incremented when key is rotated)."""
    key_version = os.environ.get("EVIDENCE_HMAC_KEY_VERSION", "001")
    return f"{_KEY_ID_PREFIX}-{key_version}"


def compute_sha256(content: Optional[str]) -> Optional[str]:
    """SHA-256 of content. Returns None if content is None (null != empty)."""
    if content is None:
        return None
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_hmac_sha256(payload: str, key: Optional[bytes] = None) -> str:
    """HMAC-SHA256 of payload using the signing key."""
    if key is None:
        key = _get_hmac_key()
    return "hmac-sha256:" + hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass
class IntegrityBlock:
    """Bloc integrite et securite du rapport d'audit Evidence.

    Fields:
        hash_request: SHA-256 of the raw user query (before any normalization)
        hash_response: SHA-256 of the final markdown response (before audit append)
        hash_document: SHA-256 of the analyzed document (None if no document)
        signature_log: HMAC-SHA256 of the session log payload
        signature_key_id: Key ID used for the HMAC signature
        signature_method: Explicitly "HMAC-SHA256 (phase 1 — verification only)"
        log_retention: Retention policy description
        audit_access: Access control description
        signed_at: ISO timestamp of signature creation
    """

    hash_request: Optional[str] = None
    hash_response: Optional[str] = None
    hash_document: Optional[str] = None
    signature_log: Optional[str] = None
    signature_key_id: str = ""
    signature_method: str = "HMAC-SHA256 (phase 1 — verification uniquement, pas de non-repudiation)"
    log_retention: str = _DEFAULT_LOG_RETENTION
    audit_access: str = _DEFAULT_AUDIT_ACCESS
    signed_at: Optional[str] = None

    @classmethod
    def from_session(
        cls,
        query: Optional[str] = None,
        response: Optional[str] = None,
        document: Optional[str] = None,
        session_id: str = "",
    ) -> "IntegrityBlock":
        """Factory: compute all hashes and sign the session log.

        Args:
            query: Raw user query (hashed as-is, no normalization)
            response: Final pipeline/LLM response markdown (before audit block)
            document: Analyzed document content (None if not applicable)
            session_id: Session ID for the signature payload
        """
        block = cls()

        block.hash_request = compute_sha256(query)
        block.hash_response = compute_sha256(response)
        block.hash_document = compute_sha256(document)

        try:
            key = _get_hmac_key()
            key_id = _get_key_id()
            now_iso = datetime.now(timezone.utc).isoformat()

            sign_payload = "\n".join([
                f"session_id={session_id}",
                f"hash_request={block.hash_request or 'null'}",
                f"hash_response={block.hash_response or 'null'}",
                f"hash_document={block.hash_document or 'null'}",
                f"signed_at={now_iso}",
            ])

            block.signature_log = compute_hmac_sha256(sign_payload, key)
            block.signature_key_id = key_id
            block.signed_at = now_iso
        except Exception as exc:
            logger.warning("IntegrityBlock HMAC signing failed: %s", exc)
            block.signature_log = "error: signature failed"

        return block

    def to_report_table(self) -> str:
        """Markdown rendering for the integrity section of the audit report."""
        rows = [
            ("Hash requete (SHA-256)", f"`{self.hash_request}`" if self.hash_request else "— (pas de requete)"),
            ("Hash reponse (SHA-256)", f"`{self.hash_response}`" if self.hash_response else "— (pas de reponse)"),
            ("Hash document (SHA-256)", f"`{self.hash_document}`" if self.hash_document else "— (pas de document analyse)"),
            ("Signature log", f"`{self.signature_log}`" if self.signature_log else "—"),
            ("Cle de signature", f"`{self.signature_key_id}`" if self.signature_key_id else "—"),
            ("Methode", self.signature_method),
            ("Signe a", f"`{self.signed_at}`" if self.signed_at else "—"),
            ("Retention des logs", self.log_retention),
            ("Acces audit", self.audit_access),
        ]

        lines = ["| CHAMP | VALEUR |", "|---|---|"]
        for label, value in rows:
            lines.append(f"| **{label}** | {value} |")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-compatible serialization."""
        return {
            "hash_request": self.hash_request,
            "hash_response": self.hash_response,
            "hash_document": self.hash_document,
            "signature_log": self.signature_log,
            "signature_key_id": self.signature_key_id,
            "signature_method": self.signature_method,
            "log_retention": self.log_retention,
            "audit_access": self.audit_access,
            "signed_at": self.signed_at,
        }

    def verify(self, query: Optional[str], response: Optional[str], document: Optional[str] = None) -> bool:
        """Verify that stored hashes match the provided content.

        Returns True only if ALL non-null hashes match.
        Does NOT verify the HMAC signature (requires the key).
        """
        checks = [
            (self.hash_request, compute_sha256(query)),
            (self.hash_response, compute_sha256(response)),
            (self.hash_document, compute_sha256(document)),
        ]
        for stored, computed in checks:
            if stored is not None and stored != computed:
                return False
        return True
