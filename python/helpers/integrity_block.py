"""
SESSION 10 — IntegrityBlock: hashes et signature pour le rapport d'audit.

Calcule les hashes SHA-256 de la requete, la reponse et le document analyse,
plus une signature du log de session :

  - **RSA-PSS-SHA256** (methode primaire) si une cle RSA est configuree
    → non-repudiation : un tiers peut verifier avec la cle publique
  - **HMAC-SHA256** (fallback) sinon
    → verification d'integrite uniquement, pas de non-repudiation

La methode est explicitement nommee dans le rapport pour que l'auditeur
ne confonde jamais "verification d'integrite" et "non-repudiation".

Fail-safe: toutes les methodes gerent les None / exceptions sans crash.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("integrity_block")

_KEY_ID_PREFIX = "KRV-SIGN-KEY"
_DEFAULT_LOG_RETENTION = "12 mois (politique Evidence standard)"
_DEFAULT_AUDIT_ACCESS = "Admin + DPO + RSSI (role-based, audit logs)"

_HMAC_METHOD = "HMAC-SHA256 (fallback — verification uniquement, pas de non-repudiation)"
_RSA_METHOD = "RSA-PSS-SHA256 (non-repudiation — verifiable par un tiers avec la cle publique)"


def _get_hmac_key() -> bytes:
    """Resolve the HMAC signing key from environment or use dev fallback."""
    env_key = os.environ.get("EVIDENCE_HMAC_KEY")
    if env_key:
        return env_key.encode("utf-8")
    logger.debug("EVIDENCE_HMAC_KEY not set — using dev fallback key")
    return b"evidence-dev-hmac-key-not-for-production"


def _get_hmac_key_id() -> str:
    key_version = os.environ.get("EVIDENCE_HMAC_KEY_VERSION", "001")
    return f"{_KEY_ID_PREFIX}-{key_version}"


def compute_sha256(content: Optional[str]) -> Optional[str]:
    """SHA-256 of content. Returns None if content is None."""
    if content is None:
        return None
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_hmac_sha256(payload: str, key: Optional[bytes] = None) -> str:
    """HMAC-SHA256 of payload using the signing key."""
    if key is None:
        key = _get_hmac_key()
    return "hmac-sha256:" + hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_sign_payload(
    session_id: str,
    hash_request: Optional[str],
    hash_response: Optional[str],
    hash_document: Optional[str],
    signed_at: str,
) -> str:
    """Build the canonical string to sign."""
    return "\n".join([
        f"session_id={session_id}",
        f"hash_request={hash_request or 'null'}",
        f"hash_response={hash_response or 'null'}",
        f"hash_document={hash_document or 'null'}",
        f"signed_at={signed_at}",
    ])


@dataclass
class IntegrityBlock:
    """Bloc integrite et securite du rapport d'audit Evidence.

    Supports both RSA-PSS-SHA256 (primary, non-repudiation) and
    HMAC-SHA256 (fallback, integrity only) signatures.
    """

    hash_request: Optional[str] = None
    hash_response: Optional[str] = None
    hash_document: Optional[str] = None
    signature_log: Optional[str] = None
    signature_key_id: str = ""
    signature_method: str = _HMAC_METHOD
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

        Tries RSA-PSS-SHA256 first; falls back to HMAC-SHA256 if no RSA key.
        """
        block = cls()

        block.hash_request = compute_sha256(query)
        block.hash_response = compute_sha256(response)
        block.hash_document = compute_sha256(document)

        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            sign_payload = _build_sign_payload(
                session_id,
                block.hash_request,
                block.hash_response,
                block.hash_document,
                now_iso,
            )

            rsa_result = _try_rsa_sign(sign_payload)
            if rsa_result is not None:
                sig_b64, key_id, algorithm = rsa_result
                block.signature_log = f"rsa-pss-sha256:{sig_b64}"
                block.signature_key_id = key_id
                block.signature_method = _RSA_METHOD
            else:
                key = _get_hmac_key()
                block.signature_log = compute_hmac_sha256(sign_payload, key)
                block.signature_key_id = _get_hmac_key_id()
                block.signature_method = _HMAC_METHOD

            block.signed_at = now_iso

        except Exception as exc:
            logger.warning("IntegrityBlock signing failed: %s", exc)
            block.signature_log = "error: signature failed"

        return block

    def to_report_table(self) -> str:
        """Markdown rendering for the integrity section."""
        rows = [
            ("Hash requete (SHA-256)", f"`{self.hash_request}`" if self.hash_request else "\u2014 (pas de requete)"),
            ("Hash reponse (SHA-256)", f"`{self.hash_response}`" if self.hash_response else "\u2014 (pas de reponse)"),
            ("Hash document (SHA-256)", f"`{self.hash_document}`" if self.hash_document else "\u2014 (pas de document analyse)"),
            ("Signature log", f"`{self.signature_log}`" if self.signature_log else "\u2014"),
            ("Cle de signature", f"`{self.signature_key_id}`" if self.signature_key_id else "\u2014"),
            ("Methode", self.signature_method),
            ("Signe a", f"`{self.signed_at}`" if self.signed_at else "\u2014"),
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

    def verify_signature(self, query: Optional[str], response: Optional[str],
                         document: Optional[str] = None, session_id: str = "") -> bool:
        """Verify the cryptographic signature (RSA or HMAC).

        For RSA: verifies with the public key for the stored key_id.
        For HMAC: recomputes and compares (requires the same key).
        """
        if not self.signature_log or not self.signed_at:
            return False

        sign_payload = _build_sign_payload(
            session_id,
            self.hash_request,
            self.hash_response,
            self.hash_document,
            self.signed_at,
        )

        if self.signature_log.startswith("rsa-pss-sha256:"):
            sig_b64 = self.signature_log[len("rsa-pss-sha256:"):]
            return _try_rsa_verify(sign_payload, sig_b64, self.signature_key_id)

        if self.signature_log.startswith("hmac-sha256:"):
            expected = compute_hmac_sha256(sign_payload)
            return hmac.compare_digest(self.signature_log, expected)

        return False


def _try_rsa_sign(payload: str):
    """Attempt RSA signing. Returns (sig_b64, key_id, algorithm) or None."""
    try:
        from python.helpers.log_signer import rsa_sign
        return rsa_sign(payload)
    except ImportError:
        return None
    except Exception as exc:
        logger.debug("RSA sign attempt failed: %s", exc)
        return None


def _try_rsa_verify(payload: str, sig_b64: str, key_id: str) -> bool:
    """Attempt RSA verification. Returns False on any failure."""
    try:
        from python.helpers.log_signer import rsa_verify
        return rsa_verify(payload, sig_b64, key_id)
    except ImportError:
        logger.warning("cryptography library not available for RSA verification")
        return False
    except Exception as exc:
        logger.warning("RSA verification attempt failed: %s", exc)
        return False
