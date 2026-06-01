"""
Couche de finalisation de sortie critique Evidence — CONSOLIDÉE (ADR-010).

Point de passage UNIQUE qui, pour une sortie d'agent :

  1. décide fail-closed / fail-soft / émission signée selon la doctrine ADR-010,
     à partir de (criticality_level, requires_consensus, consensus_result, policy) ;
  2. appose une signature vérifiable couvrant les 9 champs exigés par la doctrine
     (input_hash, output_hash, consensus_result_hash, criticality_level,
      policy_id/version, timestamp, trace_id, model/provider, human_review_required) ;
  3. fail-close en production si le secret de signature est absent.

Cette couche NE crée PAS de nouvelle primitive cryptographique : elle réutilise
`python.helpers.integrity_block` (HMAC-SHA256 / RSA-PSS-SHA256 via log_signer) et
`criticality_router` (source unique de `requires_consensus`). Cf. ADR-010 §D7/D8.

Aucun fallback silencieux. Aucun secret en dur. Typage strict.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from python.helpers.integrity_block import (
    compute_hmac_sha256,
    compute_sha256,
    _get_hmac_key,
    _get_hmac_key_id,
    _try_rsa_sign,
    _try_rsa_verify,
)

logger = logging.getLogger("critical_output")

SIGNATURE_VERSION = "2"

# Statuts de consensus considérés VALIDES pour émettre une sortie critique non bloquée.
# Doctrine ADR-010 D2/D3 : seul APPROVED autorise l'émission directe ; tout autre
# statut terminal (REJECTED / NO_CONSENSUS / INFRA_FAILURE / SKIPPED) ou l'absence
# déclenche fail-closed (sauf policy fail-soft explicite).
_VALID_CONSENSUS_STATUS = {"APPROVED"}


def _is_production() -> bool:
    return os.environ.get("EVIDENCE_ENV", "production").lower() == "production"


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRATS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OutputPolicy:
    """Policy de finalisation. fail_soft_allowed doit être EXPLICITE (ADR-010 D4)."""
    policy_id: str = "evidence-default"
    policy_version: str = "1"
    fail_soft_allowed: bool = False  # défaut: fail-closed

    @classmethod
    def from_env_or_data(cls, raw: Optional[Dict[str, Any]] = None) -> "OutputPolicy":
        """Construit une policy depuis un dict explicite (jamais implicite)."""
        if not raw:
            return cls()
        return cls(
            policy_id=str(raw.get("policy_id", "evidence-default")),
            policy_version=str(raw.get("policy_version", "1")),
            fail_soft_allowed=bool(raw.get("fail_soft_allowed", False)),
        )


@dataclass(frozen=True)
class ConsensusResultView:
    """Vue normalisée, lecture seule, d'un résultat de consensus hétérogène."""
    status: str
    approved: bool
    proposal_id: Optional[str] = None
    correlation_id: Optional[str] = None
    decision_time_ms: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def canonical(self) -> Dict[str, Any]:
        """Représentation canonique stable pour le hash de consensus."""
        return {
            "status": self.status,
            "approved": self.approved,
            "proposal_id": self.proposal_id,
            "correlation_id": self.correlation_id,
            "decision_time_ms": self.decision_time_ms,
        }


class CriticalOutputDecision(str, Enum):
    EMIT_SIGNED = "EMIT_SIGNED"                       # critique, consensus valide, signé
    EMIT_NONCRITICAL_SIGNED = "EMIT_NONCRITICAL_SIGNED"  # non critique, signé
    FAIL_CLOSED = "FAIL_CLOSED"                       # bloqué (doctrine)
    FAIL_SOFT_BANNER = "FAIL_SOFT_BANNER"             # émis avec bannière (policy explicite)
    EMIT_UNSIGNED_DEGRADED = "EMIT_UNSIGNED_DEGRADED" # hors critique + secret absent (toléré)


