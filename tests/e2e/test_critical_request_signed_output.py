"""
Test E2E — chaîne critique réelle : entrée → router → consensus → consensus_result
→ sortie signée → vérification (ADR-010).

Le seul élément simulé est l'appel LLM aux arbitres (CONSENSUS_SIMULATION=true en
développement). Le reste est RÉEL : criticality_router, le moteur PRISM
(run_consensus via ConsensusOrchestrator), la normalisation, la finalisation
fail-closed, et la signature HMAC.

Le test échoue si :
  - le consensus_result n'est pas peuplé,
  - la sortie n'est pas signée,
  - la signature ne se vérifie pas,
  - une altération du payload ne casse pas la signature,
  - une sortie critique sans consensus n'est pas bloquée (fail-closed).
"""

import os

import pytest

# Environnement déterministe : dev + simulation + secret HMAC présent.
os.environ.setdefault("EVIDENCE_ENV", "development")
os.environ.setdefault("CONSENSUS_SIMULATION", "true")
os.environ.setdefault("EVIDENCE_HMAC_KEY", "e2e-test-hmac-key-bbbbbbbbbbbbbbbbbbbbbbbb")

CRITICAL_QUERY = (
    "Peux-tu approuver et publier la recommandation juridique finale et définitive "
    "sur la responsabilité du transporteur ?"
)


@pytest.mark.asyncio
async def test_critical_request_to_signed_output_full_chain(monkeypatch):
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    monkeypatch.setenv("CONSENSUS_SIMULATION", "true")
    monkeypatch.setenv("EVIDENCE_HMAC_KEY", "e2e-test-hmac-key-bbbbbbbbbbbbbbbbbbbbbbbb")

    from python.helpers.criticality_router import get_criticality_router
    from python.helpers.consensus_arbiter import (
        ConsensusOrchestrator,
        load_consensus_config,
        reset_consensus_orchestrator,
    )
    from python.helpers.consensus_manager import DecisionType
    from python.helpers.critical_output import (
        CriticalOutputDecision,
        finalize_critical_output,
        verify_evidence_signature,
    )

    # 1) ROUTER — la requête critique est classée requires_consensus=True
    assessment = get_criticality_router().assess(query=CRITICAL_QUERY, agent_profile="legal")
    assert assessment.requires_consensus is True, "Le router doit exiger un consensus"

    # 2) CONSENSUS — moteur PRISM réel (arbitres simulés)
    reset_consensus_orchestrator()
    config = load_consensus_config()
    assert config.simulation_enabled, "La simulation doit être active en développement"
    orchestrator = ConsensusOrchestrator(config)

    consensus_result = await orchestrator.seek_consensus(
        action=CRITICAL_QUERY,
        context={"description": "E2E critical request — chemin opposable"},
        decision_type=DecisionType.CRITICAL,
        correlation_id="e2e-critical-001",
    )

    # 3) consensus_result PEUPLÉ et exploitable
    assert consensus_result is not None
    assert consensus_result.approved is True
    assert consensus_result.status.value == "APPROVED"

    # 4) FINALISATION — sortie signée alimentée par le consensus_result réel
    output_text = "Le transporteur exécutant peut réclamer le paiement direct (L.132-8)."
    result = finalize_critical_output(
        output_text=output_text,
        requires_consensus=assessment.requires_consensus,
        criticality_level="LEVEL_3",
        consensus_result=consensus_result,
        input_text=CRITICAL_QUERY,
        trace_id="e2e-critical-001",
        model="openrouter/anthropic/claude-opus-4.8",
        human_review_required=False,
    )

    assert result.decision == CriticalOutputDecision.EMIT_SIGNED
    assert result.can_emit is True

    signed = result.signed_output
    assert signed is not None

    # 5) la sortie finale contient bien le consensus_result et une signature
    assert signed["consensus_result"] is not None
    assert signed["consensus_result"]["status"] in ("APPROVED",)
    assert signed["signature"]["value"].startswith(("hmac-sha256:", "rsa-pss-sha256:"))
    assert signed["signature_version"] == "2"
    assert signed["audit_metadata"]["consensus_result_hash"] is not None

    # 6) la signature est vérifiable
    assert verify_evidence_signature(signed) is True

    # 7) une altération du payload invalide la signature
    tampered = dict(signed)
    tampered["output"] = output_text + " [INJECTION]"
    assert verify_evidence_signature(tampered) is False


@pytest.mark.asyncio
async def test_critical_request_without_consensus_is_fail_closed(monkeypatch):
    """Même requête critique mais SANS consensus_result → la sortie doit être bloquée."""
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    monkeypatch.setenv("EVIDENCE_HMAC_KEY", "e2e-test-hmac-key-bbbbbbbbbbbbbbbbbbbbbbbb")

    from python.helpers.criticality_router import get_criticality_router
    from python.helpers.critical_output import (
        CriticalOutputDecision,
        finalize_critical_output,
    )

    assessment = get_criticality_router().assess(query=CRITICAL_QUERY, agent_profile="legal")
    assert assessment.requires_consensus is True

    result = finalize_critical_output(
        output_text="Réponse critique émise sans consensus.",
        requires_consensus=assessment.requires_consensus,
        criticality_level="LEVEL_3",
        consensus_result=None,
        input_text=CRITICAL_QUERY,
    )

    assert result.decision == CriticalOutputDecision.FAIL_CLOSED
    assert result.can_emit is False
    assert result.signed_output is None
