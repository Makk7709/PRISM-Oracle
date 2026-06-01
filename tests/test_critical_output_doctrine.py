"""
Tests unitaires de la doctrine de sortie critique (ADR-010).

Couvre les 9 cas exigés par la mission de réalignement du chemin critique :
router → consensus → consensus_result → sortie signée, fail-closed par défaut.

Déterministes : aucun appel LLM réel. Le consensus_result est fourni en dur
sous forme de dict normalisé (comme produit par run_consensus/seek_consensus).
"""

import pytest

from python.helpers.critical_output import (
    CriticalOutputDecision,
    OutputPolicy,
    finalize_critical_output,
    is_consensus_valid,
    normalize_consensus_result,
    sign_evidence_output,
    verify_evidence_signature,
)

HMAC_KEY = "unit-test-hmac-key-aaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture
def hmac_env(monkeypatch):
    monkeypatch.setenv("EVIDENCE_HMAC_KEY", HMAC_KEY)
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    # neutralise toute clé RSA résiduelle pour forcer le chemin HMAC déterministe
    for var in ("EVIDENCE_RSA_PRIVATE_KEY", "EVIDENCE_RSA_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(var, raising=False)
    yield


def _approved(**over):
    base = {"status": "APPROVED", "approved": True, "proposal_id": "p1", "correlation_id": "c1"}
    base.update(over)
    return base


# ── Cas 1 : le router classe une requête critique → requires_consensus=True ──
def test_router_returns_requires_consensus_true():
    from python.helpers.criticality_router import get_criticality_router

    # "approuver" et "publier" sont des CRITICAL_ACTION_PATTERNS → LEVEL 3.
    assessment = get_criticality_router().assess(
        query="Peux-tu approuver et publier la recommandation finale et définitive ?",
        agent_profile="legal",
    )
    assert assessment.requires_consensus is True

    # Contrôle négatif : une question d'information simple ne déclenche pas le consensus.
    benign = get_criticality_router().assess(query="Quelle est la capitale de la France ?")
    assert benign.requires_consensus is False


# ── Cas 2 : consensus_result valide peuplé → sortie signée ──
def test_valid_consensus_emits_signed(hmac_env):
    r = finalize_critical_output(
        output_text="Conclusion validée.",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result=_approved(),
        input_text="question critique",
    )
    assert r.decision == CriticalOutputDecision.EMIT_SIGNED
    assert r.can_emit is True
    assert r.signed_output is not None
    assert r.signed_output["consensus_result"]["status"] == "APPROVED"
    assert verify_evidence_signature(r.signed_output) is True


# ── Cas 3 : absence de consensus_result alors que requis → fail-closed ──
def test_missing_consensus_fail_closed(hmac_env):
    r = finalize_critical_output(
        output_text="X",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result=None,
    )
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED
    assert r.can_emit is False
    assert r.signed_output is None


# ── Cas 4 : consensus_result invalide (REJECTED / NO_CONSENSUS) → fail-closed ──
@pytest.mark.parametrize("status", ["REJECTED", "NO_CONSENSUS", "INFRA_FAILURE", "SKIPPED"])
def test_invalid_consensus_fail_closed(hmac_env, status):
    r = finalize_critical_output(
        output_text="X",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result={"status": status, "approved": False},
    )
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED
    assert r.can_emit is False


def test_approved_but_not_approved_flag_is_invalid(hmac_env):
    # status APPROVED mais approved=False = incohérent → invalide (pas de maquillage)
    r = finalize_critical_output(
        output_text="X",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result={"status": "APPROVED", "approved": False},
    )
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED


# ── Cas 5 : fail-soft autorisé UNIQUEMENT par policy explicite ──
def test_fail_soft_requires_explicit_policy(hmac_env):
    # sans policy → fail-closed
    blocked = finalize_critical_output(
        output_text="X", requires_consensus=True, criticality_level="LEVEL_3",
        consensus_result=None,
    )
    assert blocked.decision == CriticalOutputDecision.FAIL_CLOSED

    # avec policy explicite → bannière (fail-soft) + signé
    soft = finalize_critical_output(
        output_text="X", requires_consensus=True, criticality_level="LEVEL_3",
        consensus_result=None, policy=OutputPolicy(fail_soft_allowed=True),
    )
    assert soft.decision == CriticalOutputDecision.FAIL_SOFT_BANNER
    assert soft.can_emit is True
    assert "NON VALIDÉE" in soft.output_text
    assert verify_evidence_signature(soft.signed_output) is True


# ── Cas 6 : signature générée avec secret valide ──
def test_signature_generated_with_secret(hmac_env):
    sig = sign_evidence_output(
        output_text="out", input_text="in", consensus_view=normalize_consensus_result(_approved()),
        criticality_level="LEVEL_3", policy=OutputPolicy(), timestamp="2026-01-01T00:00:00+00:00",
        trace_id="t1", model="openrouter/anthropic/claude-opus-4.8", human_review_required=True,
    )
    assert sig["value"].startswith(("hmac-sha256:", "rsa-pss-sha256:"))
    assert sig["version"] == "2"
    # les 9 champs doctrinaux sont couverts
    covered = sig["covered_fields"]
    for f in ("input_hash", "output_hash", "consensus_result_hash", "criticality_level",
              "policy_id", "policy_version", "timestamp", "trace_id", "model",
              "human_review_required"):
        assert f in covered


# ── Cas 7 : signature refusée si le payload est modifié ──
def test_signature_rejected_on_tamper(hmac_env):
    r = finalize_critical_output(
        output_text="Réponse authentique.", requires_consensus=True,
        criticality_level="LEVEL_3", consensus_result=_approved(), input_text="q",
    )
    assert verify_evidence_signature(r.signed_output) is True

    # tamper output
    tampered = dict(r.signed_output)
    tampered["output"] = "Réponse falsifiée."
    assert verify_evidence_signature(tampered) is False

    # tamper consensus_result
    tampered2 = dict(r.signed_output)
    tampered2["consensus_result"] = {"status": "APPROVED", "approved": True, "proposal_id": "HACK"}
    assert verify_evidence_signature(tampered2) is False


# ── Cas 8 : absence de secret HMAC en production → fail-closed ──
def test_no_secret_in_production_fail_closed(monkeypatch):
    monkeypatch.delenv("EVIDENCE_HMAC_KEY", raising=False)
    monkeypatch.setenv("EVIDENCE_ENV", "production")
    for var in ("EVIDENCE_RSA_PRIVATE_KEY", "EVIDENCE_RSA_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(var, raising=False)

    r = finalize_critical_output(
        output_text="X", requires_consensus=True, criticality_level="LEVEL_3",
        consensus_result=_approved(),
    )
    assert r.decision == CriticalOutputDecision.FAIL_CLOSED
    assert r.can_emit is False


def test_no_secret_dev_noncritical_degraded(monkeypatch):
    monkeypatch.delenv("EVIDENCE_HMAC_KEY", raising=False)
    monkeypatch.setenv("EVIDENCE_ENV", "development")
    for var in ("EVIDENCE_RSA_PRIVATE_KEY", "EVIDENCE_RSA_PRIVATE_KEY_PATH"):
        monkeypatch.delenv(var, raising=False)

    r = finalize_critical_output(
        output_text="info", requires_consensus=False, criticality_level="LEVEL_1",
    )
    assert r.decision == CriticalOutputDecision.EMIT_UNSIGNED_DEGRADED
    assert r.can_emit is True


# ── Cas 9 : consensus non requis → sortie possible MAIS signée ──
def test_non_critical_output_is_signed(hmac_env):
    r = finalize_critical_output(
        output_text="Bonjour, voici l'info.", requires_consensus=False,
        criticality_level="LEVEL_1", consensus_result=None, input_text="salut",
    )
    assert r.decision == CriticalOutputDecision.EMIT_NONCRITICAL_SIGNED
    assert r.can_emit is True
    assert r.signed_output is not None
    assert verify_evidence_signature(r.signed_output) is True


# ── Normalisation : ne maquille jamais un résultat vide en succès ──
def test_empty_consensus_not_faked_success():
    assert normalize_consensus_result(None) is None
    assert normalize_consensus_result({}) is None
    assert is_consensus_valid(None) is False


# ═══════════════════════════════════════════════════════════════════════════════
# DOCTRINE DE FRAÎCHEUR (recency) — sortie critique non vérifiée → escalade
# ═══════════════════════════════════════════════════════════════════════════════

def test_critical_recency_unverified_escalates_and_banners(hmac_env):
    # Sortie critique APPROUVÉE mais fraîcheur NON prouvée (défaut None).
    r = finalize_critical_output(
        output_text="Le taux applicable est de 25 %.",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result=_approved(),
        input_text="quel est le taux en vigueur ?",
        # recency_verified non fourni → None → non prouvé
    )
    assert r.decision == CriticalOutputDecision.EMIT_SIGNED
    assert r.can_emit is True
    assert r.reason == "recency_unverified"
    # bannière d'obsolescence apposée
    assert "potentiellement obsolète" in r.output_text
    # escalade revue humaine (champ signé)
    assert r.signed_output["audit_metadata"]["human_review_required"] is True
    assert r.signed_output["recency"]["recency_review_required"] is True
    assert r.signed_output["recency"]["recency_verified"] is None
    # signature cohérente avec le texte bannerisé
    assert verify_evidence_signature(r.signed_output) is True


def test_critical_recency_verified_no_banner_no_escalation(hmac_env):
    # Fraîcheur prouvée en amont → pas de bannière, pas d'escalade forcée.
    r = finalize_critical_output(
        output_text="Le taux applicable est de 25 % (source officielle 2026-05-30).",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result=_approved(),
        input_text="quel est le taux en vigueur ?",
        human_review_required=False,
        recency_verified=True,
    )
    assert r.decision == CriticalOutputDecision.EMIT_SIGNED
    assert r.reason == "ok"
    assert "potentiellement obsolète" not in r.output_text
    assert r.signed_output["audit_metadata"]["human_review_required"] is False
    assert r.signed_output["recency"]["recency_verified"] is True
    assert r.signed_output["recency"]["recency_review_required"] is False
    assert verify_evidence_signature(r.signed_output) is True


def test_recency_banner_is_tamper_evident(hmac_env):
    # Retirer la bannière d'obsolescence d'une sortie critique doit casser la signature.
    r = finalize_critical_output(
        output_text="Conclusion critique.",
        requires_consensus=True,
        criticality_level="LEVEL_3",
        consensus_result=_approved(),
        input_text="q",
    )
    assert verify_evidence_signature(r.signed_output) is True
    tampered = dict(r.signed_output)
    tampered["output"] = "Conclusion critique."  # bannière retirée
    assert verify_evidence_signature(tampered) is False


def test_noncritical_output_unaffected_by_recency(hmac_env):
    # Hors chemin critique : pas d'escalade ni de bannière de fraîcheur.
    r = finalize_critical_output(
        output_text="Bonjour, voici l'info.",
        requires_consensus=False,
        criticality_level="LEVEL_1",
        input_text="salut",
    )
    assert r.decision == CriticalOutputDecision.EMIT_NONCRITICAL_SIGNED
    assert "potentiellement obsolète" not in r.output_text
    assert r.signed_output["recency"]["recency_review_required"] is False
