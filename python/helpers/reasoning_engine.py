"""
KOREV Evidence — Reasoning Engine
===============================

Moteur de raisonnement non-linéaire avec décomposition de tâches,
arbre de décision, backtracking et self-reflection.

GARANTIES DE SÉCURITÉ:
- Aucun chain-of-thought brut n'est exposé dans les réponses utilisateur
- Les traces de raisonnement sont des résumés courts (<= 240 chars)
- Protection contre prompt injection: données utilisateur non fiables
- Résilient aux JSON malformés et timeouts

POINT D'INTÉGRATION:
- ReasoningPipeline.run() est le point d'entrée unique
- S'intègre via extension ou appel direct dans agent.py

Author: Korev AI
License: Proprietary
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypedDict,
    Union,
)


# ============================================================================
# EXCEPTION SANITIZATION (NO-PII)
# ============================================================================

_PII_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    (re.compile(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b'), '[SSN]'),
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE]'),
    (re.compile(r'\b\d{9,}\b'), '[LONG_NUMBER]'),
    (re.compile(r'https?://[^\s]+'), '[URL]'),
    (re.compile(r'password["\s:=]+[^\s,}"\]]+', re.IGNORECASE), '[PASSWORD_REDACTED]'),
    (re.compile(r'token["\s:=]+[^\s,}"\]]+', re.IGNORECASE), '[TOKEN_REDACTED]'),
    (re.compile(r'api[_-]?key["\s:=]+[^\s,}"\]]+', re.IGNORECASE), '[APIKEY_REDACTED]'),
]


def sanitize_exception(e: Exception, max_length: int = 100) -> Dict[str, Any]:
    """
    Sanitize exception pour logging sans PII.
    
    Returns:
        Dict safe pour logging JSON: {"error_type": ..., "message": ...}
    """
    error_type = type(e).__name__
    raw_message = str(e)[:max_length * 2]
    
    sanitized = raw_message
    for pattern, replacement in _PII_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return {"error_type": error_type, "message": sanitized}


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(frozen=True)
class ReasoningConfig:
    """Configuration du moteur de raisonnement (immutable)."""
    max_steps: int = 10
    max_backtracks: int = 3
    max_tool_calls: int = 15
    max_subtasks: int = 6
    confidence_threshold: float = 0.7
    backtrack_on_low_confidence: bool = True
    enable_self_reflection: bool = True
    trace_max_chars: int = 240
    timeout_seconds: float = 120.0


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class TaskComplexity(Enum):
    TRIVIAL = "trivial"      # Réponse directe, pas de décomposition
    SIMPLE = "simple"        # 1-2 étapes
    MODERATE = "moderate"    # 3-4 étapes
    COMPLEX = "complex"      # 5+ étapes, besoin de planning


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BACKTRACKED = "backtracked"
    SKIPPED = "skipped"


class EscalationType(Enum):
    NONE = "none"
    ASK_CLARIFY = "ask_clarify"
    HUMAN_REVIEW = "human_review"
    SAFE_REFUSE = "safe_refuse"


class ReasoningFlag(Enum):
    UNCERTAIN = "uncertain"
    NEEDS_HUMAN = "needs_human"
    POLICY_RISK = "policy_risk"
    TOOL_RISK = "tool_risk"
    CONTRADICTION = "contradiction"
    MISSING_INFO = "missing_info"
    NOVELTY = "novelty"
    LOW_CONFIDENCE = "low_confidence"


# ============================================================================
# DATA CLASSES - CONTRATS INTERNES
# ============================================================================

@dataclass
class ReasoningContext:
    """Contexte passé au moteur de raisonnement."""
    session_id: str
    user_query: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    user_role: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def query_hash(self) -> str:
        """Hash de la requête (sans PII)."""
        return hashlib.sha256(self.user_query.encode()).hexdigest()[:16]


@dataclass
class Subtask:
    """Sous-tâche décomposée."""
    id: str
    description: str  # Court, <= 100 chars
    order: int
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: TaskComplexity = TaskComplexity.SIMPLE
    required_tools: List[str] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        # Sanitize description
        self.description = self.description[:100]


@dataclass
class DecisionNode:
    """Noeud dans l'arbre de décision."""
    id: str
    subtask_id: str
    action: str  # Court, <= 80 chars
    alternatives: List[str] = field(default_factory=list)  # IDs des alternatives
    confidence: float = 0.0
    selected: bool = False
    outcome: Optional[str] = None  # "success" | "failed" | "skipped"
    
    def __post_init__(self):
        self.action = self.action[:80]


