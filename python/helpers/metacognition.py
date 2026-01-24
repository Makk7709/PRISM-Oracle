"""
Korev Oracle — Metacognition Module
====================================

Module de métacognition pour l'auto-évaluation, la détection d'incertitude,
l'escalade contrôlée et l'apprentissage léger.

GARANTIES DE SÉCURITÉ:
- Aucun chain-of-thought brut exposé
- Pas de PII dans les stats/logs
- Stockage minimal et sans contenu conversationnel

FONCTIONNALITÉS:
- Évaluation de confiance multi-facteurs
- Détection d'incertitude et contradictions
- Décision d'escalade (NONE/ASK_CLARIFY/HUMAN_REVIEW/SAFE_REFUSE)
- Apprentissage statistique léger (taux d'échec, patterns)

Author: Korev AI
License: Proprietary
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from python.helpers.reasoning_engine import (
    ReasoningContext,
    ReasoningOutcome,
    ReasoningFlag,
    EscalationType,
    TraceStep,
)


# ============================================================================
# EXCEPTIONS (PROD-SAFE)
# ============================================================================

class InvariantViolationError(Exception):
    """
    Exception levée quand un invariant de sécurité est violé.
    
    PROD-SAFE: Cette exception n'est PAS supprimable via python -O.
    Elle garantit que les violations d'invariants sont détectées en production.
    
    Usage:
        raise InvariantViolationError("I2_MONOTONICITY", details={...})
    """
    
    def __init__(self, invariant_id: str, message: str = "", details: Optional[Dict[str, Any]] = None):
        self.invariant_id = invariant_id
        self.details = details or {}
        # Message sans PII: uniquement invariant_id et valeurs numériques/enum
        safe_message = f"INVARIANT_VIOLATION [{invariant_id}]: {message}"
        super().__init__(safe_message)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export sans PII pour logging."""
        return {
            "error_type": "InvariantViolationError",
            "invariant_id": self.invariant_id,
            "details": self.details,
        }


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(frozen=True)
class MetacognitionConfig:
    """Configuration du module metacognition (immutable)."""
    # Seuils de confiance
    confidence_high: float = 0.85
    confidence_medium: float = 0.6
    confidence_low: float = 0.4
    confidence_critical: float = 0.25
    
    # Seuils d'escalade
    escalate_on_confidence_below: float = 0.5
    human_review_threshold: float = 0.35
    safe_refuse_threshold: float = 0.2
    
    # Limites
    max_clarification_questions: int = 2
    max_uncertainty_reasons: int = 3
    
    # Apprentissage
    enable_learning: bool = True
    stats_file_path: Optional[str] = None  # None = in-memory only
    stats_max_entries: int = 1000


# ============================================================================
# ENUMS
# ============================================================================

class UncertaintyType(Enum):
    MISSING_INFORMATION = "missing_information"
    CONTRADICTORY_DATA = "contradictory_data"
    LOW_CONFIDENCE_TOOLS = "low_confidence_tools"
    NOVEL_PATTERN = "novel_pattern"
    POLICY_AMBIGUITY = "policy_ambiguity"
    EXTERNAL_DEPENDENCY = "external_dependency"
    TIME_CONSTRAINT = "time_constraint"


class ConfidenceLevel(Enum):
    HIGH = "high"        # > 0.85
    MEDIUM = "medium"    # 0.6 - 0.85
    LOW = "low"          # 0.4 - 0.6
    CRITICAL = "critical"  # < 0.4


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class UncertaintySignal:
    """Signal d'incertitude détecté."""
    type: UncertaintyType
    description: str  # <= 80 chars
    severity: float  # 0-1
    source: str  # Ex: "tool_execution", "llm_response"
    
    def __post_init__(self):
        self.description = self.description[:80]


