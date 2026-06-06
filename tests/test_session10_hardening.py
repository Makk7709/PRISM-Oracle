"""
SESSION 10 — Tests Hardening: RSA-2048, rotation, monitoring, retention, endpoint, ACL.

Coverage:
- LogSigner: key generation, RSA signing, verification, key rotation
- IntegrityBlock: RSA upgrade, HMAC fallback, verify_signature
- ObservabilityMetrics: new audit counters
- audit_report_storage: retention purge
- authorization: can_access_audit_reports, compliance roles
- audit_reports endpoint: ACL checks
- Benchmarks: overhead verification
"""

import base64
import hashlib
import os
import shutil
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# LogSigner — RSA Key Management
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogSignerKeyGeneration:

    def test_generate_keypair_returns_pem_strings(self):
        from python.helpers.log_signer import generate_keypair
        private_pem, public_pem = generate_keypair()
        assert "-----BEGIN PRIVATE KEY-----" in private_pem
        assert "-----END PRIVATE KEY-----" in private_pem
        assert "-----BEGIN PUBLIC KEY-----" in public_pem
        assert "-----END PUBLIC KEY-----" in public_pem

    def test_generate_keypair_produces_unique_keys(self):
        from python.helpers.log_signer import generate_keypair
        k1_priv, _ = generate_keypair()
        k2_priv, _ = generate_keypair()
        assert k1_priv != k2_priv

    def test_generated_key_is_2048_bits(self):
        from python.helpers.log_signer import generate_keypair
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        private_pem, _ = generate_keypair()
        key = load_pem_private_key(private_pem.encode(), password=None)
        assert key.key_size == 2048


class TestLogSignerSigning:

    @pytest.fixture(autouse=True)
    def _setup_rsa_env(self, tmp_path):
        from python.helpers.log_signer import generate_keypair
        self.private_pem, self.public_pem = generate_keypair()
        self._env_patch = patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": self.private_pem,
            "EVIDENCE_RSA_KEY_ID": "002",
        })
        self._env_patch.start()
        yield
        self._env_patch.stop()

    def test_rsa_sign_returns_tuple(self):
        from python.helpers.log_signer import rsa_sign
        result = rsa_sign("test payload")
        assert result is not None
        sig_b64, key_id, algorithm = result
        assert isinstance(sig_b64, str)
        assert key_id == "KRV-SIGN-KEY-002"
        assert algorithm == "RSA-PSS-SHA256"

    def test_rsa_sign_produces_valid_base64(self):
        from python.helpers.log_signer import rsa_sign
        sig_b64, _, _ = rsa_sign("test")
        decoded = base64.b64decode(sig_b64)
        assert len(decoded) == 256  # RSA-2048 → 256 bytes

    def test_is_rsa_available_with_key(self):
        from python.helpers.log_signer import is_rsa_available
        assert is_rsa_available() is True

    def test_is_rsa_available_without_key(self):
        from python.helpers.log_signer import is_rsa_available
        with patch.dict(os.environ, {}, clear=True):
            assert is_rsa_available() is False


class TestLogSignerVerification:

    @pytest.fixture(autouse=True)
    def _setup_rsa_env(self):
        from python.helpers.log_signer import generate_keypair
        import json
        self.private_pem, self.public_pem = generate_keypair()
        self.public_keys_json = json.dumps({"002": self.public_pem})
        self._env_patch = patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": self.private_pem,
            "EVIDENCE_RSA_KEY_ID": "002",
            "EVIDENCE_RSA_PUBLIC_KEYS": self.public_keys_json,
        })
        self._env_patch.start()
        yield
        self._env_patch.stop()

    def test_sign_then_verify_succeeds(self):
        from python.helpers.log_signer import rsa_sign, rsa_verify
        payload = "session_id=TEST\nhash_request=sha256:abc"
        sig_b64, key_id, _ = rsa_sign(payload)
        assert rsa_verify(payload, sig_b64, key_id) is True

    def test_verify_fails_on_tampered_payload(self):
        from python.helpers.log_signer import rsa_sign, rsa_verify
        payload = "original"
        sig_b64, key_id, _ = rsa_sign(payload)
        assert rsa_verify("tampered", sig_b64, key_id) is False

    def test_verify_fails_on_wrong_key_id(self):
        from python.helpers.log_signer import rsa_sign, rsa_verify
        payload = "test"
        sig_b64, _, _ = rsa_sign(payload)
        assert rsa_verify(payload, sig_b64, "KRV-SIGN-KEY-999") is False

    def test_verify_with_bad_signature_returns_false(self):
        from python.helpers.log_signer import rsa_verify
        bad_sig = base64.b64encode(b"not-a-real-signature").decode()
        assert rsa_verify("payload", bad_sig, "KRV-SIGN-KEY-002") is False


