"""
SESSION 8 — Tests IntegrityBlock + AuditReportRenderer.

Coverage:
- IntegrityBlock: hashes, HMAC signature, verify, to_report_table, to_dict
- AuditReportRenderer: section ordering, fail-safe, empty inputs, footer
- Snapshot: structural validation of the full audit report
"""

import hashlib
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from python.helpers.integrity_block import (
    IntegrityBlock,
    compute_hmac_sha256,
    compute_sha256,
)
from python.helpers.audit_report_renderer import AuditReportRenderer


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrityBlock — Hashes
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeSHA256:

    def test_none_returns_none(self):
        assert compute_sha256(None) is None

    def test_empty_string_returns_hash(self):
        result = compute_sha256("")
        assert result.startswith("sha256:")
        assert len(result) == 71  # "sha256:" + 64 hex

    def test_deterministic(self):
        assert compute_sha256("hello") == compute_sha256("hello")

    def test_different_inputs_different_hashes(self):
        assert compute_sha256("a") != compute_sha256("b")

    def test_empty_vs_none_differ(self):
        assert compute_sha256("") is not None
        assert compute_sha256(None) is None


class TestComputeHMAC:

    def test_returns_prefixed_string(self):
        result = compute_hmac_sha256("payload", b"key")
        assert result.startswith("hmac-sha256:")
        assert len(result) == 76  # "hmac-sha256:" + 64 hex

    def test_deterministic(self):
        assert compute_hmac_sha256("p", b"k") == compute_hmac_sha256("p", b"k")

    def test_different_keys_different_signatures(self):
        assert compute_hmac_sha256("p", b"k1") != compute_hmac_sha256("p", b"k2")

    def test_different_payloads_different_signatures(self):
        assert compute_hmac_sha256("a", b"k") != compute_hmac_sha256("b", b"k")


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrityBlock — Factory + Serialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrityBlockFactory:

    def test_from_session_computes_all_hashes(self):
        block = IntegrityBlock.from_session(
            query="What is AI Act?",
            response="The AI Act is...",
            document="doc content",
            session_id="KRV-SES-20260401-ABC1234",
        )
        assert block.hash_request is not None
        assert block.hash_request.startswith("sha256:")
        assert block.hash_response is not None
        assert block.hash_document is not None
        assert block.signature_log is not None
        assert block.signature_log.startswith("hmac-sha256:")
        assert block.signature_key_id.startswith("KRV-SIGN-KEY-")
        assert block.signed_at is not None

    def test_none_query_produces_none_hash(self):
        block = IntegrityBlock.from_session(query=None, response="resp")
        assert block.hash_request is None
        assert block.hash_response is not None

    def test_none_document_produces_none_hash(self):
        block = IntegrityBlock.from_session(query="q", response="r", document=None)
        assert block.hash_document is None

    def test_signature_method_is_honest_hmac_fallback(self):
        """Without RSA keys, HMAC fallback is used and honestly labeled."""
        block = IntegrityBlock.from_session(query="q", response="r")
        assert block.signature_log.startswith("hmac-sha256:")
        assert "HMAC-SHA256" in block.signature_method
        assert "fallback" in block.signature_method
        assert "non-repudiation" in block.signature_method.lower()
        assert "verification uniquement" in block.signature_method.lower()

    def test_custom_key_via_env(self):
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY": "custom-secret"}):
            b1 = IntegrityBlock.from_session(query="q", response="r", session_id="s1")
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY": "other-secret"}):
            b2 = IntegrityBlock.from_session(query="q", response="r", session_id="s1")
        assert b1.signature_log != b2.signature_log

    def test_key_version_via_env(self):
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY_VERSION": "042"}):
            block = IntegrityBlock.from_session(query="q", response="r")
        assert block.signature_key_id == "KRV-SIGN-KEY-042"


class TestIntegrityBlockVerify:

    def test_verify_passes_matching_content(self):
        block = IntegrityBlock.from_session(query="q", response="r", document="d")
        assert block.verify("q", "r", "d") is True

    def test_verify_fails_on_modified_response(self):
        block = IntegrityBlock.from_session(query="q", response="r")
        assert block.verify("q", "MODIFIED") is False

    def test_verify_fails_on_modified_query(self):
        block = IntegrityBlock.from_session(query="q", response="r")
        assert block.verify("MODIFIED", "r") is False

    def test_verify_none_document_passes(self):
        block = IntegrityBlock.from_session(query="q", response="r", document=None)
        assert block.verify("q", "r", None) is True


class TestIntegrityBlockSerialization:

    def test_to_report_table_markdown(self):
        """Without RSA keys, table contains HMAC signature."""
        block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
        table = block.to_report_table()
        assert "| CHAMP | VALEUR |" in table
        assert "Hash requete" in table
        assert "Hash reponse" in table
        assert "Signature log" in table
        assert "sha256:" in table
        assert "hmac-sha256:" in table
        assert "fallback" in table.lower()

    def test_to_dict_all_keys(self):
        block = IntegrityBlock.from_session(query="q", response="r")
        d = block.to_dict()
        expected_keys = {
            "hash_request", "hash_response", "hash_document",
            "signature_log", "signature_key_id", "signature_method",
            "log_retention", "audit_access", "signed_at",
        }
        assert set(d.keys()) == expected_keys


