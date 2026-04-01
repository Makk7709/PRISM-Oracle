"""
SESSION 6 + 6.1 — Tests for audit metadata wiring into the pipeline.

Tests the two extensions in monologue_start:
  - _03_session_envelope_init: creates SessionEnvelope BEFORE pipelines
  - _20_audit_metadata_append: appends audit tables to pipeline response AFTER pipelines

SESSION 6.1 additions:
  - C1: extension in correct hook (monologue_start, not message_loop_start)
  - D1: user_profile resolves human profile via UserManager, falls back to agent profile
  - D3: organisation rendered in to_report_table()
  - D4: extension cache invalidation function

Test categories:
  - SessionEnvelopeInit: context extraction, query extraction, fail-safe
  - SessionEnvelopeInit_D1: human profile resolution with/without Flask context
  - AuditMetadataAppend: response enrichment, hash integrity, tracker resolution, fail-safe
  - AuditMetadataAppend_D3: organisation visible in rendered report
  - ExtensionCache_D4: cache invalidation
  - Integration: full chain init → pipeline → append
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MockContext:
    username: Optional[str] = "amine"
    organization: Optional[str] = "Korev AI"
    workspace: Optional[str] = "/tmp/test"


@dataclass
class MockConfig:
    profile: str = "legal_safe"


@dataclass
class MockMessage:
    content: str = "Rédige un CDI pour un Lead IA"


class MockAgent:
    """Minimal agent mock with set_data/get_data."""
    def __init__(
        self,
        username: str = "amine",
        organization: str = "Korev AI",
        profile: str = "legal_safe",
    ):
        self.data: Dict[str, Any] = {}
        self.context = MockContext(username=username, organization=organization)
        self.config = MockConfig(profile=profile)
        self.last_user_message = None

    def get_data(self, field: str):
        return self.data.get(field, None)

    def set_data(self, field: str, value):
        self.data[field] = value


class MockLoopData:
    def __init__(self, user_message=None):
        self.user_message = user_message


@dataclass
class MockStrategicResult:
    consolidated_response: str = "# Contrat CDI\n\nContenu du contrat..."
    validation_passed: bool = True
    pipeline_tracker: Any = None


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT EXTENSIONS (lazy to avoid agent import side-effects)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_envelope_init(agent, **kwargs):
    """Instantiate SessionEnvelopeInit with mock agent."""
    from python.extensions.monologue_start._03_session_envelope_init import (
        SessionEnvelopeInit,
    )
    ext = SessionEnvelopeInit.__new__(SessionEnvelopeInit)
    ext.agent = agent
    ext.kwargs = kwargs
    return ext


def _make_audit_append(agent, **kwargs):
    """Instantiate AuditMetadataAppend with mock agent."""
    from python.extensions.monologue_start._20_audit_metadata_append import (
        AuditMetadataAppend,
    )
    ext = AuditMetadataAppend.__new__(AuditMetadataAppend)
    ext.agent = agent
    ext.kwargs = kwargs
    return ext


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SessionEnvelopeInit
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionEnvelopeInit:

    def test_creates_envelope_with_context(self):
        agent = MockAgent(username="aya", organization="Korev AI")
        ext = _make_envelope_init(agent)
        loop_data = MockLoopData(user_message=MockMessage("Analyse ce contrat"))

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert envelope is not None
        assert envelope.username == "aya"
        assert envelope.organization == "Korev AI"
        # Without Flask context, falls back to agent profile
        assert envelope.user_profile == "legal_safe"

    def test_session_id_format(self):
        agent = MockAgent()
        ext = _make_envelope_init(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))

        envelope = agent.get_data("_session_envelope")
        assert envelope is not None
        assert re.match(r"^KRV-SES-\d{8}-[0-9A-F]{7}$", envelope.session_id)

    def test_extracts_query_from_loop_data(self):
        agent = MockAgent()
        ext = _make_envelope_init(agent)
        loop_data = MockLoopData(
            user_message=MockMessage("Rédige un contrat CDI cadre")
        )

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert envelope.query == "Rédige un contrat CDI cadre"

    def test_extracts_query_from_last_user_message_fallback(self):
        agent = MockAgent()
        agent.last_user_message = MockMessage("Fallback query text")
        ext = _make_envelope_init(agent)
        loop_data = MockLoopData(user_message=None)

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert envelope.query == "Fallback query text"

    def test_empty_query_when_no_message(self):
        agent = MockAgent()
        ext = _make_envelope_init(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))

        envelope = agent.get_data("_session_envelope")
        assert envelope.query is None or envelope.query == ""

    def test_truncates_long_query(self):
        agent = MockAgent()
        ext = _make_envelope_init(agent)
        long_text = "x" * 5000
        loop_data = MockLoopData(user_message=MockMessage(long_text))

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert len(envelope.query) <= 2000

    def test_handles_none_context_gracefully(self):
        agent = MockAgent()
        agent.context = None
        ext = _make_envelope_init(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))
        envelope = agent.get_data("_session_envelope")
        assert envelope is not None
        assert envelope.username is None

    def test_handles_missing_profile(self):
        agent = MockAgent()
        agent.config.profile = ""
        ext = _make_envelope_init(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "default"

    def test_fresh_envelope_each_call(self):
        agent = MockAgent()
        ext = _make_envelope_init(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))
        first_id = agent.get_data("_session_envelope").session_id

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))
        second_id = agent.get_data("_session_envelope").session_id

        assert first_id != second_id


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AuditMetadataAppend
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditMetadataAppend:

    def _setup_pipeline_agent(self, response="# CDI\n\nContenu..."):
        """Create agent with pipeline response and session envelope."""
        from python.helpers.session_envelope import SessionEnvelope

        agent = MockAgent()
        agent.set_data("_pipeline_final_response", response)

        envelope = SessionEnvelope(
            username="amine",
            organization="Korev AI",
            user_profile="legal_safe",
            query="Rédige un CDI",
        )
        agent.set_data("_session_envelope", envelope)
        return agent

    def test_skips_when_no_pipeline_response(self):
        agent = MockAgent()
        ext = _make_audit_append(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute())

        assert agent.get_data("_pipeline_final_response") is None

    def test_appends_session_table_to_response(self):
        agent = self._setup_pipeline_agent()
        ext = _make_audit_append(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert "Rapport d'audit Evidence" in updated
        assert "Identite de la session" in updated
        assert "KRV-SES-" in updated

    def test_envelope_is_completed(self):
        agent = self._setup_pipeline_agent()
        ext = _make_audit_append(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute())

        envelope = agent.get_data("_session_envelope")
        assert envelope.completed_at is not None
        assert envelope.integrity_hash is not None
        assert envelope.integrity_hash.startswith("sha256:")

    def test_response_hash_covers_original_response(self):
        original = "# CDI\n\nContenu original du contrat"
        expected_hash = "sha256:" + hashlib.sha256(
            original.encode("utf-8")
        ).hexdigest()

        agent = self._setup_pipeline_agent(response=original)
        ext = _make_audit_append(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute())

        envelope = agent.get_data("_session_envelope")
        assert envelope.response_hash == expected_hash

    def test_original_response_preserved_at_start(self):
        original = "# CDI\n\nContenu original"
        agent = self._setup_pipeline_agent(response=original)
        ext = _make_audit_append(agent)

        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert updated.startswith(original)

    def test_appends_pipeline_tracker_when_available(self):
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = self._setup_pipeline_agent()
        tracker = PipelineTracker()
        tracker.start_step("legal_safe", "Agent juridique")
        tracker.complete_step("legal_safe")
        tracker.start_step("researcher", "Agent recherche")
        tracker.complete_step("researcher")

        result = MockStrategicResult(pipeline_tracker=tracker)
        agent.set_data("_strategic_result", result)

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert "Pipeline d'execution" in updated
        assert "legal_safe" in updated
        assert "researcher" in updated

    def test_resolves_tracker_from_agent_data_fallback(self):
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = self._setup_pipeline_agent()
        tracker = PipelineTracker()
        tracker.start_step("developer", "Agent dev")
        tracker.complete_step("developer")
        agent.set_data("_pipeline_tracker", tracker)

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert "developer" in updated

    def test_shows_non_activated_agents(self):
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = self._setup_pipeline_agent()
        tracker = PipelineTracker()
        tracker.start_step("legal_safe", "Agent juridique")
        tracker.complete_step("legal_safe")
        agent.set_data("_strategic_result", MockStrategicResult(pipeline_tracker=tracker))

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert "Agents non actives" in updated

    def test_handles_envelope_complete_failure(self):
        agent = MockAgent()
        agent.set_data("_pipeline_final_response", "# Response")
        agent.set_data("_session_envelope", "not_an_envelope")

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert updated == "# Response"

    def test_handles_tracker_render_failure(self):
        agent = self._setup_pipeline_agent()
        broken_tracker = MagicMock()
        broken_tracker.get_activated.side_effect = RuntimeError("boom")
        agent.set_data("_strategic_result", MockStrategicResult(pipeline_tracker=broken_tracker))

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert "Identite de la session" in updated

    def test_pipeline_appends_grid_and_meta_without_envelope_or_tracker(self):
        """SESSION 7A : sans envelope/tracker, S6 n'ajoute rien mais 7A ajoute grille + meta."""
        agent = MockAgent()
        agent.set_data("_pipeline_final_response", "# Response")

        ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute())

        updated = agent.get_data("_pipeline_final_response")
        assert updated.startswith("# Response")
        assert "## Rapport d'audit Evidence" in updated
        assert "Grille de conformite reglementaire" in updated
        assert "Metadonnees techniques" in updated


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Integration — Full chain init → append
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationChain:

    def test_full_pipeline_chain(self):
        """Simulate: message_loop_start (init) → strategic pipeline → monologue_start (append)."""
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = MockAgent(username="amine", organization="Korev AI")

        # Step 1: message_loop_start — init envelope
        init_ext = _make_envelope_init(agent)
        loop_data = MockLoopData(
            user_message=MockMessage("Rédige un CDI cadre Syntec pour un Lead IA")
        )
        asyncio.get_event_loop().run_until_complete(init_ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert envelope is not None
        assert envelope.session_id.startswith("KRV-SES-")

        # Step 2: strategic pipeline sets response + tracker (simulated)
        tracker = PipelineTracker()
        tracker.start_step("legal_safe", "Rédaction juridique")
        tracker.complete_step("legal_safe")
        tracker.start_step("researcher", "Recherche sources")
        tracker.complete_step("researcher")
        tracker.start_step("finance", "Analyse rémunération")
        tracker.complete_step("finance")

        strategic_response = "# CONTRAT CDI\n\nArticle 1 — Nature du contrat\n..."
        agent.set_data("_pipeline_final_response", strategic_response)
        agent.set_data(
            "_strategic_result",
            MockStrategicResult(
                consolidated_response=strategic_response,
                pipeline_tracker=tracker,
            ),
        )

        # Step 3: monologue_start _20 — append audit metadata
        append_ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(append_ext.execute())

        # Verify final response
        final = agent.get_data("_pipeline_final_response")

        # Original content preserved
        assert final.startswith("# CONTRAT CDI")

        # Session identity present
        assert "KRV-SES-" in final
        assert "amine" in final

        # Integrity hash computed
        envelope = agent.get_data("_session_envelope")
        assert envelope.completed_at is not None
        assert envelope.integrity_hash.startswith("sha256:")
        assert envelope.response_hash.startswith("sha256:")

        # Pipeline tracker present
        assert "Pipeline d'execution" in final
        assert "legal_safe" in final
        assert "researcher" in final
        assert "finance" in final
        assert "Agents non actives" in final

        # Duration computed
        assert envelope.duration_ms is not None
        assert envelope.duration_ms >= 0

    def test_chain_without_pipeline(self):
        """Normal LLM request — no pipeline response, no append."""
        agent = MockAgent()

        init_ext = _make_envelope_init(agent)
        asyncio.get_event_loop().run_until_complete(
            init_ext.execute(loop_data=MockLoopData(user_message=MockMessage("Bonjour")))
        )

        assert agent.get_data("_session_envelope") is not None
        assert agent.get_data("_pipeline_final_response") is None

        append_ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(append_ext.execute())

        assert agent.get_data("_pipeline_final_response") is None

    def test_chain_with_empty_tracker(self):
        """Pipeline response but tracker has no steps — only session table appended."""
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = MockAgent()
        init_ext = _make_envelope_init(agent)
        asyncio.get_event_loop().run_until_complete(
            init_ext.execute(loop_data=MockLoopData(user_message=MockMessage("Test")))
        )

        agent.set_data("_pipeline_final_response", "# Response")
        agent.set_data(
            "_strategic_result",
            MockStrategicResult(pipeline_tracker=PipelineTracker()),
        )

        append_ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(append_ext.execute())

        final = agent.get_data("_pipeline_final_response")
        assert "Identite de la session" in final
        assert "Pipeline d'execution" not in final

    def test_response_hash_is_deterministic(self):
        """Same response content → same response_hash."""
        response = "# CDI\n\nArticle 1..."

        agent1 = MockAgent()
        agent2 = MockAgent()

        for ag in (agent1, agent2):
            init_ext = _make_envelope_init(ag)
            asyncio.get_event_loop().run_until_complete(
                init_ext.execute(loop_data=MockLoopData(user_message=MockMessage("q")))
            )
            ag.set_data("_pipeline_final_response", response)
            append_ext = _make_audit_append(ag)
            asyncio.get_event_loop().run_until_complete(append_ext.execute())

        hash1 = agent1.get_data("_session_envelope").response_hash
        hash2 = agent2.get_data("_session_envelope").response_hash
        assert hash1 == hash2

    def test_different_responses_different_hashes(self):
        """Different response content → different response_hash."""
        agents = []
        for resp in ("Response A", "Response B"):
            agent = MockAgent()
            init_ext = _make_envelope_init(agent)
            asyncio.get_event_loop().run_until_complete(
                init_ext.execute(loop_data=MockLoopData(user_message=MockMessage("q")))
            )
            agent.set_data("_pipeline_final_response", resp)
            append_ext = _make_audit_append(agent)
            asyncio.get_event_loop().run_until_complete(append_ext.execute())
            agents.append(agent)

        hash_a = agents[0].get_data("_session_envelope").response_hash
        hash_b = agents[1].get_data("_session_envelope").response_hash
        assert hash_a != hash_b


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 6.1 — Tests for defect corrections
# ═══════════════════════════════════════════════════════════════════════════════

class TestD1_HumanProfileResolution:
    """D1 FIX: user_profile resolves human profile from UserManager."""

    def test_fallback_to_agent_profile_without_flask(self):
        """Without Flask context, user_profile falls back to agent config profile."""
        agent = MockAgent(username="amine", profile="legal_safe")
        ext = _make_envelope_init(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "legal_safe"

    def test_resolves_human_profile_with_flask(self):
        """With Flask context and UserManager, user_profile = human profile."""
        mock_user_mgr = MagicMock()
        mock_user_mgr.get_user_profile.return_value = "Admin"

        mock_app = MagicMock()
        mock_app.config = {"USER_MANAGER": mock_user_mgr}

        agent = MockAgent(username="amine", profile="legal_safe")
        ext = _make_envelope_init(agent)

        with patch("flask.current_app", mock_app):
            asyncio.get_event_loop().run_until_complete(
                ext.execute(loop_data=MockLoopData())
            )

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "Admin"
        mock_user_mgr.get_user_profile.assert_called_once_with("amine")

    def test_fallback_when_user_manager_returns_empty(self):
        """If UserManager returns empty string, falls back to agent profile."""
        mock_user_mgr = MagicMock()
        mock_user_mgr.get_user_profile.return_value = ""

        mock_app = MagicMock()
        mock_app.config = {"USER_MANAGER": mock_user_mgr}

        agent = MockAgent(username="amine", profile="legal_safe")
        ext = _make_envelope_init(agent)

        with patch(
            "python.extensions.monologue_start._03_session_envelope_init.current_app",
            mock_app,
            create=True,
        ):
            asyncio.get_event_loop().run_until_complete(
                ext.execute(loop_data=MockLoopData())
            )

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "legal_safe"

    def test_fallback_when_username_is_none(self):
        """With no username, skip UserManager entirely."""
        agent = MockAgent(profile="legal_safe")
        agent.context.username = None
        ext = _make_envelope_init(agent)
        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=MockLoopData()))

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "legal_safe"

    def test_fallback_when_user_manager_raises(self):
        """If UserManager crashes, falls back gracefully."""
        mock_user_mgr = MagicMock()
        mock_user_mgr.get_user_profile.side_effect = RuntimeError("db error")

        mock_app = MagicMock()
        mock_app.config = {"USER_MANAGER": mock_user_mgr}

        agent = MockAgent(username="amine", profile="legal_safe")
        ext = _make_envelope_init(agent)

        with patch(
            "python.extensions.monologue_start._03_session_envelope_init.current_app",
            mock_app,
            create=True,
        ):
            asyncio.get_event_loop().run_until_complete(
                ext.execute(loop_data=MockLoopData())
            )

        envelope = agent.get_data("_session_envelope")
        assert envelope.user_profile == "legal_safe"


