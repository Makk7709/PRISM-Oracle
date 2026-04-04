"""
Dynamic Risk Register — scoring de risque par session et systeme.

Calcule un score de risque en temps reel a partir de :
  - divergence entre agents
  - niveau de confiance
  - type de requete
  - erreurs / timeouts
  - resultats de consensus

Declenche automatiquement HUMAN_REVIEW si le seuil est atteint.
Historise l'evolution pour audit trail.

Integration :
  - Extension monologue_end/_36_risk_assessment.py
  - Alimente human_review si HIGH/CRITICAL
  - Metrics via ObservabilityMetrics
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dynamic_risk_register")


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


RISK_THRESHOLDS = {
    RiskLevel.LOW: 0.0,
    RiskLevel.MEDIUM: 0.30,
    RiskLevel.HIGH: 0.60,
    RiskLevel.CRITICAL: 0.85,
}

HUMAN_REVIEW_THRESHOLD = RiskLevel.HIGH


@dataclass
class RiskFactor:
    """Un facteur individuel contribuant au score de risque."""
    name: str = ""
    weight: float = 0.0
    raw_value: float = 0.0
    normalized_value: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionRiskAssessment:
    """Evaluation de risque complete pour une session."""

    assessment_id: str = ""
    context_id: str = ""
    session_id: str = ""
    correlation_id: str = ""
    assessed_at: str = ""

    risk_score: float = 0.0
    risk_level: str = RiskLevel.LOW.value
    factors: List[RiskFactor] = field(default_factory=list)

    requires_human_review: bool = False
    human_review_reason: str = ""

    query_type: str = "unknown"
    agent_count: int = 0
    consensus_achieved: bool = True
    consensus_rounds: int = 0
    confidence_score: Optional[float] = None
    error_count: int = 0
    timeout_count: int = 0
    delegation_depth: int = 0
    tool_call_count: int = 0
    execution_time_ms: int = 0

    username: Optional[str] = None
    organization: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["factors"] = [f.to_dict() for f in self.factors]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRiskAssessment":
        factors_data = data.pop("factors", [])
        a = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        a.factors = [
            RiskFactor(**{k: v for k, v in fd.items() if k in RiskFactor.__dataclass_fields__})
            for fd in factors_data
        ]
        return a


@dataclass
class SystemRiskDashboard:
    """Tableau de bord risque systeme agrege."""

    computed_at: str = ""
    total_sessions: int = 0
    sessions_by_level: Dict[str, int] = field(default_factory=lambda: {
        "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0,
    })
    average_risk_score: float = 0.0
    max_risk_score: float = 0.0
    human_reviews_triggered: int = 0
    recent_assessments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_RISK_LOG_DIR = "tmp/audit"
_RISK_LOG_FILE = "risk_register.jsonl"


def _risk_log_path(base_dir: str = "") -> str:
    if not base_dir:
        from python.helpers.files import get_base_dir
        base_dir = get_base_dir()
    d = os.path.join(base_dir, _RISK_LOG_DIR)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, _RISK_LOG_FILE)


def assess_session_risk(
    *,
    context_id: str,
    session_id: str = "",
    correlation_id: str = "",
    query: str = "",
    query_type: str = "unknown",
    agent_count: int = 1,
    consensus_achieved: bool = True,
    consensus_rounds: int = 0,
    confidence_score: Optional[float] = None,
    error_count: int = 0,
    timeout_count: int = 0,
    delegation_depth: int = 0,
    tool_call_count: int = 0,
    execution_time_ms: int = 0,
    username: Optional[str] = None,
    organization: Optional[str] = None,
    base_dir: str = "",
) -> SessionRiskAssessment:
    """Evalue le risque d'une session et persiste le resultat."""
    import hashlib

    import math

    error_count = max(0, int(error_count))
    timeout_count = max(0, int(timeout_count))
    delegation_depth = max(0, int(delegation_depth))
    tool_call_count = max(0, int(tool_call_count))
    execution_time_ms = max(0, int(execution_time_ms))
    consensus_rounds = max(0, int(consensus_rounds))
    if confidence_score is not None:
        if math.isnan(confidence_score) or math.isinf(confidence_score):
            confidence_score = None
        else:
            confidence_score = max(0.0, min(1.0, float(confidence_score)))

    now = datetime.now(timezone.utc)
    assessment_id = f"RISK-{now.strftime('%Y%m%d')}-{hashlib.sha256(f'{context_id}-{now.isoformat()}'.encode()).hexdigest()[:8].upper()}"

    factors: List[RiskFactor] = []

    # --- Factor 1: Consensus failure ---
    consensus_risk = 0.0
    if not consensus_achieved:
        consensus_risk = 0.8
        if consensus_rounds >= 3:
            consensus_risk = 1.0
    elif consensus_rounds > 1:
        consensus_risk = min(0.3 * (consensus_rounds - 1), 0.6)
    factors.append(RiskFactor(
        name="consensus_failure",
        weight=0.30,
        raw_value=float(not consensus_achieved),
        normalized_value=consensus_risk,
        description=f"Consensus {'not achieved' if not consensus_achieved else 'achieved'} in {consensus_rounds} rounds",
    ))

    # --- Factor 2: Low confidence ---
    confidence_risk = 0.0
    if confidence_score is not None:
        if confidence_score < 0.3:
            confidence_risk = 1.0
        elif confidence_score < 0.5:
            confidence_risk = 0.7
        elif confidence_score < 0.7:
            confidence_risk = 0.4
        elif confidence_score < 0.85:
            confidence_risk = 0.2
    else:
        confidence_risk = 0.5
    factors.append(RiskFactor(
        name="low_confidence",
        weight=0.25,
        raw_value=confidence_score if confidence_score is not None else -1,
        normalized_value=confidence_risk,
        description=f"Confidence score: {confidence_score}",
    ))

    # --- Factor 3: Errors and timeouts ---
    error_risk = min(1.0, (error_count * 0.3 + timeout_count * 0.4))
    factors.append(RiskFactor(
        name="errors_timeouts",
        weight=0.20,
        raw_value=float(error_count + timeout_count),
        normalized_value=error_risk,
        description=f"{error_count} errors, {timeout_count} timeouts",
    ))

    # --- Factor 4: Delegation depth ---
    depth_risk = 0.0
    if delegation_depth > 3:
        depth_risk = min(1.0, 0.2 * (delegation_depth - 3))
    factors.append(RiskFactor(
        name="delegation_depth",
        weight=0.10,
        raw_value=float(delegation_depth),
        normalized_value=depth_risk,
        description=f"Delegation depth: {delegation_depth}",
    ))

    # --- Factor 5: Execution time anomaly ---
    time_risk = 0.0
    if execution_time_ms > 120_000:
        time_risk = 1.0
    elif execution_time_ms > 60_000:
        time_risk = 0.6
    elif execution_time_ms > 30_000:
        time_risk = 0.3
    factors.append(RiskFactor(
        name="execution_time",
        weight=0.10,
        raw_value=float(execution_time_ms),
        normalized_value=time_risk,
        description=f"Execution time: {execution_time_ms}ms",
    ))

    # --- Factor 6: Tool call volume ---
    tool_risk = 0.0
    if tool_call_count > 20:
        tool_risk = 0.8
    elif tool_call_count > 10:
        tool_risk = 0.4
    elif tool_call_count > 5:
        tool_risk = 0.2
    factors.append(RiskFactor(
        name="tool_call_volume",
        weight=0.05,
        raw_value=float(tool_call_count),
        normalized_value=tool_risk,
        description=f"Tool calls: {tool_call_count}",
    ))

    # --- Weighted aggregate ---
    total_weight = sum(f.weight for f in factors)
    risk_score = sum(f.weight * f.normalized_value for f in factors) / total_weight if total_weight > 0 else 0.0
    risk_score = round(min(1.0, max(0.0, risk_score)), 4)

    risk_level = RiskLevel.LOW
    for level in (RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM):
        if risk_score >= RISK_THRESHOLDS[level]:
            risk_level = level
            break

    requires_review = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    review_reason = ""
    if requires_review:
        top_factors = sorted(factors, key=lambda f: f.weight * f.normalized_value, reverse=True)[:3]
        review_reason = (
            f"Risk level {risk_level.value} (score={risk_score:.2f}). "
            f"Top factors: {', '.join(f.name for f in top_factors)}"
        )

    assessment = SessionRiskAssessment(
        assessment_id=assessment_id,
        context_id=context_id,
        session_id=session_id,
        correlation_id=correlation_id,
        assessed_at=now.isoformat(),
        risk_score=risk_score,
        risk_level=risk_level.value,
        factors=factors,
        requires_human_review=requires_review,
        human_review_reason=review_reason,
        query_type=query_type,
        agent_count=agent_count,
        consensus_achieved=consensus_achieved,
        consensus_rounds=consensus_rounds,
        confidence_score=confidence_score,
        error_count=error_count,
        timeout_count=timeout_count,
        delegation_depth=delegation_depth,
        tool_call_count=tool_call_count,
        execution_time_ms=execution_time_ms,
        username=username,
        organization=organization,
    )

    _append_to_risk_log(assessment, base_dir)

    try:
        from python.observability.runtime import ObservabilityMetrics
        metrics = ObservabilityMetrics.get()
        metrics.incr("risk_assessments_total")
        metrics.incr(f"risk_assessments_{risk_level.value.lower()}_total")
        if requires_review:
            metrics.incr("risk_human_review_triggered_total")
    except Exception:
        pass

    logger.info(
        "Risk assessment %s: score=%.2f level=%s review=%s",
        assessment_id, risk_score, risk_level.value, requires_review,
    )
    return assessment