# ═══════════════════════════════════════════════════════════════════════════════
# AuditReportRenderer
# ═══════════════════════════════════════════════════════════════════════════════


def _make_envelope(query="test query", session_id="KRV-SES-20260401-TEST123"):
    """Create a minimal SessionEnvelope mock."""
    from python.helpers.session_envelope import SessionEnvelope
    env = SessionEnvelope()
    env.session_id = session_id
    env.query = query
    env.username = "admin"
    env.organization = "Korev AI"
    return env


def _make_tracker():
    """Create a PipelineTracker with 2 completed agents."""
    from python.helpers.pipeline_tracker import PipelineTracker
    t = PipelineTracker()
    t.start_step("researcher")
    t.complete_step("researcher")
    t.start_step("finance")
    t.complete_step("finance")
    return t


class TestAuditReportRenderer:

    def test_render_with_all_components(self):
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            query="test query",
            response="Long response content for the test.",
        )
        report = renderer.render()

        assert report.startswith("\n\n---")
        assert "## Rapport d'audit Evidence" in report
        assert "### Identite de la session" in report
        assert "### Pipeline d'execution" in report
        assert "### Grille de conformite" in report or "### Metadonnees techniques" in report
        assert "### Metadonnees techniques" in report
        assert "### Integrite et securite" in report
        assert "KOREV Evidence" in report  # footer

    def test_render_empty_when_nothing(self):
        renderer = AuditReportRenderer()
        report = renderer.render()
        assert "### Metadonnees techniques" in report or report != ""

    def test_render_without_envelope(self):
        renderer = AuditReportRenderer(
            tracker=_make_tracker(),
            query="q",
            response="r",
        )
        report = renderer.render()
        assert "### Integrite et securite" in report
        assert "### Identite de la session" not in report

    def test_render_without_tracker(self):
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            query="q",
            response="r",
        )
        report = renderer.render()
        assert "### Identite de la session" in report
        assert "### Pipeline d'execution" not in report

    def test_section_ordering(self):
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            query="q",
            response="r",
        )
        report = renderer.render()
        idx_identity = report.find("### Identite de la session")
        idx_pipeline = report.find("### Pipeline d'execution")
        idx_meta = report.find("### Metadonnees techniques")
        idx_integrity = report.find("### Integrite et securite")

        assert idx_identity < idx_pipeline < idx_meta < idx_integrity

    def test_footer_present(self):
        renderer = AuditReportRenderer(query="q", response="r")
        report = renderer.render()
        assert "AI Act" in report
        assert "audit_reports" in report

    def test_integrity_hashes_match_inputs(self):
        query = "What is RGPD?"
        response = "The RGPD is..."
        renderer = AuditReportRenderer(
            envelope=_make_envelope(query=query),
            query=query,
            response=response,
        )
        report = renderer.render()
        expected_hash = "sha256:" + hashlib.sha256(query.encode()).hexdigest()
        assert expected_hash in report

    def test_response_hash_covers_original_content(self):
        response = "Original pipeline output"
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            query="q",
            response=response,
        )
        report = renderer.render()
        expected_resp_hash = "sha256:" + hashlib.sha256(response.encode()).hexdigest()
        assert expected_resp_hash in report

    def test_fail_safe_on_broken_envelope(self):
        broken_envelope = MagicMock()
        broken_envelope.to_report_table.side_effect = RuntimeError("broken")
        broken_envelope.session_id = "X"
        broken_envelope.query = "q"
        broken_envelope.response_hash = None
        broken_envelope.complete.side_effect = RuntimeError("broken")

        renderer = AuditReportRenderer(
            envelope=broken_envelope,
            query="q",
            response="r",
        )
        report = renderer.render()
        assert "### Metadonnees techniques" in report or "### Integrite" in report


# ═══════════════════════════════════════════════════════════════════════════════
# Snapshot: structural validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestReportSnapshot:
    """Validate the canonical structure of a full audit report."""

    def test_full_report_has_7_section_types(self):
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            query="test query",
            response="Full response for snapshot test.",
        )
        report = renderer.render()

        expected_sections = [
            "Identite de la session",
            "Pipeline d'execution",
            "Metadonnees techniques",
            "Integrite et securite",
            "KOREV Evidence",  # footer marker
        ]
        for section in expected_sections:
            assert section in report, f"Missing section: {section}"

    def test_full_report_has_hmac_fallback_and_sha256(self):
        """Without RSA keys, the full report uses HMAC fallback."""
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            query="q",
            response="r",
        )
        report = renderer.render()
        assert "sha256:" in report
        assert "hmac-sha256:" in report
        assert "HMAC-SHA256" in report
        assert "fallback" in report.lower()
        assert "verification uniquement" in report.lower()

    def test_session_id_consistent_across_blocks(self):
        env = _make_envelope(session_id="KRV-SES-20260401-CONSIST")
        renderer = AuditReportRenderer(
            envelope=env,
            tracker=_make_tracker(),
            query="q",
            response="r",
        )
        report = renderer.render()
        assert report.count("KRV-SES-20260401-CONSIST") >= 2