@dataclass
class ConfidenceAnalysis:
    """Analyse de confiance multi-facteurs."""
    overall: float
    level: ConfidenceLevel
    factors: Dict[str, float]  # factor_name -> score
    signals: List[UncertaintySignal]
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export sans CoT."""
        return {
            "overall": self.overall,
            "level": self.level.value,
            "factors_count": len(self.factors),
            "signals_count": len(self.signals),
        }


@dataclass
class ClarificationQuestion:
    """Question de clarification générée."""
    question: str  # <= 150 chars
    priority: int  # 1 = highest
    expected_info_type: str  # Ex: "confirmation", "specification", "choice"
    
    def __post_init__(self):
        self.question = self.question[:150]


@dataclass
class MemoryHint:
    """Suggestion pour la mémoire."""
    action: str  # "remember" | "forget" | "update"
    key: str  # Clé/topic (pas de contenu brut)
    reason: str  # <= 60 chars
    
    def __post_init__(self):
        self.reason = self.reason[:60]


@dataclass
class MetaDecision:
    """Décision de metacognition."""
    confidence: float
    confidence_analysis: ConfidenceAnalysis
    uncertainty_reasons: List[str]  # <= 3 raisons courtes
    escalation: EscalationType
    clarification_questions: List[str]  # Questions générées
    memory_hints: List[MemoryHint]
    should_retry: bool
    debug_id: str
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export sans CoT."""
        return {
            "debug_id": self.debug_id,
            "confidence": self.confidence,
            "escalation": self.escalation.value,
            "uncertainty_count": len(self.uncertainty_reasons),
            "questions_count": len(self.clarification_questions),
            "should_retry": self.should_retry,
        }


# ============================================================================
# LEARNING STATS (LIGHTWEIGHT)
# ============================================================================