def get_system_dashboard(
    limit: int = 50,
    base_dir: str = "",
) -> SystemRiskDashboard:
    """Calcule le dashboard de risque systeme a partir du log."""
    path = _risk_log_path(base_dir)
    if not os.path.exists(path):
        return SystemRiskDashboard(
            computed_at=datetime.now(timezone.utc).isoformat()
        )

    assessments: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    assessments.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    total = len(assessments)
    if total == 0:
        return SystemRiskDashboard(
            computed_at=datetime.now(timezone.utc).isoformat()
        )

    levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    scores = []
    reviews = 0

    for a in assessments:
        lvl = a.get("risk_level", "LOW")
        if lvl in levels:
            levels[lvl] += 1
        scores.append(a.get("risk_score", 0.0))
        if a.get("requires_human_review", False):
            reviews += 1

    recent = assessments[-limit:] if len(assessments) > limit else assessments

    return SystemRiskDashboard(
        computed_at=datetime.now(timezone.utc).isoformat(),
        total_sessions=total,
        sessions_by_level=levels,
        average_risk_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
        max_risk_score=max(scores) if scores else 0.0,
        human_reviews_triggered=reviews,
        recent_assessments=[
            {
                "assessment_id": a.get("assessment_id"),
                "risk_score": a.get("risk_score"),
                "risk_level": a.get("risk_level"),
                "assessed_at": a.get("assessed_at"),
            }
            for a in recent
        ],
    )


def _append_to_risk_log(assessment: SessionRiskAssessment, base_dir: str = "") -> None:
    """Ajoute une entree au log append-only du risk register."""
    path = _risk_log_path(base_dir)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(assessment.to_dict(), ensure_ascii=False) + "\n")
