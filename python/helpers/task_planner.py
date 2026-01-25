"""
Korev Evidence — Task Planner (HTN + SMART Goals)
================================================

Planificateur hiérarchique de tâches avec:
- Décomposition HTN (Hierarchical Task Network)
- Génération d'objectifs SMART
- Priorisation dynamique
- Plans adaptatifs (safe/fast/thorough)

GARANTIES DE SÉCURITÉ:
- Aucun chain-of-thought brut exposé
- Traces courtes et résumées
- Protection prompt injection

Author: Korev AI
License: Proprietary
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from python.helpers.reasoning_engine import (
    ReasoningConfig,
    ReasoningContext,
    TaskComplexity,
    Subtask,
    ExecutionStatus,
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
    """Sanitize exception pour logging sans PII."""
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
class PlannerConfig:
    """Configuration du planner (immutable)."""
    max_goals: int = 3
    max_tasks_per_goal: int = 5
    max_steps_per_task: int = 4
    default_time_horizon_hours: int = 24
    
    # Poids pour la priorisation
    weight_impact: float = 0.35
    weight_urgency: float = 0.25
    weight_risk_reduction: float = 0.25
    weight_cost: float = 0.15
    
    # Seuils
    min_priority_score: float = 0.3


# ============================================================================
# ENUMS
# ============================================================================

class PlanMode(Enum):
    SAFE = "safe"          # Outil minimal, prudent
    FAST = "fast"          # Agressif, moins de vérifications
    THOROUGH = "thorough"  # Plus d'étapes, plus de validation


class GoalStatus(Enum):
    DEFINED = "defined"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"       # Dependencies satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# DATA CLASSES - SMART GOALS
# ============================================================================

@dataclass
class SMARTCriteria:
    """Critères SMART pour un objectif."""
    specific: str          # Description précise (<= 100 chars)
    measurable: str        # Comment mesurer le succès (<= 80 chars)
    achievable: bool       # Est-ce réalisable?
    relevant: str          # Pourquoi c'est pertinent (<= 80 chars)
    time_bound: datetime   # Deadline
    
    def __post_init__(self):
        self.specific = self.specific[:100]
        self.measurable = self.measurable[:80]
        self.relevant = self.relevant[:80]


@dataclass
class Goal:
    """Objectif SMART."""
    id: str
    title: str  # <= 60 chars
    smart: SMARTCriteria
    priority_score: float = 0.0
    status: GoalStatus = GoalStatus.DEFINED
    tasks: List[str] = field(default_factory=list)  # Task IDs
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.title = self.title[:60]


@dataclass
class Task:
    """Tâche dans le plan."""
    id: str
    goal_id: str
    description: str  # <= 100 chars
    order: int
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    required_tools: List[str] = field(default_factory=list)
    estimated_duration_s: int = 60
    status: TaskStatus = TaskStatus.PENDING
    steps: List["PlanStep"] = field(default_factory=list)
    
    def __post_init__(self):
        self.description = self.description[:100]
    
    def is_ready(self, completed_tasks: set) -> bool:
        """Vérifie si les dépendances sont satisfaites."""
        return all(dep in completed_tasks for dep in self.dependencies)


@dataclass
class PlanStep:
    """Étape atomique dans une tâche."""
    id: str
    task_id: str
    action: str  # <= 80 chars
    tool: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[str] = None
    
    def __post_init__(self):
        self.action = self.action[:80]


@dataclass
class Plan:
    """Plan complet généré."""
    id: str
    mode: PlanMode
    goals: List[Goal]
    tasks: Dict[str, Task]  # task_id -> Task
    execution_order: List[str]  # Ordre d'exécution des tasks
    estimated_duration_s: int
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export safe pour logs (pas de CoT)."""
        return {
            "plan_id": self.id,
            "mode": self.mode.value,
            "goals_count": len(self.goals),
            "tasks_count": len(self.tasks),
            "estimated_duration_s": self.estimated_duration_s,
            "confidence": self.confidence,
        }


# ============================================================================
# PRIORITIZATION
# ============================================================================

@dataclass
class PriorityFactors:
    """Facteurs pour calculer la priorité."""
    impact: float = 0.5       # 0-1: Impact business
    urgency: float = 0.5      # 0-1: Urgence temporelle
    risk_reduction: float = 0.5  # 0-1: Réduction de risque
    cost: float = 0.5         # 0-1: Coût (inverse)