class TestD3_OrganisationInReport:
    """D3 FIX: organisation field rendered in to_report_table()."""

    def test_organisation_present_in_report_table(self):
        from python.helpers.session_envelope import SessionEnvelope

        envelope = SessionEnvelope(
            username="amine",
            organization="Korev AI",
            user_profile="Admin",
        )
        table = envelope.to_report_table()
        assert "Organisation" in table
        assert "Korev AI" in table

    def test_organisation_dash_when_none(self):
        from python.helpers.session_envelope import SessionEnvelope

        envelope = SessionEnvelope(username="amine", organization=None)
        table = envelope.to_report_table()
        assert "| **Organisation** | `—` |" in table

    def test_full_report_table_has_all_fields(self):
        from python.helpers.session_envelope import SessionEnvelope

        envelope = SessionEnvelope(
            username="aya",
            organization="DICA France",
            user_profile="Juriste",
        )
        envelope.complete()
        table = envelope.to_report_table()
        expected_fields = [
            "Session ID", "Horodatage debut", "Horodatage fin",
            "Duree de traitement", "Utilisateur", "Organisation",
            "Profil utilisateur", "Environnement", "Version KOREV Evidence",
            "Hash d'integrite session",
        ]
        for f in expected_fields:
            assert f in table, f"Missing field: {f}"