@dataclass
class CriticalOutputResult:
    decision: CriticalOutputDecision
    can_emit: bool
    output_text: str
    reason: str
    signed_output: Optional[Dict[str, Any]] = None
    correlation_id: str = ""

    @property
    def blocked(self) -> bool:
        return not self.can_emit


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALISATION CONSENSUS
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_consensus_result(obj: Any) -> Optional[ConsensusResultView]:
    """Normalise un consensus_result (dict, ConsensusDecision, ConsensusResult) en vue.

    Retourne None si l'objet est absent ou ne porte aucun statut exploitable.
    Ne maquille JAMAIS un résultat vide en succès (ADR-010 interdictions).
    """
    if obj is None:
        return None

    # dataclass / objet avec attributs
    if hasattr(obj, "status") and not isinstance(obj, dict):
        status = getattr(obj, "status")
        status_str = status.value if hasattr(status, "value") else str(status)
        return ConsensusResultView(
            status=status_str,
            approved=bool(getattr(obj, "approved", False)),
            proposal_id=getattr(obj, "proposal_id", None),
            correlation_id=getattr(obj, "correlation_id", None),
            decision_time_ms=getattr(obj, "decision_time_ms", None),
            raw={"type": type(obj).__name__},
        )

    if isinstance(obj, dict):
        status = obj.get("status")
        if status is None and "approved" not in obj:
            # dict sans aucune information de décision → non exploitable
            return None
        status_str = (status.value if hasattr(status, "value") else str(status)) if status is not None else ""
        return ConsensusResultView(
            status=status_str,
            approved=bool(obj.get("approved", False)),
            proposal_id=obj.get("proposal_id"),
            correlation_id=obj.get("correlation_id"),
            decision_time_ms=obj.get("decision_time_ms"),
            raw={k: v for k, v in obj.items() if k not in {"votes"}},
        )

    return None


def is_consensus_valid(view: Optional[ConsensusResultView]) -> bool:
    """Un consensus est VALIDE (autorise l'émission directe) ssi APPROVED + approved=True."""
    if view is None:
        return False
    if view.status.upper() not in _VALID_CONSENSUS_STATUS:
        return False
    return view.approved is True


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNATURE (9 CHAMPS) — réutilise integrity_block
# ═══════════════════════════════════════════════════════════════════════════════

def _consensus_result_hash(view: Optional[ConsensusResultView]) -> Optional[str]:
    if view is None:
        return None
    canonical = json.dumps(view.canonical(), sort_keys=True, ensure_ascii=False)
    return compute_sha256(canonical)


def _build_signature_payload(fields: Dict[str, Optional[str]]) -> str:
    """Chaîne canonique signée. Ordre FIXE — toute dérive casse la vérification."""
    order = [
        "signature_version",
        "input_hash",
        "output_hash",
        "consensus_result_hash",
        "criticality_level",
        "policy_id",
        "policy_version",
        "timestamp",
        "trace_id",
        "model",
        "human_review_required",
    ]
    return "\n".join(f"{k}={fields.get(k) or 'null'}" for k in order)


def sign_evidence_output(
    *,
    output_text: str,
    input_text: Optional[str],
    consensus_view: Optional[ConsensusResultView],
    criticality_level: str,
    policy: OutputPolicy,
    timestamp: str,
    trace_id: str,
    model: Optional[str] = None,
    human_review_required: Optional[bool] = None,
) -> Dict[str, Any]:
    """Signe une sortie Evidence sur les 9 champs doctrinaux.

    Lève RuntimeError si aucun secret de signature n'est disponible (HMAC absent
    ET RSA indisponible). Le caller décide alors du fail-closed (ADR-010 D6).
    """
    input_hash = compute_sha256(input_text)
    output_hash = compute_sha256(output_text)
    cr_hash = _consensus_result_hash(consensus_view)

    fields: Dict[str, Optional[str]] = {
        "signature_version": SIGNATURE_VERSION,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "consensus_result_hash": cr_hash,
        "criticality_level": criticality_level,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "timestamp": timestamp,
        "trace_id": trace_id,
        "model": model,
        "human_review_required": (
            None if human_review_required is None else str(bool(human_review_required)).lower()
        ),
    }
    payload = _build_signature_payload(fields)

    rsa_result = _try_rsa_sign(payload)
    if rsa_result is not None:
        sig_b64, key_id, _algo = rsa_result
        signature_value = f"rsa-pss-sha256:{sig_b64}"
        method = "RSA-PSS-SHA256 (non-repudiation)"
        signature_key_id = key_id
    else:
        # peut lever RuntimeError si EVIDENCE_HMAC_KEY absent → fail-closed côté caller
        signature_value = compute_hmac_sha256(payload, _get_hmac_key())
        method = "HMAC-SHA256 (integrity)"
        signature_key_id = _get_hmac_key_id()

    return {
        "value": signature_value,
        "version": SIGNATURE_VERSION,
        "method": method,
        "key_id": signature_key_id,
        "signed_at": timestamp,
        "covered_fields": {k: v for k, v in fields.items()},
    }


def verify_evidence_signature(signed_output: Dict[str, Any]) -> bool:
    """Vérifie une sortie signée. Reproductible : recalcule les hashes depuis le
    contenu présent dans `signed_output` et revalide la signature.

    Toute altération de `output`, du `consensus_result`, de la criticité, de la
    policy, du trace_id ou du timestamp invalide la signature.
    """
    try:
        signature = signed_output.get("signature") or {}
        sig_value = signature.get("value")
        signed_at = signature.get("signed_at")
        if not sig_value or not signed_at:
            return False

        consensus_view = normalize_consensus_result(signed_output.get("consensus_result"))
        assessment = signed_output.get("criticality_assessment") or {}
        meta = signed_output.get("audit_metadata") or {}
        policy = signed_output.get("policy") or {}

        fields: Dict[str, Optional[str]] = {
            "signature_version": signature.get("version", SIGNATURE_VERSION),
            "input_hash": meta.get("input_hash"),
            "output_hash": compute_sha256(signed_output.get("output")),
            "consensus_result_hash": _consensus_result_hash(consensus_view),
            "criticality_level": assessment.get("criticality_level"),
            "policy_id": policy.get("policy_id"),
            "policy_version": policy.get("policy_version"),
            "timestamp": signed_at,
            "trace_id": meta.get("trace_id"),
            "model": meta.get("model"),
            "human_review_required": (
                None if meta.get("human_review_required") is None
                else str(bool(meta.get("human_review_required"))).lower()
            ),
        }
        payload = _build_signature_payload(fields)

        if sig_value.startswith("rsa-pss-sha256:"):
            return _try_rsa_verify(payload, sig_value[len("rsa-pss-sha256:"):], signature.get("key_id", ""))
        if sig_value.startswith("hmac-sha256:"):
            import hmac as _hmac
            expected = compute_hmac_sha256(payload, _get_hmac_key())
            return _hmac.compare_digest(sig_value, expected)
        return False
    except Exception as exc:  # vérification = jamais de crash, échec = False
        logger.warning("verify_evidence_signature failed: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FINALISATION — GATE CONSOLIDÉ
# ═══════════════════════════════════════════════════════════════════════════════

def _fail_closed_notice(reason: str, correlation_id: str) -> str:
    return (
        "⛔ **Sortie critique bloquée (fail-closed).**\n\n"
        f"Motif : {reason}\n\n"
        "Conformément à la doctrine Evidence (ADR-010), une réponse critique ne peut être "
        "émise sans consensus validé et/ou signature vérifiable. "
        f"`correlation_id={correlation_id}`"
    )


def _fail_soft_banner(reason: str, correlation_id: str) -> str:
    return (
        "\n\n---\n"
        "⚠️ **Réponse NON VALIDÉE par consensus** (fail-soft autorisé par policy).\n"
        f"Motif : {reason}. Cette réponse n'est pas opposable au sens Evidence. "
        f"`correlation_id={correlation_id}`"
    )


def _recency_banner(as_of: str, correlation_id: str) -> str:
    """Bannière de fraîcheur non vérifiée (doctrine de fraîcheur stricte).

    Apposée par le gate quand une sortie critique n'a pas prouvé l'usage de
    données à jour. La sortie reste émise (signée) mais est escaladée en revue
    humaine et explicitement marquée comme potentiellement obsolète.
    """
    return (
        "\n\n---\n"
        "⚠️ **Fraîcheur des données non vérifiée automatiquement.** "
        f"Cette sortie critique n'a pas prouvé l'usage de données à jour (as-of {as_of}) "
        "via des outils de récupération : réponse potentiellement obsolète, "
        "revue humaine requise avant usage opposable. "
        f"`correlation_id={correlation_id}`"
    )


def finalize_critical_output(
    *,
    output_text: str,
    requires_consensus: bool,
    criticality_level: str,
    consensus_result: Any = None,
    policy: Optional[OutputPolicy] = None,
    input_text: Optional[str] = None,
    trace_id: Optional[str] = None,
    model: Optional[str] = None,
    human_review_required: Optional[bool] = None,
    is_production: Optional[bool] = None,
    recency_verified: Optional[bool] = None,
) -> CriticalOutputResult:
    """Applique la doctrine ADR-010 et produit une sortie (signée ou bloquée).

    Voir la matrice de comportement de l'ADR-010.

    `recency_verified` (doctrine de fraîcheur stricte) : indique si la fraîcheur
    des données a été affirmativement prouvée en amont. Sur une sortie critique,
    une fraîcheur NON prouvée (None ou False) force `human_review_required=True`
    et appose une bannière « potentiellement obsolète » (escalade, jamais
    blocage silencieux).
    """
    policy = policy or OutputPolicy()
    if is_production is None:
        is_production = _is_production()
    correlation_id = trace_id or str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    view = normalize_consensus_result(consensus_result)
    is_critical = bool(requires_consensus)

    # ── Doctrine de fraîcheur : sortie critique sans fraîcheur prouvée → escalade ──
    recency_unverified = is_critical and (recency_verified is not True)
    if recency_unverified:
        human_review_required = True

    # ── D2/D3 : consensus requis mais invalide/absent ──
    if is_critical and not is_consensus_valid(view):
        status_txt = view.status if view is not None else "absent"
        reason = f"consensus requis mais résultat invalide/absent (status={status_txt})"
        if policy.fail_soft_allowed:
            # D4 : fail-soft autorisé EXPLICITEMENT par policy → bannière + signature
            signed = _try_sign_or_none(
                output_text=output_text + _fail_soft_banner(reason, correlation_id),
                input_text=input_text, consensus_view=view, criticality_level=criticality_level,
                policy=policy, timestamp=timestamp, trace_id=correlation_id, model=model,
                human_review_required=human_review_required,
            )
            return CriticalOutputResult(
                decision=CriticalOutputDecision.FAIL_SOFT_BANNER,
                can_emit=True,
                output_text=output_text + _fail_soft_banner(reason, correlation_id),
                reason=reason,
                signed_output=signed,
                correlation_id=correlation_id,
            )
        # défaut : fail-closed
        logger.warning("FAIL-CLOSED [%s]: %s", correlation_id, reason)
        return CriticalOutputResult(
            decision=CriticalOutputDecision.FAIL_CLOSED,
            can_emit=False,
            output_text=_fail_closed_notice(reason, correlation_id),
            reason=reason,
            signed_output=None,
            correlation_id=correlation_id,
        )

    # Texte émis : sur sortie critique à fraîcheur non prouvée, bannière obsolescence.
    # Le texte signé == le texte émis (cohérence de la signature, anti-tamper).
    emitted_text = output_text
    if recency_unverified:
        emitted_text = output_text + _recency_banner(timestamp[:10], correlation_id)

    # ── Signature (D5/D6) ──
    try:
        signature = sign_evidence_output(
            output_text=emitted_text, input_text=input_text, consensus_view=view,
            criticality_level=criticality_level, policy=policy, timestamp=timestamp,
            trace_id=correlation_id, model=model, human_review_required=human_review_required,
        )
    except RuntimeError as exc:
        # secret absent
        if is_production and is_critical:
            reason = f"secret de signature absent en production (sortie critique) : {exc}"
            logger.error("FAIL-CLOSED [%s]: %s", correlation_id, reason)
            return CriticalOutputResult(
                decision=CriticalOutputDecision.FAIL_CLOSED,
                can_emit=False,
                output_text=_fail_closed_notice(reason, correlation_id),
                reason=reason,
                signed_output=None,
                correlation_id=correlation_id,
            )
        # hors critique (ou dev) : émission dégradée non signée, tracée
        logger.warning("EMIT_UNSIGNED_DEGRADED [%s]: %s", correlation_id, exc)
        return CriticalOutputResult(
            decision=CriticalOutputDecision.EMIT_UNSIGNED_DEGRADED,
            can_emit=True,
            output_text=emitted_text,
            reason=f"secret de signature absent (hors chemin critique) : {exc}",
            signed_output=None,
            correlation_id=correlation_id,
        )

    signed_output = _assemble_signed_output(
        output_text=emitted_text, view=view, criticality_level=criticality_level,
        requires_consensus=requires_consensus, policy=policy, signature=signature,
        trace_id=correlation_id, model=model, human_review_required=human_review_required,
        recency_verified=recency_verified,
    )
    decision = (
        CriticalOutputDecision.EMIT_SIGNED if is_critical
        else CriticalOutputDecision.EMIT_NONCRITICAL_SIGNED
    )
    return CriticalOutputResult(
        decision=decision,
        can_emit=True,
        output_text=emitted_text,
        reason="recency_unverified" if recency_unverified else "ok",
        signed_output=signed_output,
        correlation_id=correlation_id,
    )


def _try_sign_or_none(**kwargs) -> Optional[Dict[str, Any]]:
    """Signe sans propager l'absence de secret (utilisé en fail-soft explicite)."""
    try:
        sig = sign_evidence_output(**kwargs)
    except RuntimeError as exc:
        logger.warning("fail-soft sans signature (secret absent): %s", exc)
        return None
    view = kwargs.get("consensus_view")
    return _assemble_signed_output(
        output_text=kwargs["output_text"], view=view,
        criticality_level=kwargs["criticality_level"], requires_consensus=True,
        policy=kwargs["policy"], signature=sig, trace_id=kwargs["trace_id"],
        model=kwargs.get("model"), human_review_required=kwargs.get("human_review_required"),
    )


def _agent_query_text(agent) -> Optional[str]:
    """Best-effort extraction de la requête utilisateur depuis l'agent (duck-typed)."""
    msg = getattr(agent, "last_user_message", None)
    if msg is None:
        return None
    fn = getattr(msg, "output_text", None)
    if callable(fn):
        try:
            return str(fn())
        except Exception:
            pass
    content = getattr(msg, "content", None)
    if isinstance(content, dict):
        return str(content.get("message") or content.get("text") or content)
    return str(content) if content is not None else None


def _agent_model_name(agent) -> Optional[str]:
    cfg = getattr(agent, "config", None)
    chat_model = getattr(cfg, "chat_model", None) if cfg else None
    if chat_model is None:
        return None
    name = getattr(chat_model, "name", None)
    provider = getattr(chat_model, "provider", None)
    provider = getattr(provider, "value", provider)
    if name and provider:
        return f"{provider}/{name}"
    return name or (str(provider) if provider else None)


def finalize_pipeline_short_circuit(agent, output_text: str) -> CriticalOutputResult:
    """Finalise une sortie de pipeline court-circuité (legal/adversarial/contract).

    Lit le contexte de signature posé par l'extension de pipeline sur l'agent
    (`_consensus_result`, `_pipeline_requires_consensus`, `_output_policy`,
    `_pipeline_criticality_level`, `_pipeline_human_review`) et applique la MÊME
    doctrine ADR-010 que le chemin chat. Aucun nouveau mécanisme : réutilise
    `finalize_critical_output`.
    """
    def _get(key):
        getter = getattr(agent, "get_data", None)
        if callable(getter):
            try:
                return getter(key)
            except Exception:
                return None
        return None

    requires_consensus = bool(_get("_pipeline_requires_consensus"))
    criticality_level = _get("_pipeline_criticality_level") or (
        "LEVEL_3" if requires_consensus else "LEVEL_1"
    )
    human_review = _get("_pipeline_human_review")
    recency = _get("_pipeline_recency_verified")
    return finalize_critical_output(
        output_text=output_text,
        requires_consensus=requires_consensus,
        criticality_level=criticality_level,
        consensus_result=_get("_consensus_result"),
        policy=OutputPolicy.from_env_or_data(_get("_output_policy")),
        input_text=_agent_query_text(agent),
        trace_id=_get("_legal_safe_correlation_id"),
        model=_agent_model_name(agent),
        human_review_required=bool(human_review) if human_review is not None else None,
        recency_verified=bool(recency) if recency is not None else None,
    )


def _assemble_signed_output(
    *,
    output_text: str,
    view: Optional[ConsensusResultView],
    criticality_level: str,
    requires_consensus: bool,
    policy: OutputPolicy,
    signature: Dict[str, Any],
    trace_id: str,
    model: Optional[str],
    human_review_required: Optional[bool],
    recency_verified: Optional[bool] = None,
) -> Dict[str, Any]:
    """Structure de sortie signée audit-ready (ADR-010 §6)."""
    covered = signature.get("covered_fields", {})
    # Fraîcheur non prouvée sur une sortie critique → marquée + escaladée (signée
    # via human_review_required, qui fait partie des champs couverts).
    recency_unverified = bool(requires_consensus) and (recency_verified is not True)
    return {
        "output": output_text,
        "criticality_assessment": {
            "criticality_level": criticality_level,
            "requires_consensus": requires_consensus,
        },
        "recency": {
            "recency_verified": bool(recency_verified) if recency_verified is not None else None,
            "recency_review_required": recency_unverified,
        },
        # On stocke la vue canonique (status/approved/proposal_id/...) : c'est
        # EXACTEMENT ce qui est couvert par consensus_result_hash, donc reproductible
        # à la vérification quel que soit le type d'entrée (dict ou ConsensusResult).
        "consensus_result": (view.canonical() if view is not None else None),
        "signature": {
            "value": signature["value"],
            "version": signature["version"],
            "method": signature["method"],
            "key_id": signature["key_id"],
            "signed_at": signature["signed_at"],
        },
        "audit_metadata": {
            "trace_id": trace_id,
            "model": model,
            "human_review_required": human_review_required,
            "input_hash": covered.get("input_hash"),
            "output_hash": covered.get("output_hash"),
            "consensus_result_hash": covered.get("consensus_result_hash"),
        },
        "policy": {
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "fail_soft_allowed": policy.fail_soft_allowed,
        },
        "signature_version": signature["version"],
        "verification_hint": (
            "verify_evidence_signature(signed_output) — requiert EVIDENCE_HMAC_KEY "
            "(ou la clé publique RSA) du signataire."
        ),
    }