class TestLogSignerKeyRotation:

    def test_active_key_id_from_env(self):
        from python.helpers.log_signer import get_active_key_id
        with patch.dict(os.environ, {"EVIDENCE_RSA_KEY_ID": "003"}):
            assert get_active_key_id() == "KRV-SIGN-KEY-003"

    def test_default_key_id(self):
        from python.helpers.log_signer import get_active_key_id
        with patch.dict(os.environ, {}, clear=True):
            assert get_active_key_id() == "KRV-SIGN-KEY-001"

    def test_old_report_verifiable_with_historical_key(self):
        """Simulate: report signed with key 001, verified after rotation to 002."""
        import json
        from python.helpers.log_signer import generate_keypair, rsa_sign, rsa_verify

        old_priv, old_pub = generate_keypair()
        new_priv, new_pub = generate_keypair()

        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": old_priv,
            "EVIDENCE_RSA_KEY_ID": "001",
        }):
            payload = "old-report-data"
            sig_b64, key_id, _ = rsa_sign(payload)
            assert key_id == "KRV-SIGN-KEY-001"

        public_keys = json.dumps({"001": old_pub, "002": new_pub})
        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": new_priv,
            "EVIDENCE_RSA_KEY_ID": "002",
            "EVIDENCE_RSA_PUBLIC_KEYS": public_keys,
        }):
            assert rsa_verify(payload, sig_b64, "KRV-SIGN-KEY-001") is True

    def test_private_key_from_file(self, tmp_path):
        from python.helpers.log_signer import generate_keypair, rsa_sign
        priv, _ = generate_keypair()
        key_file = tmp_path / "rsa_key.pem"
        key_file.write_text(priv)
        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY_PATH": str(key_file),
            "EVIDENCE_RSA_KEY_ID": "004",
        }, clear=True):
            result = rsa_sign("payload")
            assert result is not None
            assert result[1] == "KRV-SIGN-KEY-004"


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrityBlock — RSA Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrityBlockRSA:

    @pytest.fixture(autouse=True)
    def _setup_rsa(self):
        from python.helpers.log_signer import generate_keypair
        import json
        priv, pub = generate_keypair()
        self._env_patch = patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": priv,
            "EVIDENCE_RSA_KEY_ID": "002",
            "EVIDENCE_RSA_PUBLIC_KEYS": json.dumps({"002": pub}),
        })
        self._env_patch.start()
        yield
        self._env_patch.stop()

    def test_from_session_uses_rsa_when_available(self):
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
        assert block.signature_log.startswith("rsa-pss-sha256:")
        assert block.signature_key_id == "KRV-SIGN-KEY-002"
        assert "RSA-PSS-SHA256" in block.signature_method

    def test_verify_signature_rsa_succeeds(self):
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
        assert block.verify_signature("q", "r", session_id="S1") is True

    def test_verify_signature_rsa_fails_on_tampered_stored_hash(self):
        """If an attacker modifies a stored hash, the RSA signature becomes invalid."""
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
        block.hash_request = "sha256:tampered_hash_value"
        assert block.verify_signature("q", "r", session_id="S1") is False

    def test_tampered_content_detected_by_verify_then_signature(self):
        """Full tamper detection: verify() catches content change,
        and verify_signature() validates the cryptographic proof is intact."""
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")

        assert block.verify("q", "r") is True
        assert block.verify_signature("q", "r", session_id="S1") is True

        assert block.verify("TAMPERED", "r") is False
        assert block.verify("q", "TAMPERED") is False

        assert block.verify_signature("q", "r", session_id="S1") is True

    def test_report_table_shows_rsa_method(self):
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock.from_session(query="q", response="r")
        table = block.to_report_table()
        assert "RSA-PSS-SHA256" in table
        assert "non-repudiation" in table