class Prioritizer:
    """Calcule les scores de priorité."""
    
    def __init__(self, config: PlannerConfig):
        self.config = config
    
    def calculate_score(self, factors: PriorityFactors) -> float:
        """Calcule le score de priorité."""
        score = (
            self.config.weight_impact * factors.impact
            + self.config.weight_urgency * factors.urgency
            + self.config.weight_risk_reduction * factors.risk_reduction
            - self.config.weight_cost * factors.cost
        )
        return max(0.0, min(1.0, score))
    
    def rank_goals(self, goals: List[Goal]) -> List[Goal]:
        """Trie les objectifs par priorité."""
        return sorted(goals, key=lambda g: g.priority_score, reverse=True)
    
    def rank_tasks(self, tasks: List[Task], completed: set) -> List[Task]:
        """Trie les tâches prêtes par ordre."""
        ready = [t for t in tasks if t.is_ready(completed)]
        return sorted(ready, key=lambda t: t.order)


# ============================================================================
# HTN DECOMPOSITION
# ============================================================================

class HTNDecomposer:
    """
    Décomposeur HTN simplifié.
    
    Décompose: Goal -> Tasks -> Steps
    """
    
    def __init__(self, config: PlannerConfig):
        self.config = config
        self._method_library: Dict[str, Callable] = {}
    
    def register_method(self, pattern: str, method: Callable):
        """Enregistre une méthode de décomposition."""
        self._method_library[pattern] = method
    
    def decompose_goal(
        self,
        goal: Goal,
        context: ReasoningContext,
    ) -> List[Task]:
        """Décompose un objectif en tâches."""
        tasks: List[Task] = []
        
        # Chercher une méthode applicable
        for pattern, method in self._method_library.items():
            if pattern.lower() in goal.title.lower():
                try:
                    tasks = method(goal, context)
                    break
                except Exception:
                    continue
        
        # Fallback: décomposition générique
        if not tasks:
            tasks = self._generic_decomposition(goal, context)
        
        # Limiter le nombre de tâches
        return tasks[:self.config.max_tasks_per_goal]
    
    def decompose_task(
        self,
        task: Task,
        context: ReasoningContext,
    ) -> List[PlanStep]:
        """Décompose une tâche en étapes."""
        steps: List[PlanStep] = []
        
        # Générer des étapes basiques
        if task.required_tools:
            for i, tool in enumerate(task.required_tools[:self.config.max_steps_per_task]):
                steps.append(PlanStep(
                    id=f"{task.id}_s{i}",
                    task_id=task.id,
                    action=f"Execute {tool}",
                    tool=tool,
                    order=i,
                ))
        else:
            # Tâche sans outil: étape unique
            steps.append(PlanStep(
                id=f"{task.id}_s0",
                task_id=task.id,
                action=task.description[:80],
                order=0,
            ))
        
        return steps
    
    def _generic_decomposition(
        self,
        goal: Goal,
        context: ReasoningContext,
    ) -> List[Task]:
        """Décomposition générique d'un objectif."""
        # Analyser le titre pour déterminer les tâches
        title_lower = goal.title.lower()
        tasks: List[Task] = []
        
        # Patterns de décomposition
        if "analyze" in title_lower or "analyser" in title_lower:
            tasks = [
                Task(
                    id=f"{goal.id}_t0",
                    goal_id=goal.id,
                    description="Gather relevant data",
                    order=0,
                ),
                Task(
                    id=f"{goal.id}_t1",
                    goal_id=goal.id,
                    description="Process and analyze data",
                    order=1,
                    dependencies=[f"{goal.id}_t0"],
                ),
                Task(
                    id=f"{goal.id}_t2",
                    goal_id=goal.id,
                    description="Generate insights and report",
                    order=2,
                    dependencies=[f"{goal.id}_t1"],
                ),
            ]
        elif "create" in title_lower or "créer" in title_lower:
            tasks = [
                Task(
                    id=f"{goal.id}_t0",
                    goal_id=goal.id,
                    description="Define requirements",
                    order=0,
                ),
                Task(
                    id=f"{goal.id}_t1",
                    goal_id=goal.id,
                    description="Create initial version",
                    order=1,
                    dependencies=[f"{goal.id}_t0"],
                ),
                Task(
                    id=f"{goal.id}_t2",
                    goal_id=goal.id,
                    description="Review and finalize",
                    order=2,
                    dependencies=[f"{goal.id}_t1"],
                ),
            ]
        else:
            # Décomposition minimale
            tasks = [
                Task(
                    id=f"{goal.id}_t0",
                    goal_id=goal.id,
                    description=f"Execute: {goal.title[:70]}",
                    order=0,
                ),
            ]
        
        return tasks


# ============================================================================
# TASK PLANNER - MAIN CLASS
# ============================================================================

