"""
Observability log schema tests.
"""

import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.criticality_router import CriticalityRouter
from python.consensus.engine import ConsensusEngine


def _find_event(records, event_name: str):
    for record in records:
        try:
            payload = json.loads(record.message)
        except Exception:
            continue
        if payload.get("event") == event_name:
            return payload
    return None


def test_router_decision_log_has_correlation_id(caplog):
    caplog.set_level("INFO")
    router = CriticalityRouter(is_production=False)
    router.assess(query="What is a contract?", agent_profile="default")
    payload = _find_event(caplog.records, "router_decision")
    assert payload is not None
    assert payload.get("correlation_id")


# NOTE (Phase 9 cleanup) : le test du wrapper `ConsensusMCPWrapper.collect` a été
# supprimé avec le module orphelin `consensus_mcp_integration`. La présence du
# correlation_id sur le chemin canonique reste couverte par les deux tests
# router/engine de ce fichier.


@pytest.mark.asyncio
async def test_engine_logs_have_correlation_id(caplog, monkeypatch):
    caplog.set_level("INFO")
    engine = ConsensusEngine()
    monkeypatch.setattr(engine, "_select_arbiters", lambda: [])
    await engine.run_consensus(
        evidence_pack=None,
        policy={"action": "test", "context": {}, "correlation_id": "corr-2"},
    )
    router_payload = _find_event(caplog.records, "router_to_engine")
    tally_payload = _find_event(caplog.records, "consensus_tally")
    assert router_payload is not None
    assert tally_payload is not None
    assert router_payload.get("correlation_id") == "corr-2"
    assert tally_payload.get("correlation_id") == "corr-2"