class TestIntegrityBlockHMACFallback:

    def test_falls_back_to_hmac_without_rsa(self):
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY": "test-key"}, clear=True):
            from python.helpers.integrity_block import IntegrityBlock
            block = IntegrityBlock.from_session(query="q", response="r")
            assert block.signature_log.startswith("hmac-sha256:")
            assert "HMAC-SHA256" in block.signature_method
            assert "fallback" in block.signature_method

    def test_verify_signature_hmac_succeeds(self):
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY": "test-key"}, clear=True):
            from python.helpers.integrity_block import IntegrityBlock
            block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
            assert block.verify_signature("q", "r", session_id="S1") is True

    def test_verify_signature_returns_false_on_empty(self):
        from python.helpers.integrity_block import IntegrityBlock
        block = IntegrityBlock()
        assert block.verify_signature("q", "r") is False


# ═══════════════════════════════════════════════════════════════════════════════
# Monitoring — ObservabilityMetrics
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditMetrics:

    def setup_method(self):
        from python.observability.runtime import ObservabilityMetrics
        ObservabilityMetrics.reset_for_tests()

    def test_new_audit_counters_in_snapshot(self):
        from python.observability.runtime import ObservabilityMetrics
        m = ObservabilityMetrics.get()
        snap = m.snapshot()
        assert "audit_reports_generated_total" in snap
        assert "audit_reports_failed_total" in snap
        assert "audit_report_generation_ms_total" in snap
        assert "audit_report_size_bytes_total" in snap

    def test_incr_audit_counters(self):
        from python.observability.runtime import ObservabilityMetrics
        m = ObservabilityMetrics.get()
        m.incr("audit_reports_generated_total")
        m.incr("audit_report_generation_ms_total", 42)
        m.incr("audit_report_size_bytes_total", 5000)
        snap = m.snapshot()
        assert snap["audit_reports_generated_total"] == 1
        assert snap["audit_report_generation_ms_total"] == 42
        assert snap["audit_report_size_bytes_total"] == 5000