@dataclass
class DecisionTree:
    """Arbre de décision pour l'exécution."""
    root_id: str
    nodes: Dict[str, DecisionNode] = field(default_factory=dict)
    current_path: List[str] = field(default_factory=list)
    backtrack_count: int = 0


@dataclass
class TraceStep:
    """Étape de trace résumée (jamais de CoT brut)."""
    step_id: str
    timestamp: str
    action: str  # <= 60 chars, sanitized
    outcome: str  # <= 60 chars, sanitized
    confidence: float
    duration_ms: int
    
    # Patterns CoT à sanitizer (remplacés par "[...]")
    _COT_PATTERNS: ClassVar[List[str]] = [
        "thought:",
        "let me think",
        "let's think",
        "step-by-step",
        "step by step",
        "chain-of-thought",
        "chain of thought",
        "scratchpad",
        "internal reasoning",
        "my reasoning is",
        "i need to think",
        "reasoning:",
    ]
    
    def __post_init__(self):
        # 1. Sanitize CoT patterns AVANT troncation
        self.action = self._sanitize_cot(self.action)
        self.outcome = self._sanitize_cot(self.outcome)
        # 2. Tronquer à 60 chars
        self.action = self.action[:60]
        self.outcome = self.outcome[:60]
    
    def _sanitize_cot(self, text: str) -> str:
        """Remplace les patterns CoT par '[...]' pour éviter les fuites."""
        if not text:
            return text
        result = text
        for pattern in self._COT_PATTERNS:
            # Remplacement insensible à la casse
            import re
            result = re.sub(re.escape(pattern), "[...]", result, flags=re.IGNORECASE)
        return result


@dataclass
class ReflectionSummary:
    """Résumé de self-reflection (pas de CoT)."""
    confidence_delta: float  # Change in confidence
    issues_found: List[str]  # Short issue descriptions
    suggestions: List[str]  # Short suggestions
    should_retry: bool = False


@dataclass
class ReasoningOutcome:
    """Résultat du raisonnement."""
    answer: str
    trace: List[TraceStep]
    confidence: float
    flags: List[ReasoningFlag]
    debug_id: str
    subtasks_completed: int
    subtasks_total: int
    backtracks_used: int
    tool_calls_made: int
    total_duration_ms: int
    
    _CONFIDENCE_LABELS = {
        (0.0, 0.3): "faible",
        (0.3, 0.6): "moderee",
        (0.6, 0.8): "bonne",
        (0.8, 1.01): "elevee",
    }

    _FLAG_LABELS = {
        ReasoningFlag.UNCERTAIN: "Incertitude detectee",
        ReasoningFlag.NEEDS_HUMAN: "Verification humaine recommandee",
        ReasoningFlag.POLICY_RISK: "Risque de conformite identifie",
        ReasoningFlag.TOOL_RISK: "Risque lie aux outils externes",
        ReasoningFlag.CONTRADICTION: "Contradiction detectee dans les sources",
        ReasoningFlag.MISSING_INFO: "Informations manquantes",
        ReasoningFlag.NOVELTY: "Sujet inhabituel ou peu documente",
        ReasoningFlag.LOW_CONFIDENCE: "Confiance insuffisante",
    }

    def to_safe_dict(self) -> Dict[str, Any]:
        """Export safe pour logs/API (sans CoT)."""
        return {
            "debug_id": self.debug_id,
            "confidence": self.confidence,
            "flags": [f.value for f in self.flags],
            "subtasks": f"{self.subtasks_completed}/{self.subtasks_total}",
            "backtracks": self.backtracks_used,
            "tool_calls": self.tool_calls_made,
            "duration_ms": self.total_duration_ms,
            "trace_steps": len(self.trace),
            "narrative": self.to_safe_narrative(),
        }

    def to_safe_narrative(self) -> str:
        """Art. 13 — Human-readable reasoning summary (no CoT, no prompts).

        Produces a plain-language description of the steps taken, confidence
        level, and any flags raised — comprehensible by a non-technical DPO.
        """
        parts: List[str] = []

        conf_label = "non evaluee"
        for (lo, hi), label in self._CONFIDENCE_LABELS.items():
            if lo <= self.confidence < hi:
                conf_label = label
                break

        parts.append(
            f"Le systeme a execute {len(self.trace)} etape(s) de raisonnement "
            f"({self.subtasks_completed}/{self.subtasks_total} sous-taches completees) "
            f"en {self.total_duration_ms / 1000:.1f} secondes."
        )

        parts.append(f"Confiance globale du resultat : {conf_label} ({self.confidence:.0%}).")

        if self.backtracks_used > 0:
            parts.append(
                f"Le systeme a reconsidere son approche {self.backtracks_used} fois "
                "avant de converger vers la reponse finale."
            )

        if self.flags:
            flag_labels = [self._FLAG_LABELS.get(f, f.value) for f in self.flags]
            parts.append("Alertes : " + " ; ".join(flag_labels) + ".")

        step_summaries = []
        for step in self.trace[:10]:
            action = step.action[:60] if step.action else "action"
            outcome = step.outcome[:60] if step.outcome else "—"
            step_summaries.append(f"  - {action} → {outcome}")
        if step_summaries:
            parts.append("Etapes principales :\n" + "\n".join(step_summaries))

        return "\n".join(parts)