@dataclass
class LearningStats:
    """
    Stats d'apprentissage léger.
    
    Stocke uniquement des métriques agrégées, pas de contenu conversationnel.
    """
    tool_failure_rates: Dict[str, float] = field(default_factory=dict)
    task_type_uncertainty: Dict[str, float] = field(default_factory=dict)
    escalation_counts: Dict[str, int] = field(default_factory=dict)
    total_evaluations: int = 0
    avg_confidence: float = 0.0
    last_updated: str = ""
    
    def update_tool_failure(self, tool_name: str, failed: bool):
        """Met à jour le taux d'échec d'un outil."""
        current = self.tool_failure_rates.get(tool_name, 0.0)
        # Moving average simple
        alpha = 0.1
        new_value = 1.0 if failed else 0.0
        self.tool_failure_rates[tool_name] = current + alpha * (new_value - current)
    
    def update_task_uncertainty(self, task_hash: str, uncertainty: float):
        """Met à jour l'incertitude pour un type de tâche."""
        current = self.task_type_uncertainty.get(task_hash, 0.5)
        alpha = 0.1
        self.task_type_uncertainty[task_hash] = current + alpha * (uncertainty - current)
        
        # Limiter le nombre d'entrées
        if len(self.task_type_uncertainty) > 500:
            # Garder les plus récents (approximation)
            self.task_type_uncertainty = dict(
                list(self.task_type_uncertainty.items())[-400:]
            )
    
    def record_escalation(self, escalation: EscalationType):
        """Enregistre une escalade."""
        key = escalation.value
        self.escalation_counts[key] = self.escalation_counts.get(key, 0) + 1
    
    def update_evaluation(self, confidence: float):
        """Met à jour les stats d'évaluation."""
        self.total_evaluations += 1
        n = self.total_evaluations
        self.avg_confidence = self.avg_confidence + (confidence - self.avg_confidence) / n
        self.last_updated = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour stockage."""
        return {
            "tool_failure_rates": self.tool_failure_rates,
            "task_type_uncertainty": dict(list(self.task_type_uncertainty.items())[-100:]),
            "escalation_counts": self.escalation_counts,
            "total_evaluations": self.total_evaluations,
            "avg_confidence": self.avg_confidence,
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningStats":
        """Désérialise depuis le stockage."""
        return cls(
            tool_failure_rates=data.get("tool_failure_rates", {}),
            task_type_uncertainty=data.get("task_type_uncertainty", {}),
            escalation_counts=data.get("escalation_counts", {}),
            total_evaluations=data.get("total_evaluations", 0),
            avg_confidence=data.get("avg_confidence", 0.0),
            last_updated=data.get("last_updated", ""),
        )


# ============================================================================
# METACOGNITION - MAIN CLASS
# ============================================================================

class Metacognition:
    """
    Module de métacognition principal.
    
    Usage:
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
    """
    
    def __init__(
        self,
        config: Optional[MetacognitionConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or MetacognitionConfig()
        self._logger = logger or logging.getLogger(__name__)
        self._stats = LearningStats()
        
        # Charger les stats si fichier configuré
        if self.config.stats_file_path and self.config.enable_learning:
            self._load_stats()
    
    async def evaluate(
        self,
        outcome: ReasoningOutcome,
        context: ReasoningContext,
    ) -> MetaDecision:
        """
        Évalue un résultat de raisonnement.
        
        Args:
            outcome: Résultat du reasoning engine
            context: Contexte de raisonnement
        
        Returns:
            MetaDecision avec escalation et recommendations
        """
        debug_id = f"meta_{outcome.debug_id}"
        
        self._log_event("meta_eval_start", debug_id, {})
        
        try:
            # ================================================================
            # POLITIQUE D'ESCALADE NON-DILUABLE ET MONOTONE
            # ================================================================
            # 
            # INVARIANTS:
            # I1. Non-dilution: raw_confidence < safe_refuse_threshold => SAFE_REFUSE
            #     Aucun score composite ne peut lever cette escalade.
            # I2. Monotonicité: les signaux ne peuvent que DURCIR l'escalade
            #     Ordre: NONE < ASK_CLARIFY < HUMAN_REVIEW < SAFE_REFUSE
            # ================================================================
            
            raw_confidence = outcome.confidence  # Source de vérité pour hard guards
            
            # Toujours calculer l'analyse composite (pour observabilité)
            confidence_analysis = self._analyze_confidence(outcome, context)
            signals = self._detect_uncertainty_signals(outcome, context)
            uncertainty_reasons = self._summarize_uncertainties(signals)
            
            # HARD GUARD 1: Non-dilution (I1)
            # raw < safe_refuse_threshold => SAFE_REFUSE, point final
            if raw_confidence < self.config.safe_refuse_threshold:
                escalation = EscalationType.SAFE_REFUSE
                self._log_event("hard_guard_safe_refuse", debug_id, {
                    "raw_confidence": raw_confidence,
                    "threshold": self.config.safe_refuse_threshold,
                    "rationale": "I1_NON_DILUTION",
                })
            else:
                # Calculer l'escalade de BASE à partir de raw_confidence
                base_escalation = self._compute_base_escalation(raw_confidence)
                
                # Appliquer le durcissement via signaux (I2: monotone)
                escalation = self._apply_hardening_signals(
                    base_escalation,
                    signals,
                    outcome.flags,
                    raw_confidence,
                )
                
                self._log_event("escalation_computed", debug_id, {
                    "raw_confidence": raw_confidence,
                    "composite_confidence": confidence_analysis.overall,
                    "base_escalation": base_escalation.value,
                    "final_escalation": escalation.value,
                })
            
            # 5. Générer les questions de clarification si nécessaire
            questions: List[str] = []
            if escalation == EscalationType.ASK_CLARIFY:
                questions = self._generate_clarification_questions(
                    signals, context
                )
            
            # 6. Générer les hints mémoire
            memory_hints = self._generate_memory_hints(outcome, confidence_analysis)
            
            # 7. Déterminer si retry
            should_retry = self._should_retry(outcome, confidence_analysis)
            
            # 8. Apprentissage
            if self.config.enable_learning:
                self._learn_from_evaluation(outcome, escalation, signals)
            
            decision = MetaDecision(
                confidence=confidence_analysis.overall,
                confidence_analysis=confidence_analysis,
                uncertainty_reasons=uncertainty_reasons,
                escalation=escalation,
                clarification_questions=questions,
                memory_hints=memory_hints,
                should_retry=should_retry,
                debug_id=debug_id,
            )
            
            self._log_event("meta_eval_end", debug_id, decision.to_safe_dict())
            
            return decision
            
        except Exception as e:
            self._logger.error(f"Metacognition error: {str(e)[:100]}")
            return self._create_fallback_decision(debug_id)
    
    # ========================================================================
    # CONFIDENCE ANALYSIS
    # ========================================================================
    
    def _analyze_confidence(
        self,
        outcome: ReasoningOutcome,
        context: ReasoningContext,
    ) -> ConfidenceAnalysis:
        """Analyse multi-facteurs de la confiance."""
        factors: Dict[str, float] = {}
        signals: List[UncertaintySignal] = []
        
        # Facteur 1: Confiance brute du reasoning
        factors["reasoning_confidence"] = outcome.confidence
        
        # Facteur 2: Taux de succès des sous-tâches
        if outcome.subtasks_total > 0:
            success_rate = outcome.subtasks_completed / outcome.subtasks_total
            factors["task_success_rate"] = success_rate
            
            if success_rate < 0.7:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.LOW_CONFIDENCE_TOOLS,
                    description=f"Low task success: {success_rate:.0%}",
                    severity=1 - success_rate,
                    source="task_execution",
                ))
        else:
            factors["task_success_rate"] = 0.5
        
        # Facteur 3: Backtracks (indicateur de difficulté)
        backtrack_penalty = min(outcome.backtracks_used * 0.1, 0.3)
        factors["backtrack_factor"] = 1 - backtrack_penalty
        
        if outcome.backtracks_used > 1:
            signals.append(UncertaintySignal(
                type=UncertaintyType.LOW_CONFIDENCE_TOOLS,
                description=f"Multiple backtracks: {outcome.backtracks_used}",
                severity=min(outcome.backtracks_used * 0.15, 0.5),
                source="reasoning",
            ))
        
        # Facteur 4: Flags de raisonnement
        flag_penalty = len(outcome.flags) * 0.05
        factors["flag_factor"] = max(0.5, 1 - flag_penalty)
        
        # Facteur 5: Historical learning (si disponible)
        task_hash = self._hash_task_type(context.user_query)
        historical_uncertainty = self._stats.task_type_uncertainty.get(task_hash, 0.5)
        factors["historical_factor"] = 1 - historical_uncertainty
        
        # Calculer la confiance globale (moyenne pondérée)
        weights = {
            "reasoning_confidence": 0.35,
            "task_success_rate": 0.25,
            "backtrack_factor": 0.15,
            "flag_factor": 0.15,
            "historical_factor": 0.10,
        }
        
        overall = sum(factors[k] * weights[k] for k in factors)
        overall = max(0.0, min(1.0, overall))
        
        # Déterminer le niveau
        level = self._confidence_to_level(overall)
        
        return ConfidenceAnalysis(
            overall=overall,
            level=level,
            factors=factors,
            signals=signals,
        )
    
    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convertit une confiance en niveau."""
        if confidence >= self.config.confidence_high:
            return ConfidenceLevel.HIGH
        elif confidence >= self.config.confidence_medium:
            return ConfidenceLevel.MEDIUM
        elif confidence >= self.config.confidence_low:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.CRITICAL
    
    # ========================================================================
    # UNCERTAINTY DETECTION
    # ========================================================================
    
    def _detect_uncertainty_signals(
        self,
        outcome: ReasoningOutcome,
        context: ReasoningContext,
    ) -> List[UncertaintySignal]:
        """Détecte les signaux d'incertitude."""
        signals: List[UncertaintySignal] = []
        
        # Signal: Flags de raisonnement
        for flag in outcome.flags:
            if flag == ReasoningFlag.MISSING_INFO:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.MISSING_INFORMATION,
                    description="Missing information detected",
                    severity=0.6,
                    source="reasoning_flags",
                ))
            elif flag == ReasoningFlag.CONTRADICTION:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.CONTRADICTORY_DATA,
                    description="Contradictory information",
                    severity=0.8,
                    source="reasoning_flags",
                ))
            elif flag == ReasoningFlag.NOVELTY:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.NOVEL_PATTERN,
                    description="Novel pattern encountered",
                    severity=0.5,
                    source="reasoning_flags",
                ))
            elif flag == ReasoningFlag.POLICY_RISK:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.POLICY_AMBIGUITY,
                    description="Policy ambiguity detected",
                    severity=0.7,
                    source="reasoning_flags",
                ))
        
        # Signal: Confiance basse
        if outcome.confidence < self.config.confidence_low:
            signals.append(UncertaintySignal(
                type=UncertaintyType.LOW_CONFIDENCE_TOOLS,
                description=f"Overall confidence: {outcome.confidence:.0%}",
                severity=1 - outcome.confidence,
                source="confidence",
            ))
        
        # Signal: Échecs d'outils (basé sur l'historique)
        for tool, failure_rate in self._stats.tool_failure_rates.items():
            if failure_rate > 0.3 and tool in context.available_tools:
                signals.append(UncertaintySignal(
                    type=UncertaintyType.LOW_CONFIDENCE_TOOLS,
                    description=f"Tool {tool} has {failure_rate:.0%} failure rate",
                    severity=failure_rate,
                    source="historical",
                ))
        
        return signals
    
    def _summarize_uncertainties(
        self,
        signals: List[UncertaintySignal],
    ) -> List[str]:
        """Résume les incertitudes en raisons courtes."""
        # Trier par sévérité
        sorted_signals = sorted(signals, key=lambda s: s.severity, reverse=True)
        
        # Prendre les top N
        reasons: List[str] = []
        seen_types: Set[UncertaintyType] = set()
        
        for signal in sorted_signals:
            if len(reasons) >= self.config.max_uncertainty_reasons:
                break
            if signal.type in seen_types:
                continue
            
            seen_types.add(signal.type)
            reasons.append(signal.description[:60])
        
        return reasons
    
    # ========================================================================
    # ESCALATION (NON-DILUABLE, MONOTONE)
    # ========================================================================
    
    # Ordre de sévérité des escalades (pour garantir la monotonicité)
    _ESCALATION_SEVERITY: Dict[EscalationType, int] = {
        EscalationType.NONE: 0,
        EscalationType.ASK_CLARIFY: 1,
        EscalationType.HUMAN_REVIEW: 2,
        EscalationType.SAFE_REFUSE: 3,
    }
    
    def _compute_base_escalation(self, raw_confidence: float) -> EscalationType:
        """
        Calcule l'escalade de BASE uniquement à partir de raw_confidence.
        
        C'est le plancher: les signaux peuvent durcir, jamais adoucir.
        
        Politique:
        - raw < safe_refuse_threshold => SAFE_REFUSE (géré par hard guard en amont)
        - raw < human_review_threshold => HUMAN_REVIEW
        - raw < escalate_on_confidence_below => ASK_CLARIFY
        - sinon => NONE
        """
        if raw_confidence < self.config.safe_refuse_threshold:
            return EscalationType.SAFE_REFUSE
        
        if raw_confidence < self.config.human_review_threshold:
            return EscalationType.HUMAN_REVIEW
        
        if raw_confidence < self.config.escalate_on_confidence_below:
            return EscalationType.ASK_CLARIFY
        
        return EscalationType.NONE
    
    def _apply_hardening_signals(
        self,
        base_escalation: EscalationType,
        signals: List[UncertaintySignal],
        flags: List[ReasoningFlag],
        raw_confidence: float,
    ) -> EscalationType:
        """
        Applique le durcissement via signaux/flags.
        
        INVARIANT MONOTONICITÉ (I2):
        Le résultat est TOUJOURS >= base_escalation en sévérité.
        Les signaux ne peuvent que DURCIR, jamais ADOUCIR.
        
        Args:
            base_escalation: Escalade de base (plancher)
            signals: Signaux d'incertitude détectés
            flags: Flags du raisonnement
            raw_confidence: Confiance brute (pour log)
        
        Returns:
            Escalade finale (>= base_escalation en sévérité)
        """
        current = base_escalation
        base_severity = self._ESCALATION_SEVERITY[base_escalation]
        
        # Flags critiques → HUMAN_REVIEW minimum
        critical_flags = {
            ReasoningFlag.POLICY_RISK,
            ReasoningFlag.NEEDS_HUMAN,
        }
        if any(f in critical_flags for f in flags):
            if self._ESCALATION_SEVERITY[EscalationType.HUMAN_REVIEW] > base_severity:
                current = EscalationType.HUMAN_REVIEW
        
        # Signaux haute sévérité multiples → durcir vers ASK_CLARIFY ou plus
        high_severity_signals = [s for s in signals if s.severity > 0.7]
        if len(high_severity_signals) >= 2:
            candidate = EscalationType.ASK_CLARIFY
            if self._ESCALATION_SEVERITY[candidate] > self._ESCALATION_SEVERITY[current]:
                current = candidate
        
        # MISSING_INFO → peut orienter vers ASK_CLARIFY si on n'est pas déjà plus sévère
        if ReasoningFlag.MISSING_INFO in flags:
            if self._ESCALATION_SEVERITY[EscalationType.ASK_CLARIFY] > self._ESCALATION_SEVERITY[current]:
                current = EscalationType.ASK_CLARIFY
        
        # Vérification finale: monotonicité garantie (PROD-SAFE)
        # NOTE: Pas d'assert ici — les asserts sont supprimables via python -O
        final_severity = self._ESCALATION_SEVERITY[current]
        if final_severity < base_severity:
            raise InvariantViolationError(
                invariant_id="I2_MONOTONICITY",
                message=f"Escalade réduite: {current.value} < {base_escalation.value}",
                details={
                    "base_escalation": base_escalation.value,
                    "final_escalation": current.value,
                    "base_severity": base_severity,
                    "final_severity": final_severity,
                },
            )
        
        return current
    
    def _determine_escalation(
        self,
        confidence: float,
        signals: List[UncertaintySignal],
        flags: List[ReasoningFlag],
    ) -> EscalationType:
        """
        DEPRECATED: Utilisez _compute_base_escalation + _apply_hardening_signals.
        
        Conservé pour compatibilité ascendante.
        """
        base = self._compute_base_escalation(confidence)
        return self._apply_hardening_signals(base, signals, flags, confidence)
    
    # ========================================================================
    # CLARIFICATION
    # ========================================================================
    
    def _generate_clarification_questions(
        self,
        signals: List[UncertaintySignal],
        context: ReasoningContext,
    ) -> List[str]:
        """Génère des questions de clarification."""
        questions: List[str] = []
        
        # Générer selon le type d'incertitude
        for signal in signals[:self.config.max_clarification_questions]:
            if signal.type == UncertaintyType.MISSING_INFORMATION:
                questions.append(
                    "Could you provide more details about your request?"
                )
            elif signal.type == UncertaintyType.CONTRADICTORY_DATA:
                questions.append(
                    "I found conflicting information. Which aspect should I prioritize?"
                )
            elif signal.type == UncertaintyType.POLICY_AMBIGUITY:
                questions.append(
                    "This involves policy considerations. Should I proceed with caution?"
                )
            elif signal.type == UncertaintyType.NOVEL_PATTERN:
                questions.append(
                    "This is a new type of request. Could you confirm the expected outcome?"
                )
        
        # Dédupliquer et limiter
        seen: Set[str] = set()
        unique_questions: List[str] = []
        for q in questions:
            if q not in seen and len(unique_questions) < self.config.max_clarification_questions:
                seen.add(q)
                unique_questions.append(q)
        
        return unique_questions
    
    # ========================================================================
    # MEMORY HINTS
    # ========================================================================
    
    def _generate_memory_hints(
        self,
        outcome: ReasoningOutcome,
        analysis: ConfidenceAnalysis,
    ) -> List[MemoryHint]:
        """Génère des suggestions pour la mémoire."""
        hints: List[MemoryHint] = []
        
        # Suggérer de mémoriser si haute confiance
        if analysis.level == ConfidenceLevel.HIGH:
            hints.append(MemoryHint(
                action="remember",
                key=f"success_pattern_{outcome.debug_id[:8]}",
                reason="High confidence outcome - worth remembering",
            ))
        
        # Suggérer d'oublier les patterns à faible confiance répétés
        if analysis.level == ConfidenceLevel.CRITICAL:
            hints.append(MemoryHint(
                action="forget",
                key="low_confidence_attempt",
                reason="Critical confidence - avoid repeating approach",
            ))
        
        return hints[:3]  # Max 3 hints
    
    # ========================================================================
    # RETRY LOGIC
    # ========================================================================
    
    def _should_retry(
        self,
        outcome: ReasoningOutcome,
        analysis: ConfidenceAnalysis,
    ) -> bool:
        """Détermine si un retry est recommandé."""
        # Ne pas retry si déjà beaucoup de backtracks
        if outcome.backtracks_used >= 2:
            return False
        
        # Ne pas retry si confiance critique
        if analysis.level == ConfidenceLevel.CRITICAL:
            return False
        
        # Retry si confiance basse mais pas critique
        if analysis.level == ConfidenceLevel.LOW:
            return True
        
        # Retry si beaucoup de tâches ont échoué
        if outcome.subtasks_total > 0:
            failure_rate = 1 - (outcome.subtasks_completed / outcome.subtasks_total)
            if failure_rate > 0.5:
                return True
        
        return False
    
    # ========================================================================
    # LEARNING
    # ========================================================================
    
    def _learn_from_evaluation(
        self,
        outcome: ReasoningOutcome,
        escalation: EscalationType,
        signals: List[UncertaintySignal],
    ):
        """Apprentissage léger à partir de l'évaluation."""
        # Enregistrer l'escalade
        self._stats.record_escalation(escalation)
        
        # Mettre à jour la confiance moyenne
        self._stats.update_evaluation(outcome.confidence)
        
        # Calculer l'incertitude pour ce type de tâche
        if signals:
            avg_severity = sum(s.severity for s in signals) / len(signals)
        else:
            avg_severity = 1 - outcome.confidence
        
        # Utiliser un hash du type de tâche (pas le contenu)
        # Pour l'instant, on utilise les flags comme proxy
        task_hash = "_".join(sorted(f.value for f in outcome.flags)) or "default"
        self._stats.update_task_uncertainty(task_hash, avg_severity)
        
        # Sauvegarder périodiquement
        if self._stats.total_evaluations % 10 == 0:
            self._save_stats()
    
    def _hash_task_type(self, query: str) -> str:
        """Hash le type de tâche (pas le contenu)."""
        # Extraire les mots-clés de structure
        keywords = []
        query_lower = query.lower()
        
        action_words = [
            "analyze", "create", "find", "search", "write",
            "calculate", "compare", "summarize", "explain",
        ]
        
        for word in action_words:
            if word in query_lower:
                keywords.append(word)
        
        if not keywords:
            keywords = ["generic"]
        
        return "_".join(sorted(keywords))
    
    def _load_stats(self):
        """Charge les stats depuis le fichier."""
        if not self.config.stats_file_path:
            return
        
        try:
            path = Path(self.config.stats_file_path)
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                    self._stats = LearningStats.from_dict(data)
                self._logger.info(f"Loaded metacognition stats: {self._stats.total_evaluations} evaluations")
        except Exception as e:
            self._logger.warning(f"Could not load stats: {e}")
    
    def _save_stats(self):
        """Sauvegarde les stats dans le fichier."""
        if not self.config.stats_file_path:
            return
        
        try:
            path = Path(self.config.stats_file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w") as f:
                json.dump(self._stats.to_dict(), f, indent=2)
        except Exception as e:
            self._logger.warning(f"Could not save stats: {e}")
    
    # ========================================================================
    # FALLBACK & UTILS
    # ========================================================================
    
    def _create_fallback_decision(self, debug_id: str) -> MetaDecision:
        """Crée une décision de fallback prudente."""
        return MetaDecision(
            confidence=0.3,
            confidence_analysis=ConfidenceAnalysis(
                overall=0.3,
                level=ConfidenceLevel.LOW,
                factors={"fallback": 0.3},
                signals=[],
            ),
            uncertainty_reasons=["Evaluation error - proceeding with caution"],
            escalation=EscalationType.HUMAN_REVIEW,
            clarification_questions=[],
            memory_hints=[],
            should_retry=False,
            debug_id=debug_id,
        )
    
    def _log_event(self, event: str, debug_id: str, data: Dict[str, Any]):
        """Log structuré JSON (pas de contenu user)."""
        log_entry = {
            "event": event,
            "correlation_id": debug_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._logger.info(json.dumps(log_entry))
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les stats (pas de PII)."""
        return self._stats.to_dict()
    
    def reset_stats(self):
        """Réinitialise les stats."""
        self._stats = LearningStats()
        if self.config.stats_file_path:
            self._save_stats()


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def create_metacognition(
    enable_learning: bool = True,
    stats_path: Optional[str] = None,
) -> Metacognition:
    """Crée une instance de Metacognition configurée."""
    config = MetacognitionConfig(
        enable_learning=enable_learning,
        stats_file_path=stats_path,
    )
    return Metacognition(config)
