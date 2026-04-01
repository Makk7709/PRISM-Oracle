"""
Tests unitaires — SESSION 7A : ReportMetadata

Couvre :
- Construction par defaut (valeurs saines)
- Factory from_session avec toutes les combinaisons de sources
- Serialisation to_dict / to_json / to_markdown_block
- Fail-safe : sources None, attributs manquants, exceptions dans tracker
"""

import json
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from python.helpers.report_metadata import ReportMetadata


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

def _make_envelope(**overrides):
    from python.helpers.session_envelope import SessionEnvelope
    env = SessionEnvelope(
        username="test_user",
        organization="Test Org",
    )
    env.session_id = overrides.get("session_id", "KRV-SES-TEST-001")
    env.evidence_version = overrides.get("evidence_version", "v1.2.3")
    env.complete()
    if "duration_ms" in overrides:
        env.duration_ms = overrides["duration_ms"]
    return env


def _make_tracker(agents=None):
    from python.helpers.pipeline_tracker import PipelineTracker
    tracker = PipelineTracker(registry=frozenset(agents or ["researcher", "finance"]))
    for name in (agents or ["researcher", "finance"]):
        tracker.start_step(name, role_description=f"Agent {name}")
        tracker.complete_step(name)
    return tracker


def _make_route_decision(**overrides):
    from python.helpers.router.routing_contract import (
        RouteDecision, RouteVerdict, AIActCategory,
    )
    rd = RouteDecision(verdict=RouteVerdict.PROCEED)
    rd.routing_strength = overrides.get("routing_strength", 0.85)
    if "ai_act_category" in overrides:
        rd.ai_act_category = overrides["ai_act_category"]
    else:
        rd.ai_act_category = AIActCategory.HIGH_RISK
    return rd


@dataclass
class FakeModelConfig:
    name: str = "gpt-4o"
    provider: str = "openai"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS : CONSTRUCTION PAR DEFAUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaults:
    def test_default_values_are_safe(self):
        meta = ReportMetadata()
        assert meta.session_id == ""
        assert meta.model_primary == "unknown"
        assert meta.agents_activated == []
        assert meta.confidence_score is None
        assert meta.processing_time_ms is None
        assert meta.ai_act_category == "unknown"
        assert meta.data_residency == "EU (OVH Cloud, Gravelines)"
        assert meta.evidence_version == "unknown"

    def test_default_is_json_serializable(self):
        meta = ReportMetadata()
        j = json.loads(meta.to_json())
        assert j["model_primary"] == "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS : FACTORY from_session
# ═══════════════════════════════════════════════════════════════════════════════

class TestFromSession:
    def test_all_sources(self):
        meta = ReportMetadata.from_session(
            envelope=_make_envelope(duration_ms=5000),
            tracker=_make_tracker(["researcher", "finance"]),
            route_decision=_make_route_decision(),
            model_config=FakeModelConfig(),
        )
        assert meta.session_id == "KRV-SES-TEST-001"
        assert meta.evidence_version == "v1.2.3"
        assert meta.processing_time_ms == 5000
        assert set(meta.agents_activated) == {"researcher", "finance"}
        assert meta.ai_act_category == "high_risk"
        assert meta.confidence_score == 0.85
        assert meta.model_primary == "openai/gpt-4o"

    def test_envelope_only(self):
        meta = ReportMetadata.from_session(envelope=_make_envelope())
        assert meta.session_id == "KRV-SES-TEST-001"
        assert meta.agents_activated == []
        assert meta.model_primary == "unknown"

    def test_tracker_only(self):
        meta = ReportMetadata.from_session(tracker=_make_tracker(["legal"]))
        assert meta.agents_activated == ["legal"]
        assert meta.session_id == ""

    def test_route_decision_only(self):
        meta = ReportMetadata.from_session(route_decision=_make_route_decision())
        assert meta.ai_act_category == "high_risk"
        assert meta.confidence_score == 0.85

    def test_model_config_only(self):
        meta = ReportMetadata.from_session(model_config=FakeModelConfig(name="claude-3", provider="anthropic"))
        assert meta.model_primary == "anthropic/claude-3"

    def test_model_config_no_provider(self):
        meta = ReportMetadata.from_session(model_config=FakeModelConfig(name="local-llama", provider=""))
        assert meta.model_primary == "local-llama"

    def test_all_none(self):
        meta = ReportMetadata.from_session()
        assert meta.session_id == ""
        assert meta.model_primary == "unknown"
        assert meta.ai_act_category == "unknown"

    def test_tracker_exception_is_swallowed(self):
        broken_tracker = MagicMock()
        broken_tracker.get_activated.side_effect = RuntimeError("boom")
        meta = ReportMetadata.from_session(tracker=broken_tracker)
        assert meta.agents_activated == []

    def test_route_decision_no_ai_act_category(self):
        from python.helpers.router.routing_contract import RouteDecision, RouteVerdict
        rd = RouteDecision(verdict=RouteVerdict.PROCEED)
        rd.ai_act_category = None
        meta = ReportMetadata.from_session(route_decision=rd)
        assert meta.ai_act_category == "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS : SERIALISATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_to_dict_all_keys(self):
        meta = ReportMetadata.from_session(
            envelope=_make_envelope(),
            model_config=FakeModelConfig(),
        )
        d = meta.to_dict()
        expected_keys = {
            "session_id", "model_primary", "agents_activated",
            "confidence_score", "processing_time_ms", "ai_act_category",
            "data_residency", "evidence_version",
        }
        assert set(d.keys()) == expected_keys

    def test_to_json_roundtrip(self):
        meta = ReportMetadata.from_session(
            envelope=_make_envelope(duration_ms=1234),
            tracker=_make_tracker(["researcher"]),
        )
        j = meta.to_json()
        parsed = json.loads(j)
        assert parsed["processing_time_ms"] == 1234
        assert parsed["agents_activated"] == ["researcher"]

    def test_to_markdown_block_structure(self):
        meta = ReportMetadata.from_session(
            envelope=_make_envelope(duration_ms=9876),
            tracker=_make_tracker(["researcher", "finance"]),
            route_decision=_make_route_decision(),
            model_config=FakeModelConfig(),
        )
        md = meta.to_markdown_block()
        assert "| PARAMETRE | VALEUR |" in md
        assert "|---|---|" in md
        assert "KRV-SES-TEST-001" in md
        assert "openai/gpt-4o" in md
        assert "researcher" in md
        assert "9,876 ms" in md
        assert "high_risk" in md
        assert "v1.2.3" in md

    def test_to_markdown_block_handles_unknowns(self):
        meta = ReportMetadata()
        md = meta.to_markdown_block()
        assert "unknown (non resolu)" in md
        assert "unknown" in md

    def test_to_markdown_block_no_agents(self):
        meta = ReportMetadata()
        md = meta.to_markdown_block()
        lines = md.split("\n")
        agent_line = [l for l in lines if "Agents actives" in l][0]
        assert "—" in agent_line