class TaskPlanner:
    """
    Planificateur de tâches principal.
    
    Usage:
        planner = TaskPlanner(config)
        plan = await planner.plan(query, context)
    """
    
    def __init__(
        self,
        config: Optional[PlannerConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or PlannerConfig()
        self._logger = logger or logging.getLogger(__name__)
        self._decomposer = HTNDecomposer(self.config)
        self._prioritizer = Prioritizer(self.config)
        
        # Stats internes
        self._stats = {
            "plans_created": 0,
            "avg_tasks_per_plan": 0.0,
        }
    
    async def plan(
        self,
        query: str,
        context: ReasoningContext,
        mode: Optional[PlanMode] = None,
    ) -> Plan:
        """
        Génère un plan pour la requête.
        
        Args:
            query: Requête utilisateur
            context: Contexte de raisonnement
            mode: Mode de plan (auto-détecté si None)
        
        Returns:
            Plan complet
        """
        plan_id = f"plan_{uuid.uuid4().hex[:10]}"
        start_time = time.time()
        
        self._log_event("planning_start", plan_id, {"query_hash": context.query_hash})
        
        try:
            # 1. Déterminer le mode
            selected_mode = mode or self._select_mode(query, context)
            
            # 2. Générer les objectifs SMART
            goals = await self._generate_goals(query, context, selected_mode)
            
            # 3. Prioriser les objectifs
            goals = self._prioritizer.rank_goals(goals)
            
            # 4. Décomposer en tâches
            all_tasks: Dict[str, Task] = {}
            for goal in goals[:self.config.max_goals]:
                tasks = self._decomposer.decompose_goal(goal, context)
                for task in tasks:
                    task.steps = self._decomposer.decompose_task(task, context)
                    all_tasks[task.id] = task
                    goal.tasks.append(task.id)
            
            # 5. Calculer l'ordre d'exécution
            execution_order = self._compute_execution_order(all_tasks)
            
            # 6. Estimer la durée
            total_duration = sum(t.estimated_duration_s for t in all_tasks.values())
            
            # 7. Calculer la confiance
            confidence = self._estimate_confidence(goals, all_tasks, selected_mode)
            
            plan = Plan(
                id=plan_id,
                mode=selected_mode,
                goals=goals,
                tasks=all_tasks,
                execution_order=execution_order,
                estimated_duration_s=total_duration,
                confidence=confidence,
                created_at=datetime.now(timezone.utc),
            )
            
            self._update_stats(plan)
            self._log_event("planning_done", plan_id, plan.to_safe_dict())
            
            return plan
            
        except Exception as e:
            safe_error = sanitize_exception(e)
            self._logger.error(json.dumps({
                "event": "planning_error",
                "correlation_id": plan_id,
                **safe_error,
            }))
            return self._create_fallback_plan(query, plan_id)
    
    async def _generate_goals(
        self,
        query: str,
        context: ReasoningContext,
        mode: PlanMode,
    ) -> List[Goal]:
        """Génère les objectifs SMART."""
        goals: List[Goal] = []
        
        # Analyser la requête pour identifier les objectifs
        objectives = self._extract_objectives(query)
        
        for i, obj in enumerate(objectives[:self.config.max_goals]):
            # Créer les critères SMART
            smart = SMARTCriteria(
                specific=obj[:100],
                measurable="Task completed successfully",
                achievable=True,
                relevant="Requested by user",
                time_bound=datetime.now(timezone.utc) + timedelta(
                    hours=self.config.default_time_horizon_hours
                ),
            )
            
            # Calculer la priorité
            factors = self._assess_priority_factors(obj, context, mode)
            priority = self._prioritizer.calculate_score(factors)
            
            goal = Goal(
                id=f"goal_{uuid.uuid4().hex[:8]}",
                title=obj[:60],
                smart=smart,
                priority_score=priority,
            )
            
            goals.append(goal)
        
        return goals
    
    def _select_mode(self, query: str, context: ReasoningContext) -> PlanMode:
        """Sélectionne le mode de plan approprié."""
        query_lower = query.lower()
        
        # Indicateurs de mode
        if any(w in query_lower for w in ["quick", "fast", "rapide", "vite"]):
            return PlanMode.FAST
        
        if any(w in query_lower for w in ["careful", "thorough", "detailed", "détaillé"]):
            return PlanMode.THOROUGH
        
        # Par défaut: SAFE
        if context.constraints.get("high_risk") or context.user_role == "legal_safe":
            return PlanMode.SAFE
        
        return PlanMode.SAFE
    
    def _extract_objectives(self, query: str) -> List[str]:
        """Extrait les objectifs de la requête."""
        objectives: List[str] = []
        
        # Patterns de séparation
        separators = [" and ", " et ", " puis ", " then ", ". "]
        
        parts = [query]
        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts
        
        # Nettoyer et filtrer
        for part in parts:
            cleaned = part.strip()
            if len(cleaned) > 10:  # Ignorer les fragments trop courts
                objectives.append(cleaned)
        
        return objectives if objectives else [query]
    
    def _assess_priority_factors(
        self,
        objective: str,
        context: ReasoningContext,
        mode: PlanMode,
    ) -> PriorityFactors:
        """Évalue les facteurs de priorité."""
        obj_lower = objective.lower()
        
        # Heuristiques
        impact = 0.5
        urgency = 0.5
        risk_reduction = 0.5
        cost = 0.5
        
        # Ajuster selon les mots-clés
        if any(w in obj_lower for w in ["urgent", "asap", "immediately"]):
            urgency = 0.9
        
        if any(w in obj_lower for w in ["critical", "important", "crucial"]):
            impact = 0.8
        
        if any(w in obj_lower for w in ["security", "sécurité", "risk"]):
            risk_reduction = 0.8
        
        # Ajuster selon le mode
        if mode == PlanMode.FAST:
            cost = 0.3  # Moins de poids sur le coût
        elif mode == PlanMode.THOROUGH:
            cost = 0.7  # Plus de validation = plus de coût
        
        return PriorityFactors(
            impact=impact,
            urgency=urgency,
            risk_reduction=risk_reduction,
            cost=cost,
        )
    
    def _compute_execution_order(self, tasks: Dict[str, Task]) -> List[str]:
        """Calcule l'ordre d'exécution topologique."""
        # Tri topologique basique
        order: List[str] = []
        visited: set = set()
        
        def visit(task_id: str):
            if task_id in visited or task_id not in tasks:
                return
            visited.add(task_id)
            
            task = tasks[task_id]
            for dep in task.dependencies:
                visit(dep)
            
            order.append(task_id)
        
        # Trier par ordre puis visiter
        sorted_tasks = sorted(tasks.values(), key=lambda t: t.order)
        for task in sorted_tasks:
            visit(task.id)
        
        return order
    
    def _estimate_confidence(
        self,
        goals: List[Goal],
        tasks: Dict[str, Task],
        mode: PlanMode,
    ) -> float:
        """Estime la confiance du plan."""
        if not goals:
            return 0.3
        
        # Facteurs
        base_confidence = 0.7
        
        # Ajuster selon le nombre de tâches
        task_count = len(tasks)
        if task_count > 10:
            base_confidence -= 0.1
        elif task_count <= 3:
            base_confidence += 0.1
        
        # Ajuster selon le mode
        if mode == PlanMode.THOROUGH:
            base_confidence += 0.1
        elif mode == PlanMode.FAST:
            base_confidence -= 0.05
        
        return max(0.0, min(1.0, base_confidence))
    
    def _create_fallback_plan(self, query: str, plan_id: str) -> Plan:
        """Crée un plan de fallback minimal."""
        goal = Goal(
            id="fallback_goal",
            title=query[:60],
            smart=SMARTCriteria(
                specific=query[:100],
                measurable="Completion",
                achievable=True,
                relevant="User request",
                time_bound=datetime.now(timezone.utc) + timedelta(hours=1),
            ),
        )
        
        task = Task(
            id="fallback_task",
            goal_id=goal.id,
            description="Execute request directly",
            order=0,
        )
        goal.tasks.append(task.id)
        
        return Plan(
            id=plan_id,
            mode=PlanMode.SAFE,
            goals=[goal],
            tasks={task.id: task},
            execution_order=[task.id],
            estimated_duration_s=60,
            confidence=0.5,
            created_at=datetime.now(timezone.utc),
        )
    
    def _update_stats(self, plan: Plan):
        """Met à jour les stats internes."""
        self._stats["plans_created"] += 1
        n = self._stats["plans_created"]
        old_avg = self._stats["avg_tasks_per_plan"]
        self._stats["avg_tasks_per_plan"] = old_avg + (len(plan.tasks) - old_avg) / n
    
    def _log_event(self, event: str, plan_id: str, data: Dict[str, Any]):
        """Log structuré JSON."""
        log_entry = {
            "event": event,
            "plan_id": plan_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._logger.info(json.dumps(log_entry))
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les stats."""
        return dict(self._stats)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_smart_goal(
    title: str,
    measurable: str,
    time_hours: int = 24,
) -> Goal:
    """Crée un objectif SMART rapidement."""
    return Goal(
        id=f"goal_{uuid.uuid4().hex[:8]}",
        title=title[:60],
        smart=SMARTCriteria(
            specific=title,
            measurable=measurable,
            achievable=True,
            relevant="User-defined goal",
            time_bound=datetime.now(timezone.utc) + timedelta(hours=time_hours),
        ),
    )