class TestD4_ExtensionCacheInvalidation:
    """D4 FIX: extension cache can be invalidated."""

    def test_invalidate_entire_cache(self):
        from python.helpers.extension import _cache, invalidate_extension_cache

        _cache["test/folder/a"] = [MagicMock()]
        _cache["test/folder/b"] = [MagicMock()]

        invalidate_extension_cache()

        assert len(_cache) == 0

    def test_invalidate_specific_folder(self):
        from python.helpers.extension import _cache, invalidate_extension_cache
        from python.helpers import files

        abs_a = files.get_abs_path("test/specific/a")
        abs_b = files.get_abs_path("test/specific/b")
        _cache[abs_a] = [MagicMock()]
        _cache[abs_b] = [MagicMock()]

        invalidate_extension_cache("test/specific/a")

        assert abs_a not in _cache
        assert abs_b in _cache

        del _cache[abs_b]

    def test_invalidate_nonexistent_folder_no_error(self):
        from python.helpers.extension import invalidate_extension_cache

        invalidate_extension_cache("nonexistent/folder/xyz")


class TestC1_MonologueStartPlacement:
    """C1 FIX: _03 is in monologue_start, not message_loop_start."""

    def test_extension_importable_from_monologue_start(self):
        from python.extensions.monologue_start._03_session_envelope_init import (
            SessionEnvelopeInit,
        )
        assert SessionEnvelopeInit is not None

    def test_old_message_loop_start_path_does_not_exist(self):
        import importlib
        try:
            importlib.import_module(
                "python.extensions.message_loop_start._05_session_envelope_init"
            )
            assert False, "Old module should not exist"
        except (ImportError, ModuleNotFoundError):
            pass

    def test_extension_runs_in_monologue_start_context(self):
        """Verify init works when called like monologue_start (with loop_data kwarg)."""
        agent = MockAgent(username="test_c1")
        ext = _make_envelope_init(agent)
        loop_data = MockLoopData(user_message=MockMessage("test C1"))

        asyncio.get_event_loop().run_until_complete(ext.execute(loop_data=loop_data))

        envelope = agent.get_data("_session_envelope")
        assert envelope is not None
        assert envelope.username == "test_c1"
        assert envelope.query == "test C1"


class TestIntegrationChain_61:
    """SESSION 6.1: Integration tests covering all corrections together."""

    def test_full_chain_with_organisation_visible(self):
        """End-to-end: organisation now appears in final report."""
        from python.helpers.pipeline_tracker import PipelineTracker

        agent = MockAgent(username="amine", organization="Korev AI")

        init_ext = _make_envelope_init(agent)
        loop_data = MockLoopData(
            user_message=MockMessage("Rédige un CDI cadre")
        )
        asyncio.get_event_loop().run_until_complete(init_ext.execute(loop_data=loop_data))

        agent.set_data("_pipeline_final_response", "# CDI\n\nArticle 1...")
        tracker = PipelineTracker()
        tracker.start_step("legal_safe", "Juridique")
        tracker.complete_step("legal_safe")
        agent.set_data("_strategic_result", MockStrategicResult(pipeline_tracker=tracker))

        append_ext = _make_audit_append(agent)
        asyncio.get_event_loop().run_until_complete(append_ext.execute())

        final = agent.get_data("_pipeline_final_response")
        assert "Korev AI" in final
        assert "Organisation" in final
        assert "amine" in final
        assert "KRV-SES-" in final
