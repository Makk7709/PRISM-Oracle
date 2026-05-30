"""
Tests P1-1 — signature v2 du chemin pipeline legal (ADR-010).

Couvre :
  - le mapping `LegalOutput.consensus_status` → (consensus_result, requires_consensus) ;
  - la finalisation du short-circuit pipeline (`finalize_pipeline_short_circuit`),
    qui est EXACTEMENT la fonction appelée par agent.py au point d'émission ;
  - signature présente + vérifiable, anti-tamper, fail-closed si secret absent en prod.

Déterministe : aucun LLM, aucun pipeline réel. On simule le contexte de signature
tel que l'extension legal_safe le pose sur l'agent.
"""

import types

import pytest

from python.helpers.critical_output import (
    CriticalOutputDecision,
    finalize_pipeline_short_circuit,
    verify_evidence_signature,
)
from python.helpers.legal_signing import map_legal_consensus

HMAC_KEY = "legal-p1-test-key-cccccccccccccccccccccccc"


@pytest.fixture
def hmac_env(monkeypatch):
    monkeypatch.setenv("EVIDENCE_HMAC_KEY", HMAC_KEY)
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    for var in ("EVIDENCE_RSA_PRIVATE_KEY", "EVIDENCE_RSA_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(var, raising=False)
    yield


class _FakeAgent:
    """Agent minimal dupliquant l'API lue par finalize_pipeline_short_circuit."""

    def __init__(self, data=None, query="Question juridique critique ?"):
        self._data = dict(data or {})
        self.config = types.SimpleNamespace(
            chat_model=types.SimpleNamespace(name="claude-opus-4.8", provider="openrouter")
        )
        self.last_user_message = types.SimpleNamespace(output_text=lambda: query)

    def get_data(self, k):
        return self._data.get(k)

    def set_data(self, k, v):
        self._data[k] = v


def _legal_context(consensus_status, *, fail_soft=True):
    """Reproduit ce que pose l'extension legal_safe sur l'agent."""
    cr, req = map_legal_consensus(consensus_status, "cid-1", "corr-legal-1")
    return {
        "_pipeline_final_response": "## Analyse juridique\nPosition validée.",
        "_consensus_result": cr,
        "_pipeline_requires_consensus": req,
        "_pipeline_criticality_level": "LEVEL_3" if req else "LEVEL_2",
        "_output_policy": {"policy_id": "legal-pipeline", "policy_version": "validated_position",
                            "fail_soft_allowed": fail_soft},
        "_legal_safe_correlation_id": "corr-legal-1",
    }


# ── Mapping consensus_status ──
@pytest.mark.parametrize("status,exp_req,exp_app", [
    ("APPROVED", True, True),
    ("REJECTED", True, False),
    ("NO_CONSENSUS", True, False),
    ("INFRA_FAILURE", True, False),
    (None, False, None),
    ("", False, None),
])
def test_map_legal_consensus(status, exp_req, exp_app):
    cr, req = map_legal_consensus(status, "cid", "corr")
    assert req is exp_req
    if exp_app is None:
        assert cr is None
    else:
        assert cr["approved"] is exp_app
        assert cr["status"] == status


# ── Legal APPROVED → sortie signée opposable ──
def test_legal_approved_emits_signed(hmac_env):
    agent = _FakeAgent(_legal_context("APPROVED"))
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.EMIT_SIGNED
    assert r.can_emit is True
    assert r.signed_output["consensus_result"]["status"] == "APPROVED"
    assert r.signed_output["signature"]["version"] == "2"
    assert verify_evidence_signature(r.signed_output) is True


# ── Legal REJECTED + policy fail-soft explicite → bannière + signé (pas de blocage) ──
def test_legal_rejected_fail_soft_banner(hmac_env):
    agent = _FakeAgent(_legal_context("REJECTED", fail_soft=True))
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.FAIL_SOFT_BANNER
    assert r.can_emit is True
    assert "NON VALIDÉE" in r.output_text
    assert verify_evidence_signature(r.signed_output) is True


# ── Legal REJECTED SANS policy fail-soft → fail-closed ──
def test_legal_rejected_without_failsoft_blocks(hmac_env):
    ctx = _legal_context("REJECTED", fail_soft=False)
    agent = _FakeAgent(ctx)
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED
    assert r.can_emit is False


# ── Legal sans consensus (INFO/low-risk) → signé non critique, pas de bannière ──
def test_legal_no_consensus_noncritical_signed(hmac_env):
    agent = _FakeAgent(_legal_context(None))
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.EMIT_NONCRITICAL_SIGNED
    assert r.can_emit is True
    assert verify_evidence_signature(r.signed_output) is True
    assert "NON VALIDÉE" not in r.output_text


# ── Anti-tamper sur sortie legal signée ──
def test_legal_signed_output_tamper_detected(hmac_env):
    agent = _FakeAgent(_legal_context("APPROVED"))
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert verify_evidence_signature(r.signed_output) is True
    tampered = dict(r.signed_output)
    tampered["output"] = "Position juridique falsifiée."
    assert verify_evidence_signature(tampered) is False


# ── Secret absent en production sur sortie legal critique → fail-closed (D6) ──
def test_legal_no_secret_production_fail_closed(monkeypatch):
    monkeypatch.delenv("EVIDENCE_HMAC_KEY", raising=False)
    monkeypatch.setenv("EVIDENCE_ENV", "production")
    for var in ("EVIDENCE_RSA_PRIVATE_KEY", "EVIDENCE_RSA_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(var, raising=False)
    agent = _FakeAgent(_legal_context("APPROVED"))
    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED
    assert r.can_emit is False


# ── E2E : contrat writer/reader via la VRAIE méthode d'extension ──
# Verrouille que `_set_signing_context` (écrit par l'extension legal_safe) et
# `finalize_pipeline_short_circuit` (lu par agent.py) partagent les mêmes clés.
def test_legal_extension_set_signing_context_e2e(monkeypatch):
    monkeypatch.setenv("EVIDENCE_HMAC_KEY", HMAC_KEY)
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    monkeypatch.setenv("CONSENSUS_SIMULATION", "true")
    try:
        from python.extensions.legal_safe_mode._10_legal_safe_integration import (
            LegalSafeModeExtension,
        )
    except Exception as exc:  # pragma: no cover - deps optionnelles absentes
        pytest.skip(f"legal_safe extension import indisponible: {exc}")

    agent = _FakeAgent(query="Peut-on résilier ce contrat ?")
    agent.set_data("_legal_safe_correlation_id", "corr-e2e-1")
    agent.set_data("_pipeline_final_response", "## Position juridique validée\nOK.")

    ext = LegalSafeModeExtension(agent=None)
    cr, req = map_legal_consensus("APPROVED", "cid-e2e", "corr-e2e-1")
    ext._set_signing_context(
        agent, requires_consensus=req, consensus_result=cr,
        policy_id="legal-pipeline", policy_version="validated_position", human_review=True,
    )

    r = finalize_pipeline_short_circuit(agent, agent.get_data("_pipeline_final_response"))
    assert r.decision == CriticalOutputDecision.EMIT_SIGNED
    assert r.can_emit is True
    assert verify_evidence_signature(r.signed_output) is True
    # anti-tamper sur la chaîne réelle
    tampered = dict(r.signed_output)
    tampered["output"] = "Réponse modifiée."
    assert verify_evidence_signature(tampered) is False
