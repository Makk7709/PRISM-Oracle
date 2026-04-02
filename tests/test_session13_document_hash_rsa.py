"""
SESSION 13 — Tests: document hash for strategic pipelines + RSA signing.

Validates:
  - _resolve_document returns pipeline_response for strategic pipelines
  - _resolve_document returns None for non-strategic pipelines
  - IntegrityBlock.from_session produces hash_document when document is provided
  - IntegrityBlock.from_session produces None hash_document when document is None
  - RSA sign/verify round-trip (when cryptography is available)
  - HMAC fallback when no RSA key is configured
  - Tampered content fails verification
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
from python.helpers.integrity_block import IntegrityBlock, compute_sha256


def _make_hook():
    """Build a minimal AuditMetadataAppend with a mock agent."""
    from python.extensions.monologue_start._20_audit_metadata_append import (
        AuditMetadataAppend,
    )
    agent = MagicMock()
    stored = {}
    agent.set_data = lambda k, v: stored.__setitem__(k, v)
    agent.get_data = lambda k: stored.get(k)
    hook = AuditMetadataAppend.__new__(AuditMetadataAppend)
    hook.agent = agent
    hook._stored = stored
    return hook


class TestResolveDocument:

    def test_returns_response_for_strategic_pipeline(self):
        hook = _make_hook()
        hook._stored["_strategic_result"] = MagicMock()
        result = hook._resolve_document("consolidated strategic text")
        assert result == "consolidated strategic text"

    def test_returns_none_for_non_strategic(self):
        hook = _make_hook()
        result = hook._resolve_document("regular pipeline response")
        assert result is None

    def test_returns_none_on_error(self):
        hook = _make_hook()
        hook.agent.get_data = MagicMock(side_effect=RuntimeError("boom"))
        result = hook._resolve_document("anything")
        assert result is None


class TestIntegrityBlockDocumentHash:

    def test_hash_document_present_when_document_provided(self):
        block = IntegrityBlock.from_session(
            query="test query",
            response="test response",
            document="consolidated strategic document",
            session_id="KRV-TEST-001",
        )
        assert block.hash_document is not None
        assert block.hash_document.startswith("sha256:")
        assert block.hash_document == compute_sha256("consolidated strategic document")

    def test_hash_document_none_when_no_document(self):
        block = IntegrityBlock.from_session(
            query="test query",
            response="test response",
            document=None,
            session_id="KRV-TEST-002",
        )
        assert block.hash_document is None

    def test_hash_document_in_report_table(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document="doc content",
            session_id="KRV-TEST-003",
        )
        table = block.to_report_table()
        assert "sha256:" in table
        assert "pas de document" not in table

    def test_no_document_shows_dash_in_report(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document=None,
            session_id="KRV-TEST-004",
        )
        table = block.to_report_table()
        assert "pas de document" in table

    def test_document_hash_covers_content_before_audit(self):
        """Hash must be computed on raw document, not modified after."""
        doc = "This is the raw strategic document before audit block"
        block = IntegrityBlock.from_session(
            query="q", response="r", document=doc, session_id="KRV-TEST"
        )
        assert block.hash_document == compute_sha256(doc)
        modified = doc + "\n\n## Audit Report\n..."
        assert block.hash_document != compute_sha256(modified)


class TestIntegrityBlockSignature:

    def test_hmac_signature_present(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", session_id="KRV-TEST"
        )
        assert block.signature_log is not None
        assert block.signed_at is not None

    def test_hmac_verify_succeeds(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document="d", session_id="KRV-TEST"
        )
        assert block.verify("q", "r", "d") is True

    def test_tampered_response_fails_verify(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document="d", session_id="KRV-TEST"
        )
        assert block.verify("q", "TAMPERED", "d") is False

    def test_tampered_document_fails_verify(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document="d", session_id="KRV-TEST"
        )
        assert block.verify("q", "r", "TAMPERED") is False

    def test_to_dict_includes_document_hash(self):
        block = IntegrityBlock.from_session(
            query="q", response="r", document="strategic doc",
            session_id="KRV-TEST",
        )
        d = block.to_dict()
        assert "hash_document" in d
        assert d["hash_document"].startswith("sha256:")

    def test_signature_includes_document_hash(self):
        """Document hash is included in the signed payload."""
        block = IntegrityBlock.from_session(
            query="q", response="r", document="d", session_id="KRV-TEST"
        )
        assert block.verify_signature("q", "r", "d", "KRV-TEST") is True


class TestRSAWhenAvailable:

    def test_rsa_sign_verify_roundtrip(self):
        """If cryptography is installed, test RSA round-trip."""
        try:
            from python.helpers.log_signer import generate_keypair, rsa_sign
        except ImportError:
            return

        priv_pem, pub_pem = generate_keypair()
        os.environ["EVIDENCE_RSA_PRIVATE_KEY"] = priv_pem
        os.environ["EVIDENCE_RSA_KEY_ID"] = "test-001"
        os.environ["EVIDENCE_RSA_PUBLIC_KEYS"] = (
            '{"test-001": "' + pub_pem.replace("\n", "\\n") + '"}'
        )

        try:
            block = IntegrityBlock.from_session(
                query="q", response="r", document="strategic doc",
                session_id="KRV-RSA-TEST",
            )
            assert "rsa-pss-sha256:" in block.signature_log
            assert "RSA-PSS-SHA256" in block.signature_method
            assert block.verify_signature("q", "r", "strategic doc", "KRV-RSA-TEST")
        finally:
            os.environ.pop("EVIDENCE_RSA_PRIVATE_KEY", None)
            os.environ.pop("EVIDENCE_RSA_KEY_ID", None)
            os.environ.pop("EVIDENCE_RSA_PUBLIC_KEYS", None)
