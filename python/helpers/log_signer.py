"""
SESSION 10 — LogSigner: signature RSA-2048 et rotation des cles.

Fournit la signature asymetrique (RSA-PSS + SHA-256) pour le rapport d'audit
Evidence. Remplace la phase 1 HMAC-SHA256 par une vraie non-repudiation :
un tiers peut verifier le rapport avec la cle publique, sans connaitre
la cle privee.

Gestion des cles :
  - EVIDENCE_RSA_PRIVATE_KEY : PEM de la cle privee (env var ou fichier)
  - EVIDENCE_RSA_KEY_ID      : identifiant de la cle active (ex: "002")
  - Cles publiques historiques pour verification des anciens rapports

Si aucune cle RSA n'est configuree, le module retourne None et l'appelant
doit tomber en fallback HMAC (backward compat).

Fail-safe : toute exception est absorbee — jamais de crash.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger("log_signer")

_KEY_ID_PREFIX = "KRV-SIGN-KEY"
_DEFAULT_KEY_ID = "001"

_RSA_KEY_SIZE = 2048
_SIGNATURE_ALGORITHM = "RSA-PSS-SHA256"


def _load_private_key():
    """Load RSA private key from environment.

    Checks EVIDENCE_RSA_PRIVATE_KEY (PEM string) first,
    then EVIDENCE_RSA_PRIVATE_KEY_PATH (file path).
    Returns None if no key is configured.
    """
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        pem_str = os.environ.get("EVIDENCE_RSA_PRIVATE_KEY")
        if pem_str:
            return load_pem_private_key(pem_str.encode("utf-8"), password=None)

        pem_path = os.environ.get("EVIDENCE_RSA_PRIVATE_KEY_PATH")
        if pem_path and os.path.isfile(pem_path):
            with open(pem_path, "rb") as f:
                return load_pem_private_key(f.read(), password=None)

    except ImportError:
        logger.debug("cryptography library not installed — RSA signing unavailable")
    except Exception as exc:
        logger.warning("Failed to load RSA private key: %s", exc)

    return None


def _load_public_key_for_id(key_id: str):
    """Load a public key by key ID for verification.

    Checks EVIDENCE_RSA_PUBLIC_KEYS (JSON map: {"001": "PEM..."})
    or derives from private key if key_id matches active key.
    """
    try:
        from cryptography.hazmat.primitives.serialization import (
            load_pem_public_key,
        )

        registry_json = os.environ.get("EVIDENCE_RSA_PUBLIC_KEYS")
        if registry_json:
            registry = json.loads(registry_json)
            pem_str = registry.get(key_id)
            if not pem_str and key_id.startswith(_KEY_ID_PREFIX + "-"):
                version = key_id[len(_KEY_ID_PREFIX) + 1:]
                pem_str = registry.get(version)
            if pem_str:
                return load_pem_public_key(pem_str.encode("utf-8"))

        active_id = get_active_key_id()
        if key_id == active_id:
            private_key = _load_private_key()
            if private_key is not None:
                return private_key.public_key()

    except ImportError:
        logger.debug("cryptography library not installed")
    except Exception as exc:
        logger.warning("Failed to load public key for %s: %s", key_id, exc)

    return None


def get_active_key_id() -> str:
    """Return the active signing key ID (format: KRV-SIGN-KEY-NNN)."""
    version = os.environ.get("EVIDENCE_RSA_KEY_ID", _DEFAULT_KEY_ID)
    return f"{_KEY_ID_PREFIX}-{version}"


def is_rsa_available() -> bool:
    """Check if RSA signing is available (private key loaded)."""
    return _load_private_key() is not None


def rsa_sign(payload: str) -> Optional[Tuple[str, str, str]]:
    """Sign a payload with RSA-PSS + SHA-256.

    Returns (signature_b64, key_id, algorithm) or None if unavailable.
    The signature is base64-encoded for embedding in the audit report.
    """
    private_key = _load_private_key()
    if private_key is None:
        return None

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        signature_bytes = private_key.sign(
            payload.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

        sig_b64 = base64.b64encode(signature_bytes).decode("ascii")
        key_id = get_active_key_id()

        return sig_b64, key_id, _SIGNATURE_ALGORITHM

    except Exception as exc:
        logger.warning("RSA signing failed: %s", exc)
        return None


def rsa_verify(payload: str, signature_b64: str, key_id: str) -> bool:
    """Verify an RSA-PSS signature.

    Returns True if the signature is valid, False otherwise.
    """
    public_key = _load_public_key_for_id(key_id)
    if public_key is None:
        logger.warning("No public key found for key_id=%s", key_id)
        return False

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature

        signature_bytes = base64.b64decode(signature_b64)

        public_key.verify(
            signature_bytes,
            payload.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True

    except InvalidSignature:
        return False
    except Exception as exc:
        logger.warning("RSA verification failed: %s", exc)
        return False


def generate_keypair() -> Tuple[str, str]:
    """Generate a new RSA-2048 keypair.

    Returns (private_pem, public_pem) as strings.
    Utility for key provisioning — NOT called at runtime.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=_RSA_KEY_SIZE,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem
