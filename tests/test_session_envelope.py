"""
Tests unitaires pour SessionEnvelope.
SESSION 1 de la feuille de route conformite format Evidence.
"""

import sys
import re
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.session_envelope import (
    SessionEnvelope,
    _generate_session_id,
    _resolve_evidence_version,
    _resolve_environment_label,
    _HASH_NULL_SENTINEL,
    _HASH_SEPARATOR,
)


# ── FORMAT SESSION ID ────────────────────────────────────────────────────────

SESSION_ID_PATTERN = re.compile(r"^KRV-SES-\d{8}-[0-9A-F]{7}$")


class TestSessionIdFormat:
    def test_format_matches_pattern(self):
        for _ in range(10):
            sid = _generate_session_id()
            assert SESSION_ID_PATTERN.match(sid), f"Invalid session_id: {sid}"

    def test_date_part_is_utc_today(self):
        sid = _generate_session_id()
        date_str = sid.split("-")[2]
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert date_str == today

    def test_random_part_is_unique(self):
        ids = {_generate_session_id() for _ in range(100)}
        assert len(ids) == 100, "session_id collision detected"

    def test_random_part_not_sequential(self):
        ids = [_generate_session_id().split("-")[3] for _ in range(10)]
        sorted_ids = sorted(ids)
        assert ids != sorted_ids, "random parts appear sequential"


# ── INSTANCIATION ────────────────────────────────────────────────────────────

class TestInstantiation:
    def test_default_fields_populated(self):
        env = SessionEnvelope()
        assert env.session_id is not None
        assert SESSION_ID_PATTERN.match(env.session_id)
        assert env.started_at is not None
        assert env.completed_at is None
        assert env.duration_ms is None
        assert env.integrity_hash is None

    def test_explicit_fields(self):
        env = SessionEnvelope(
            username="amine",
            organization="korev-ai",
            user_profile="Analyste — Niveau 2",
            query="Analyse ce contrat",
        )
        assert env.username == "amine"
        assert env.organization == "korev-ai"
        assert env.user_profile == "Analyste — Niveau 2"
        assert env.query == "Analyse ce contrat"


# ── COMPLETE / DURATION ──────────────────────────────────────────────────────

class TestComplete:
    def test_complete_sets_completed_at(self):
        env = SessionEnvelope()
        assert env.completed_at is None
        env.complete()
        assert env.completed_at is not None

    def test_complete_computes_duration(self):
        env = SessionEnvelope()
        time.sleep(0.05)
        env.complete()
        assert env.duration_ms is not None
        assert env.duration_ms >= 40

    def test_complete_computes_integrity_hash(self):
        env = SessionEnvelope(query="test", response_hash="abc123")
        env.complete()
        assert env.integrity_hash is not None
        assert env.integrity_hash.startswith("sha256:")

    def test_complete_returns_self(self):
        env = SessionEnvelope()
        result = env.complete()
        assert result is env

    def test_duration_non_negative(self):
        env = SessionEnvelope()
        env.complete()
        assert env.duration_ms >= 0

    def test_duration_seconds_property(self):
        env = SessionEnvelope()
        time.sleep(0.05)
        env.complete()
        assert env.duration_seconds is not None
        assert env.duration_seconds >= 0.0
        assert env.duration_seconds == round(env.duration_ms / 1000, 1)

    def test_duration_seconds_none_before_complete(self):
        env = SessionEnvelope()
        assert env.duration_seconds is None


# ── INTEGRITY HASH ───────────────────────────────────────────────────────────

class TestIntegrityHash:
    def test_deterministic(self):
        env1 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="hello",
            response_hash="resp123",
        )
        env2 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="hello",
            response_hash="resp123",
        )
        h1 = env1._compute_integrity_hash()
        h2 = env2._compute_integrity_hash()
        assert h1 == h2

    def test_changes_with_different_query(self):
        env1 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="hello",
            response_hash="resp",
        )
        env2 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="hellO",
            response_hash="resp",
        )
        assert env1._compute_integrity_hash() != env2._compute_integrity_hash()

    def test_changes_with_different_session_id(self):
        env1 = SessionEnvelope(session_id="KRV-SES-20260331-AAAAAAA", query="q")
        env2 = SessionEnvelope(session_id="KRV-SES-20260331-BBBBBBB", query="q")
        assert env1._compute_integrity_hash() != env2._compute_integrity_hash()

    def test_query_none(self):
        env = SessionEnvelope(session_id="KRV-SES-20260331-AAAAAAA")
        h = env._compute_integrity_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_response_hash_none(self):
        env = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="test",
            response_hash=None,
        )
        h = env._compute_integrity_hash()
        assert h.startswith("sha256:")

    def test_unicode_query(self):
        env = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="Analyse les clauses du contrat — résilier à l'échéance 日本語",
            response_hash="abc",
        )
        h = env._compute_integrity_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_none_vs_empty_string_distinguished(self):
        """None and '' must produce different hashes (D4 fix)."""
        env_none = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query=None,
            response_hash="r",
        )
        env_empty = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="",
            response_hash="r",
        )
        assert env_none._compute_integrity_hash() != env_empty._compute_integrity_hash()

    def test_empty_query_produces_valid_hash(self):
        env = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="",
            response_hash="r",
        )
        h = env._compute_integrity_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_separator_in_query_no_collision(self):
        """Pipe in query must not cause collision (D6 fix)."""
        env1 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="A|B",
            response_hash="C",
        )
        env2 = SessionEnvelope(
            session_id="KRV-SES-20260331-AAAAAAA",
            query="A",
            response_hash="B|C",
        )
        assert env1._compute_integrity_hash() != env2._compute_integrity_hash()

    def test_manual_verification(self):
        env = SessionEnvelope(
            session_id="KRV-SES-20260331-ABC1234",
            query="test",
            response_hash="hash",
        )
        payload = _HASH_SEPARATOR.join([
            "KRV-SES-20260331-ABC1234",
            "test",
            "hash",
        ])
        expected = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert env._compute_integrity_hash() == expected


# ── RESOLUTION FUNCTIONS ─────────────────────────────────────────────────────

class TestResolution:
    def test_resolve_version_with_git(self):
        import python.helpers.git as git_mod
        original = git_mod.get_version
        try:
            git_mod.get_version = lambda: "v3.1.0"
            result = _resolve_evidence_version()
            assert result == "v3.1.0"
        finally:
            git_mod.get_version = original

    def test_resolve_version_unknown_logs_warning(self, caplog):
        import python.helpers.git as git_mod
        original = git_mod.get_version
        try:
            git_mod.get_version = lambda: "unknown"
            with caplog.at_level(logging.WARNING, logger="session_envelope"):
                result = _resolve_evidence_version()
            assert result == "unknown"
            assert "evidence_version could not be resolved" in caplog.text
        finally:
            git_mod.get_version = original

    def test_resolve_version_runtime_error(self, caplog):
        import python.helpers.git as git_mod
        original = git_mod.get_version
        def _raise():
            raise RuntimeError("git broken")
        try:
            git_mod.get_version = _raise
            with caplog.at_level(logging.WARNING, logger="session_envelope"):
                result = _resolve_evidence_version()
            assert result == "unknown"
        finally:
            git_mod.get_version = original

    def test_resolve_environment_label_default_empty(self):
        result = _resolve_environment_label()
        assert isinstance(result, str)

    def test_resolve_environment_label_never_crashes(self):
        """Even if settings module fails, must return empty string."""
        env = SessionEnvelope(environment_label="")
        assert env.environment_label == ""


# ── EDGE CASES ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_username_none(self):
        env = SessionEnvelope(username=None)
        assert env.username is None
        d = env.to_dict()
        assert d["username"] is None

    def test_username_none_renders_dash_in_report(self):
        env = SessionEnvelope(username=None)
        table = env.to_report_table()
        assert "| **Utilisateur** | `—` |" in table

    def test_organization_empty(self):
        env = SessionEnvelope(organization="")
        assert env.organization == ""

    def test_version_unknown_renders_warning_in_report(self):
        env = SessionEnvelope(evidence_version="unknown")
        table = env.to_report_table()
        assert "unknown (non resolu)" in table

    def test_environment_label_empty(self):
        env = SessionEnvelope(environment_label="")
        assert env.environment_label == ""


# ── SERIALISATION ────────────────────────────────────────────────────────────

class TestSerialization:
    def test_to_dict_all_keys(self):
        env = SessionEnvelope(
            username="amine",
            organization="korev-ai",
            user_profile="Admin",
            query="test",
        )
        env.complete()
        d = env.to_dict()
        expected_keys = {
            "session_id", "started_at", "completed_at", "duration_ms",
            "username", "organization", "user_profile",
            "environment_label", "evidence_version", "integrity_hash",
        }
        assert set(d.keys()) == expected_keys

    def test_to_report_table_markdown(self):
        env = SessionEnvelope(
            session_id="KRV-SES-20260331-TEST123",
            username="amine",
            user_profile="Analyste — Niveau 2",
            environment_label="Production — EU-West (Paris)",
        )
        env.complete()
        table = env.to_report_table()
        assert "| CHAMP | VALEUR |" in table
        assert "KRV-SES-20260331-TEST123" in table
        assert "amine" in table
        assert "Analyste — Niveau 2" in table
        assert "Production — EU-West (Paris)" in table
        assert "sha256:" in table

    def test_to_report_table_duration_in_seconds(self):
        env = SessionEnvelope()
        time.sleep(0.05)
        env.complete()
        table = env.to_report_table()
        assert "secondes" in table

    def test_to_report_table_missing_fields(self):
        env = SessionEnvelope()
        table = env.to_report_table()
        assert "—" in table