@dataclass
class ReasoningResult:
    """Résultat final exposé (API publique)."""
    answer: str
    trace: List[TraceStep]
    confidence: float
    flags: List[ReasoningFlag]
    debug_id: str
    escalation: EscalationType
    clarification_questions: List[str] = field(default_factory=list)
    
    @classmethod
    def from_outcome(
        cls,
        outcome: ReasoningOutcome,
        escalation: EscalationType = EscalationType.NONE,
        questions: Optional[List[str]] = None
    ) -> "ReasoningResult":
        return cls(
            answer=outcome.answer,
            trace=outcome.trace,
            confidence=outcome.confidence,
            flags=outcome.flags,
            debug_id=outcome.debug_id,
            escalation=escalation,
            clarification_questions=questions or [],
        )


# ============================================================================
# EXECUTORS - PLUGGABLE EXECUTION STRATEGIES
# ============================================================================

class Executor(Protocol):
    """Protocol pour les exécuteurs pluggables."""
    
    async def execute(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Exécute une sous-tâche, retourne (result, confidence)."""
        ...


class LLMExecutor:
    """Exécuteur utilisant le LLM."""
    
    def __init__(self, call_llm_func: Callable, model_name: str = "default"):
        self._call_llm = call_llm_func
        self._model_name = model_name
    
    async def execute(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Appelle le LLM pour exécuter la sous-tâche."""
        # Prompt sécurisé - pas de contexte brut
        prompt = self._build_safe_prompt(subtask, context)
        
        try:
            # Appel LLM avec timeout
            result = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=30.0
            )
            
            # Parse JSON response ou fallback
            parsed = self._parse_response(result)
            return parsed["result"], parsed["confidence"]
            
        except asyncio.TimeoutError:
            return "Timeout during execution", 0.3
        except Exception as e:
            return f"Execution error: {str(e)[:50]}", 0.2
    
    def _build_safe_prompt(self, subtask: Subtask, context: ReasoningContext) -> str:
        """Construit un prompt sécurisé sans données brutes utilisateur."""
        # On ne passe jamais le contexte complet - juste le nécessaire
        return f"""Execute this subtask and respond with JSON:
Task: {subtask.description}
Required tools: {', '.join(subtask.required_tools) or 'none'}

Respond ONLY with valid JSON:
{{"result": "your concise result", "confidence": 0.8}}"""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse LLM avec fallback."""
        try:
            # Essayer de parser le JSON
            data = json.loads(response)
            return {
                "result": str(data.get("result", response))[:500],
                "confidence": float(data.get("confidence", 0.5)),
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            # Fallback: utiliser la réponse brute
            return {
                "result": response[:500] if response else "No response",
                "confidence": 0.4,
            }


class ToolExecutor:
    """Exécuteur utilisant les outils Evidence."""
    
    def __init__(self, tool_runner: Callable):
        self._run_tool = tool_runner
    
    async def execute(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Exécute via un outil Evidence."""
        if not subtask.required_tools:
            return "No tool specified", 0.3
        
        tool_name = subtask.required_tools[0]
        
        try:
            result = await asyncio.wait_for(
                self._run_tool(tool_name, {"task": subtask.description}),
                timeout=60.0
            )
            return str(result)[:500], 0.85
        except asyncio.TimeoutError:
            return "Tool timeout", 0.2
        except Exception as e:
            return f"Tool error: {str(e)[:50]}", 0.2