class TestStorageMetricsIntegration:

    def setup_method(self):
        from python.observability.runtime import ObservabilityMetrics
        ObservabilityMetrics.reset_for_tests()

    def test_store_audit_report_emits_metrics(self, tmp_path):
        from python.helpers.audit_report_storage import store_audit_report
        from python.observability.runtime import ObservabilityMetrics

        result = store_audit_report(
            "ctx-test",
            "# Report\nContent",
            generate_pdf=False,
            folder_override=str(tmp_path),
        )
        assert result is not None

        snap = ObservabilityMetrics.get().snapshot()
        assert snap["audit_reports_generated_total"] == 1
        assert snap["audit_report_generation_ms_total"] >= 0
        assert snap["audit_report_size_bytes_total"] > 0

    def test_failed_store_increments_failure_counter(self, tmp_path):
        from python.helpers.audit_report_storage import store_audit_report
        from python.observability.runtime import ObservabilityMetrics

        bad_folder = str(tmp_path / "nonexistent" / "deep" / "path")
        with patch("python.helpers.audit_report_storage.os.makedirs", side_effect=PermissionError):
            store_audit_report("ctx-fail", "content", folder_override=bad_folder)

        snap = ObservabilityMetrics.get().snapshot()
        assert snap["audit_reports_failed_total"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Retention — Purge
# ═══════════════════════════════════════════════════════════════════════════════


class TestRetentionPurge:

    def test_purge_deletes_old_reports(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports, AUDIT_REPORT_MD

        old_folder = tmp_path / "chat-old"
        old_folder.mkdir()
        report = old_folder / AUDIT_REPORT_MD
        report.write_text("# Old report")
        very_old_mtime = time.time() - (6 * 365 * 86400)
        os.utime(str(report), (very_old_mtime, very_old_mtime))

        deleted = purge_expired_reports(max_age_days=1825, chats_dir_override=str(tmp_path))
        assert len(deleted) == 1
        assert not old_folder.exists()

    def test_purge_preserves_recent_reports(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports, AUDIT_REPORT_MD

        recent_folder = tmp_path / "chat-recent"
        recent_folder.mkdir()
        (recent_folder / AUDIT_REPORT_MD).write_text("# Fresh report")

        deleted = purge_expired_reports(max_age_days=1825, chats_dir_override=str(tmp_path))
        assert len(deleted) == 0
        assert recent_folder.exists()

    def test_purge_preserves_chats_without_reports(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports

        no_report_folder = tmp_path / "chat-no-report"
        no_report_folder.mkdir()
        (no_report_folder / "chat.json").write_text("{}")

        deleted = purge_expired_reports(max_age_days=0, chats_dir_override=str(tmp_path))
        assert len(deleted) == 0
        assert no_report_folder.exists()

    def test_purge_respects_env_var(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports, AUDIT_REPORT_MD

        folder = tmp_path / "chat-env"
        folder.mkdir()
        report = folder / AUDIT_REPORT_MD
        report.write_text("# Report")
        old_mtime = time.time() - (10 * 86400)
        os.utime(str(report), (old_mtime, old_mtime))

        with patch.dict(os.environ, {"EVIDENCE_RETENTION_DAYS": "5"}):
            deleted = purge_expired_reports(chats_dir_override=str(tmp_path))
        assert len(deleted) == 1

    def test_purge_empty_dir_returns_empty(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports
        deleted = purge_expired_reports(chats_dir_override=str(tmp_path))
        assert deleted == []

    def test_purge_nonexistent_dir_returns_empty(self):
        from python.helpers.audit_report_storage import purge_expired_reports
        deleted = purge_expired_reports(chats_dir_override="/nonexistent/path")
        assert deleted == []


# ═══════════════════════════════════════════════════════════════════════════════
# Authorization — Compliance Roles
# ═══════════════════════════════════════════════════════════════════════════════


class TestCanAccessAuditReports:

    def _principal(self, **kwargs):
        from python.security.authorization import AccessPrincipal
        defaults = {
            "username": "alice",
            "organization": "Korev AI",
            "org_role": "MEMBER",
            "role": "admin",
            "workspace": "ws1",
            "compliance_role": None,
        }
        defaults.update(kwargs)
        return AccessPrincipal(**defaults)

    def test_owner_can_access(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(org_role="OWNER")
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is True
        assert "owner" in reason

    def test_dpo_can_access(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(compliance_role="DPO")
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is True
        assert "dpo" in reason

    def test_rssi_can_access(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(compliance_role="RSSI")
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is True
        assert "rssi" in reason

    def test_compliance_officer_can_access(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(compliance_role="COMPLIANCE_OFFICER")
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is True

    def test_regular_member_denied(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(org_role="MEMBER", compliance_role=None)
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is False
        assert "denied" in reason

    def test_cross_org_denied(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(org_role="OWNER", organization="Other Org")
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is False
        assert "cross_organization" in reason

    def test_anonymous_denied(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(username=None)
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is False
        assert "anonymous" in reason

    def test_missing_org_denied(self):
        from python.security.authorization import can_access_audit_reports
        p = self._principal(organization=None)
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is False


class TestAccessPrincipalComplianceRole:

    def test_compliance_role_default_none(self):
        from python.security.authorization import AccessPrincipal
        p = AccessPrincipal(
            username="bob",
            organization="Org",
            org_role="MEMBER",
            role="user",
            workspace="ws",
        )
        assert p.compliance_role is None

    def test_compliance_role_set(self):
        from python.security.authorization import AccessPrincipal
        p = AccessPrincipal(
            username="bob",
            organization="Org",
            org_role="MEMBER",
            role="user",
            workspace="ws",
            compliance_role="DPO",
        )
        assert p.compliance_role == "DPO"


class TestAuditReportsHandlerRBAC:
    """Integration: AuditReports handler honours fine-grained policy, not admin-only."""

    def test_requires_admin_is_false(self):
        from python.api.audit_reports import AuditReports
        assert AuditReports.requires_admin() is False

    def test_requires_auth_is_true(self):
        from python.api.audit_reports import AuditReports
        assert AuditReports.requires_auth() is True

    def test_dpo_not_blocked_by_requires_admin(self):
        """A DPO principal should pass can_access_audit_reports even though
        they are not admin — this was broken when requires_admin returned True."""
        from python.security.authorization import can_access_audit_reports, AccessPrincipal
        p = AccessPrincipal(
            username="dpo_user",
            organization="Korev AI",
            org_role="MEMBER",
            role="user",
            workspace="ws1",
            compliance_role="DPO",
        )
        allowed, reason = can_access_audit_reports(p, target_org="Korev AI")
        assert allowed is True
        assert "dpo" in reason

    def test_log_security_event_kwargs_match_signature(self):
        """Verify the log_security_event call in audit_reports uses correct kwargs."""
        import inspect
        from python.security.security_audit import log_security_event
        sig = inspect.signature(log_security_event)
        required_params = {
            name for name, param in sig.parameters.items()
            if param.default is inspect.Parameter.empty
            and param.kind in (
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        }
        assert "action" in required_params
        assert "decision" in required_params
        assert "user" in required_params
        assert "resource_type" in required_params
        assert "username" not in sig.parameters
        assert "details" not in sig.parameters


# ═══════════════════════════════════════════════════════════════════════════════
# Job Loop — Retention Hook
# ═══════════════════════════════════════════════════════════════════════════════


class TestJobLoopRetention:
    """Test the retention hook logic.

    job_loop.py imports TaskScheduler which pulls in the full agent chain
    (agent -> models -> whisper). We mock sys.modules to break the chain.
    """

    @pytest.fixture(autouse=True)
    def _mock_heavy_deps(self):
        import sys
        mods_to_mock = [
            "python.helpers.task_scheduler", "agent", "models",
            "python.helpers.settings", "python.helpers.whisper",
            "whisper", "python.helpers.defer", "python.helpers.git",
        ]
        saved = {}
        for mod in mods_to_mock:
            saved[mod] = sys.modules.get(mod)
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()

        if "python.helpers.job_loop" in sys.modules:
            del sys.modules["python.helpers.job_loop"]

        yield

        for mod, original in saved.items():
            if original is None:
                sys.modules.pop(mod, None)
            else:
                sys.modules[mod] = original
        sys.modules.pop("python.helpers.job_loop", None)

    def test_retention_check_is_guarded_by_interval(self):
        import python.helpers.job_loop as jl
        jl._last_retention_check = time.time()
        with patch("python.helpers.audit_report_storage.purge_expired_reports") as mock_purge:
            jl._run_retention_check_if_due()
            mock_purge.assert_not_called()

    def test_retention_check_runs_when_due(self):
        import python.helpers.job_loop as jl
        jl._last_retention_check = 0
        with patch("python.helpers.audit_report_storage.purge_expired_reports", return_value=[]) as mock_purge:
            jl._run_retention_check_if_due()
            mock_purge.assert_called_once()

    def test_retention_check_failsafe(self):
        import python.helpers.job_loop as jl
        jl._last_retention_check = 0
        with patch("python.helpers.audit_report_storage.purge_expired_reports", side_effect=RuntimeError("boom")):
            jl._run_retention_check_if_due()


# Benchmarks
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarks:

    def test_rsa_sign_verify_under_100ms(self):
        from python.helpers.log_signer import generate_keypair, rsa_sign, rsa_verify
        import json

        priv, pub = generate_keypair()
        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": priv,
            "EVIDENCE_RSA_KEY_ID": "001",
            "EVIDENCE_RSA_PUBLIC_KEYS": json.dumps({"001": pub}),
        }):
            payload = "session_id=TEST\nhash=sha256:abc123"

            t0 = time.monotonic()
            sig_b64, key_id, _ = rsa_sign(payload)
            result = rsa_verify(payload, sig_b64, key_id)
            elapsed_ms = (time.monotonic() - t0) * 1000

            assert result is True
            assert elapsed_ms < 100, f"RSA sign+verify took {elapsed_ms:.1f}ms (> 100ms)"

    def test_integrity_block_rsa_under_200ms(self):
        from python.helpers.log_signer import generate_keypair
        from python.helpers.integrity_block import IntegrityBlock
        import json

        priv, pub = generate_keypair()
        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": priv,
            "EVIDENCE_RSA_KEY_ID": "001",
            "EVIDENCE_RSA_PUBLIC_KEYS": json.dumps({"001": pub}),
        }):
            t0 = time.monotonic()
            block = IntegrityBlock.from_session(
                query="Benchmark query",
                response="Benchmark response" * 100,
                document="Document content" * 50,
                session_id="KRV-SES-BENCH",
            )
            elapsed_ms = (time.monotonic() - t0) * 1000
            assert block.signature_log.startswith("rsa-pss-sha256:")
            assert elapsed_ms < 200, f"IntegrityBlock RSA took {elapsed_ms:.1f}ms (> 200ms)"

    def test_retention_purge_under_200ms_for_100_folders(self, tmp_path):
        from python.helpers.audit_report_storage import purge_expired_reports, AUDIT_REPORT_MD

        for i in range(100):
            folder = tmp_path / f"chat-{i:04d}"
            folder.mkdir()
            (folder / AUDIT_REPORT_MD).write_text(f"# Report {i}")

        t0 = time.monotonic()
        deleted = purge_expired_reports(max_age_days=99999, chats_dir_override=str(tmp_path))
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert len(deleted) == 0
        assert elapsed_ms < 200, f"Retention scan took {elapsed_ms:.1f}ms (> 200ms)"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration — Full Flow
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrationFullFlow:

    def test_rsa_sign_store_verify_cycle(self, tmp_path):
        """Full cycle: generate keys, sign report, store, verify."""
        from python.helpers.log_signer import generate_keypair
        from python.helpers.integrity_block import IntegrityBlock
        from python.helpers.audit_report_storage import store_audit_report, AUDIT_REPORT_MD
        import json

        priv, pub = generate_keypair()
        with patch.dict(os.environ, {
            "EVIDENCE_RSA_PRIVATE_KEY": priv,
            "EVIDENCE_RSA_KEY_ID": "001",
            "EVIDENCE_RSA_PUBLIC_KEYS": json.dumps({"001": pub}),
        }):
            query = "Is this AI Act compliant?"
            response = "Based on Article 52..."

            block = IntegrityBlock.from_session(
                query=query,
                response=response,
                session_id="KRV-SES-INTEG",
            )

            assert block.verify(query, response) is True
            assert block.verify_signature(query, response, session_id="KRV-SES-INTEG") is True

            report_md = f"# Audit Report\n\n{block.to_report_table()}"
            path = store_audit_report(
                "integ-test",
                report_md,
                generate_pdf=False,
                folder_override=str(tmp_path),
            )
            assert path is not None
            assert os.path.isfile(path)

            stored = open(path, encoding="utf-8").read()
            assert "rsa-pss-sha256:" in stored
            assert "RSA-PSS-SHA256" in stored

    def test_hmac_fallback_full_cycle(self, tmp_path):
        """Without RSA keys, HMAC is used and everything still works."""
        with patch.dict(os.environ, {"EVIDENCE_HMAC_KEY": "test-key"}, clear=True):
            from python.helpers.integrity_block import IntegrityBlock
            from python.helpers.audit_report_storage import store_audit_report

            block = IntegrityBlock.from_session(query="q", response="r", session_id="S1")
            assert block.signature_log.startswith("hmac-sha256:")
            assert block.verify("q", "r") is True
            assert block.verify_signature("q", "r", session_id="S1") is True

            path = store_audit_report("hmac-ctx", "# HMAC report",
                                       generate_pdf=False, folder_override=str(tmp_path))
            assert path is not None