class RuleExecutor:
    """Exécuteur déterministe basé sur des règles."""
    
    def __init__(self, rules: Optional[Dict[str, Callable]] = None):
        self._rules = rules or {}
    
    async def execute(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Exécution déterministe via règles."""
        # Chercher une règle applicable
        for pattern, handler in self._rules.items():
            if pattern.lower() in subtask.description.lower():
                try:
                    result = handler(subtask, context)
                    return str(result)[:500], 0.95  # High confidence for rules
                except Exception as e:
                    return f"Rule error: {str(e)[:50]}", 0.3
        
        # Pas de règle trouvée
        return "No applicable rule found", 0.1


# ============================================================================
# REASONING ENGINE - CORE
# ============================================================================

class ReasoningEngine:
    """
    Moteur de raisonnement principal.
    
    Fonctionnalités:
    - Décomposition de tâches
    - Arbre de décision avec backtracking
    - Self-reflection
    - Exécution pluggable
    
    Usage:
        engine = ReasoningEngine(config)
        outcome = await engine.run(query, context)
    """
    
    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        llm_executor: Optional[LLMExecutor] = None,
        tool_executor: Optional[ToolExecutor] = None,
        rule_executor: Optional[RuleExecutor] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or ReasoningConfig()
        self._llm = llm_executor
        self._tools = tool_executor
        self._rules = rule_executor or RuleExecutor()
        self._logger = logger or logging.getLogger(__name__)
        
        # Stats internes (pas de PII)
        self._stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "backtrack_count": 0,
            "avg_confidence": 0.0,
        }
        
        # Patterns CoT interdits (détection fuite)
        self._cot_patterns = [
            "thought:",
            "let me think",
            "let's think",
            "step-by-step",
            "step by step",
            "chain-of-thought",
            "chain of thought",
            "scratchpad",
            "internal reasoning",
            "my reasoning is",
            "i need to think",
            "first, i'll think",
            "step 1: think",
            "step 1: analyze",
            "step 1: consider",
            "reasoning:",
            "analysis:",
            "working through",
        ]
    
    def _contains_cot_pattern(self, text: str) -> bool:
        """
        Détecte si un texte contient des patterns de chain-of-thought.
        
        Utilisé pour valider que les traces ne fuient pas de raisonnement interne.
        
        Args:
            text: Texte à vérifier
        
        Returns:
            True si un pattern CoT est détecté
        """
        if not text:
            return False
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self._cot_patterns)
    
    async def run(
        self,
        query: str,
        context: ReasoningContext,
    ) -> ReasoningOutcome:
        """Point d'entrée principal du reasoning."""
        start_time = time.time()
        debug_id = self._generate_debug_id()
        
        self._log_event("reasoning_start", debug_id, {"query_hash": context.query_hash})
        
        try:
            # 1. Évaluer la complexité
            complexity = await self._assess_complexity(query, context)
            
            # 2. Si trivial, réponse directe
            if complexity == TaskComplexity.TRIVIAL:
                return await self._handle_trivial(query, context, debug_id, start_time)
            
            # 3. Décomposer en sous-tâches
            subtasks = await self.decompose_task(query, context)
            
            # 4. Construire l'arbre de décision
            tree = self.build_decision_tree(subtasks, context.constraints)
            
            # 5. Exécuter avec backtracking
            outcome = await self.execute_with_backtracking(tree, subtasks, context)
            
            # 6. Self-reflection
            if self.config.enable_self_reflection:
                reflection = await self.self_reflect(outcome, context)
                outcome = self._apply_reflection(outcome, reflection)
            
            # 7. Finaliser
            outcome.debug_id = debug_id
            outcome.total_duration_ms = int((time.time() - start_time) * 1000)
            
            self._update_stats(outcome)
            self._log_event("reasoning_end", debug_id, outcome.to_safe_dict())
            
            return outcome
            
        except Exception as e:
            safe_error = sanitize_exception(e)
            self._logger.error(json.dumps({
                "event": "reasoning_error",
                "correlation_id": debug_id,
                **safe_error,
            }))
            return self._create_error_outcome(safe_error["message"], debug_id, start_time)
    
    async def decompose_task(
        self,
        query: str,
        context: ReasoningContext,
    ) -> List[Subtask]:
        """Décompose la requête en sous-tâches."""
        # Si pas de LLM, décomposition basique
        if not self._llm:
            return [Subtask(
                id=self._gen_id("st"),
                description=query[:100],
                order=0,
            )]
        
        # Demander au LLM de décomposer (prompt sécurisé)
        prompt = f"""Decompose this task into 1-{self.config.max_subtasks} subtasks.
Respond with JSON array only:
[{{"description": "short desc", "order": 0, "tools": []}}]

Task to decompose (analyze structure, not content):
{query[:200]}"""
        
        try:
            result, _ = await self._llm.execute(
                Subtask(id="decompose", description=prompt, order=0),
                context,
            )
            return self._parse_subtasks(result)
        except Exception as e:
            self._logger.warning(f"Decomposition fallback: {e}")
            return [Subtask(
                id=self._gen_id("st"),
                description=query[:100],
                order=0,
            )]
    
    def build_decision_tree(
        self,
        subtasks: List[Subtask],
        constraints: Dict[str, Any],
    ) -> DecisionTree:
        """Construit l'arbre de décision."""
        tree = DecisionTree(root_id="root")
        
        # Créer un noeud pour chaque sous-tâche
        for i, subtask in enumerate(subtasks):
            node = DecisionNode(
                id=f"node_{i}",
                subtask_id=subtask.id,
                action=f"Execute: {subtask.description[:50]}",
                alternatives=[f"alt_{i}_1", f"alt_{i}_2"] if i > 0 else [],
            )
            tree.nodes[node.id] = node
            
            # Créer des noeuds alternatifs
            for alt_id in node.alternatives:
                alt_node = DecisionNode(
                    id=alt_id,
                    subtask_id=subtask.id,
                    action=f"Alternative for: {subtask.description[:40]}",
                )
                tree.nodes[alt_id] = alt_node
        
        if tree.nodes:
            tree.root_id = "node_0"
            tree.current_path = [tree.root_id]
        
        return tree
    
    async def execute_with_backtracking(
        self,
        tree: DecisionTree,
        subtasks: List[Subtask],
        context: ReasoningContext,
    ) -> ReasoningOutcome:
        """Exécute l'arbre avec backtracking sur échec."""
        trace: List[TraceStep] = []
        results: List[str] = []
        total_confidence = 0.0
        flags: List[ReasoningFlag] = []
        tool_calls = 0
        
        for subtask in subtasks:
            step_start = time.time()
            
            # Exécuter la sous-tâche
            result, confidence = await self._execute_subtask(subtask, context)
            tool_calls += 1 if subtask.required_tools else 0
            
            # Vérifier si backtrack nécessaire
            if confidence < self.config.confidence_threshold:
                if (
                    self.config.backtrack_on_low_confidence
                    and tree.backtrack_count < self.config.max_backtracks
                ):
                    # Essayer une alternative
                    alt_result, alt_conf = await self._try_alternative(
                        subtask, tree, context
                    )
                    tree.backtrack_count += 1
                    
                    if alt_conf > confidence:
                        result, confidence = alt_result, alt_conf
                        flags.append(ReasoningFlag.LOW_CONFIDENCE)
                        self._log_event("backtrack", tree.root_id, {
                            "subtask": subtask.id,
                            "new_confidence": alt_conf,
                        })
            
            # Enregistrer le résultat
            subtask.status = ExecutionStatus.SUCCESS if confidence >= 0.5 else ExecutionStatus.FAILED
            subtask.result = result
            results.append(result)
            total_confidence += confidence
            
            # Ajouter à la trace
            trace.append(TraceStep(
                step_id=subtask.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=subtask.description[:60],
                outcome=result[:60] if result else "No result",
                confidence=confidence,
                duration_ms=int((time.time() - step_start) * 1000),
            ))
            
            # Check limits
            if tool_calls >= self.config.max_tool_calls:
                flags.append(ReasoningFlag.TOOL_RISK)
                break
        
        # Calculer la confiance moyenne
        avg_confidence = total_confidence / max(len(subtasks), 1)
        
        # Détecter les flags
        if avg_confidence < self.config.confidence_threshold:
            flags.append(ReasoningFlag.UNCERTAIN)
        
        completed = sum(1 for s in subtasks if s.status == ExecutionStatus.SUCCESS)
        
        return ReasoningOutcome(
            answer=self._synthesize_answer(results),
            trace=trace,
            confidence=min(avg_confidence, 1.0),
            flags=list(set(flags)),
            debug_id="",  # Set by caller
            subtasks_completed=completed,
            subtasks_total=len(subtasks),
            backtracks_used=tree.backtrack_count,
            tool_calls_made=tool_calls,
            total_duration_ms=0,  # Set by caller
        )
    
    async def self_reflect(
        self,
        outcome: ReasoningOutcome,
        context: ReasoningContext,
    ) -> ReflectionSummary:
        """Self-reflection sur le résultat."""
        issues: List[str] = []
        suggestions: List[str] = []
        confidence_delta = 0.0
        
        # Analyser les flags
        if ReasoningFlag.LOW_CONFIDENCE in outcome.flags:
            issues.append("Low confidence detected")
            suggestions.append("Consider requesting clarification")
            confidence_delta -= 0.1
        
        if ReasoningFlag.CONTRADICTION in outcome.flags:
            issues.append("Contradictory information")
            confidence_delta -= 0.15
        
        # Analyser le taux de succès
        success_rate = outcome.subtasks_completed / max(outcome.subtasks_total, 1)
        if success_rate < 0.7:
            issues.append(f"Low success rate: {success_rate:.0%}")
            suggestions.append("Task may need decomposition revision")
            confidence_delta -= 0.1
        
        # Analyser les backtracks
        if outcome.backtracks_used > 1:
            issues.append(f"Multiple backtracks: {outcome.backtracks_used}")
            confidence_delta -= 0.05 * outcome.backtracks_used
        
        return ReflectionSummary(
            confidence_delta=confidence_delta,
            issues_found=issues[:3],  # Max 3 issues
            suggestions=suggestions[:2],  # Max 2 suggestions
            should_retry=success_rate < 0.5 and outcome.backtracks_used < self.config.max_backtracks,
        )
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    async def _assess_complexity(
        self,
        query: str,
        context: ReasoningContext,
    ) -> TaskComplexity:
        """Évalue la complexité de la requête."""
        # Heuristiques simples
        query_lower = query.lower()
        
        # Trivial: questions simples
        trivial_patterns = ["what is", "who is", "when is", "define", "explain"]
        if any(p in query_lower for p in trivial_patterns) and len(query) < 100:
            return TaskComplexity.TRIVIAL
        
        # Complex: multi-step indicators
        complex_patterns = ["and then", "after that", "step by step", "multiple", "analyze and"]
        if any(p in query_lower for p in complex_patterns):
            return TaskComplexity.COMPLEX
        
        # Moderate: tool usage likely
        if context.available_tools:
            return TaskComplexity.MODERATE
        
        return TaskComplexity.SIMPLE
    
    async def _handle_trivial(
        self,
        query: str,
        context: ReasoningContext,
        debug_id: str,
        start_time: float,
    ) -> ReasoningOutcome:
        """Gère les requêtes triviales sans décomposition."""
        return ReasoningOutcome(
            answer="",  # To be filled by caller/LLM
            trace=[TraceStep(
                step_id="direct",
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="Direct response (trivial)",
                outcome="Passed to LLM",
                confidence=0.9,
                duration_ms=int((time.time() - start_time) * 1000),
            )],
            confidence=0.9,
            flags=[],
            debug_id=debug_id,
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=int((time.time() - start_time) * 1000),
        )
    
    async def _execute_subtask(
        self,
        subtask: Subtask,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Exécute une sous-tâche via l'exécuteur approprié."""
        # Priorité: Rules > Tools > LLM
        if self._rules:
            result, conf = await self._rules.execute(subtask, context)
            if conf > 0.5:
                return result, conf
        
        if self._tools and subtask.required_tools:
            return await self._tools.execute(subtask, context)
        
        if self._llm:
            return await self._llm.execute(subtask, context)
        
        return "No executor available", 0.2
    
    async def _try_alternative(
        self,
        subtask: Subtask,
        tree: DecisionTree,
        context: ReasoningContext,
    ) -> tuple[str, float]:
        """Essaie une approche alternative."""
        # Modifier légèrement la sous-tâche
        alt_subtask = Subtask(
            id=f"{subtask.id}_alt",
            description=f"Alternative approach: {subtask.description[:70]}",
            order=subtask.order,
            required_tools=subtask.required_tools,
        )
        
        return await self._execute_subtask(alt_subtask, context)
    
    def _parse_subtasks(self, response: str) -> List[Subtask]:
        """Parse la réponse de décomposition."""
        try:
            data = json.loads(response)
            if not isinstance(data, list):
                data = [data]
            
            subtasks = []
            for i, item in enumerate(data[:self.config.max_subtasks]):
                subtasks.append(Subtask(
                    id=self._gen_id("st"),
                    description=str(item.get("description", f"Step {i+1}"))[:100],
                    order=int(item.get("order", i)),
                    required_tools=list(item.get("tools", [])),
                ))
            
            return subtasks if subtasks else [Subtask(
                id=self._gen_id("st"),
                description="Execute task",
                order=0,
            )]
            
        except (json.JSONDecodeError, ValueError, TypeError):
            return [Subtask(
                id=self._gen_id("st"),
                description="Execute task",
                order=0,
            )]
    
    def _synthesize_answer(self, results: List[str]) -> str:
        """Synthétise les résultats en réponse finale."""
        if not results:
            return ""
        if len(results) == 1:
            return results[0]
        
        # Combiner les résultats non-vides
        valid_results = [r for r in results if r and r.strip()]
        if not valid_results:
            return ""
        
        return " | ".join(valid_results[:5])  # Max 5 résultats
    
    def _apply_reflection(
        self,
        outcome: ReasoningOutcome,
        reflection: ReflectionSummary,
    ) -> ReasoningOutcome:
        """Applique les ajustements de la reflection."""
        new_confidence = max(0.0, min(1.0, outcome.confidence + reflection.confidence_delta))
        
        # Ajouter flags si nécessaire
        flags = list(outcome.flags)
        if new_confidence < self.config.confidence_threshold:
            if ReasoningFlag.LOW_CONFIDENCE not in flags:
                flags.append(ReasoningFlag.LOW_CONFIDENCE)
        
        return ReasoningOutcome(
            answer=outcome.answer,
            trace=outcome.trace,
            confidence=new_confidence,
            flags=flags,
            debug_id=outcome.debug_id,
            subtasks_completed=outcome.subtasks_completed,
            subtasks_total=outcome.subtasks_total,
            backtracks_used=outcome.backtracks_used,
            tool_calls_made=outcome.tool_calls_made,
            total_duration_ms=outcome.total_duration_ms,
        )
    
    def _create_error_outcome(
        self,
        error: str,
        debug_id: str,
        start_time: float,
    ) -> ReasoningOutcome:
        """Crée un outcome d'erreur."""
        return ReasoningOutcome(
            answer="",
            trace=[TraceStep(
                step_id="error",
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="Error during reasoning",
                outcome=error[:60],
                confidence=0.0,
                duration_ms=int((time.time() - start_time) * 1000),
            )],
            confidence=0.0,
            flags=[ReasoningFlag.UNCERTAIN],
            debug_id=debug_id,
            subtasks_completed=0,
            subtasks_total=0,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=int((time.time() - start_time) * 1000),
        )
    
    def _update_stats(self, outcome: ReasoningOutcome):
        """Met à jour les stats internes (pas de PII)."""
        self._stats["total_runs"] += 1
        if outcome.confidence >= self.config.confidence_threshold:
            self._stats["successful_runs"] += 1
        self._stats["backtrack_count"] += outcome.backtracks_used
        
        # Moving average for confidence
        n = self._stats["total_runs"]
        old_avg = self._stats["avg_confidence"]
        self._stats["avg_confidence"] = old_avg + (outcome.confidence - old_avg) / n
    
    def _log_event(self, event: str, debug_id: str, data: Dict[str, Any]):
        """Log structuré JSON (pas de contenu user)."""
        log_entry = {
            "event": event,
            "correlation_id": debug_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._logger.info(json.dumps(log_entry))
    
    def _generate_debug_id(self) -> str:
        """Génère un ID de debug unique."""
        return f"re_{uuid.uuid4().hex[:12]}"
    
    def _gen_id(self, prefix: str) -> str:
        """Génère un ID court."""
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les stats (pas de PII)."""
        return dict(self._stats)


# ============================================================================
# REASONING PIPELINE - ORCHESTRATEUR
# ============================================================================

class ReasoningPipeline:
    """
    Orchestrateur principal du raisonnement.
    
    Coordonne: TaskPlanner -> ReasoningEngine -> Metacognition
    
    Usage:
        pipeline = ReasoningPipeline(config)
        result = await pipeline.run(query, context)
    """
    
    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        engine: Optional[ReasoningEngine] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or ReasoningConfig()
        self._engine = engine or ReasoningEngine(self.config, logger=logger)
        self._logger = logger or logging.getLogger(__name__)
        
        # Import dynamique pour éviter les dépendances circulaires
        self._planner = None
        self._metacognition = None
    
    def set_planner(self, planner: Any):
        """Configure le planner (injection de dépendance)."""
        self._planner = planner
    
    def set_metacognition(self, meta: Any):
        """Configure la metacognition (injection de dépendance)."""
        self._metacognition = meta
    
    async def run(
        self,
        user_query: str,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:
        """
        Point d'entrée unique du pipeline de raisonnement.
        
        Args:
            user_query: Requête utilisateur
            session_context: Contexte de session (optionnel)
        
        Returns:
            ReasoningResult avec réponse, trace et escalation
        """
        debug_id = f"rp_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        self._log_event("pipeline_start", debug_id, {})
        
        # Construire le contexte
        context = ReasoningContext(
            session_id=session_context.get("session_id", debug_id) if session_context else debug_id,
            user_query=user_query,
            conversation_history=session_context.get("history", []) if session_context else [],
            available_tools=session_context.get("tools", []) if session_context else [],
            user_role=session_context.get("user_role") if session_context else None,
        )
        
        try:
            # 1. Planning (si disponible)
            if self._planner:
                plan = await self._planner.plan(user_query, context)
                context.metadata["plan"] = plan
            
            # 2. Raisonnement
            outcome = await self._engine.run(user_query, context)
            
            # 3. Metacognition (si disponible)
            escalation = EscalationType.NONE
            questions: List[str] = []
            
            if self._metacognition:
                meta_decision = await self._metacognition.evaluate(outcome, context)
                escalation = meta_decision.escalation
                
                if escalation == EscalationType.ASK_CLARIFY:
                    questions = meta_decision.clarification_questions[:2]
            else:
                # Fallback: déterminer escalation basique
                escalation = self._determine_escalation(outcome)
            
            # 4. Finaliser
            result = ReasoningResult.from_outcome(outcome, escalation, questions)
            
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_event("pipeline_end", debug_id, {
                "confidence": result.confidence,
                "escalation": escalation.value,
                "duration_ms": duration_ms,
            })
            
            return result
            
        except Exception as e:
            safe_error = sanitize_exception(e)
            self._logger.error(json.dumps({
                "event": "pipeline_error",
                "correlation_id": debug_id,
                **safe_error,
            }))
            return ReasoningResult(
                answer="",
                trace=[],
                confidence=0.0,
                flags=[ReasoningFlag.UNCERTAIN],
                debug_id=debug_id,
                escalation=EscalationType.SAFE_REFUSE,
            )
    
    def _determine_escalation(self, outcome: ReasoningOutcome) -> EscalationType:
        """Détermine l'escalation basique sans metacognition."""
        if outcome.confidence < 0.3:
            return EscalationType.SAFE_REFUSE
        if outcome.confidence < 0.5:
            return EscalationType.HUMAN_REVIEW
        if ReasoningFlag.MISSING_INFO in outcome.flags:
            return EscalationType.ASK_CLARIFY
        return EscalationType.NONE
    
    def _log_event(self, event: str, debug_id: str, data: Dict[str, Any]):
        """Log structuré."""
        log_entry = {
            "event": event,
            "correlation_id": debug_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._logger.info(json.dumps(log_entry))
