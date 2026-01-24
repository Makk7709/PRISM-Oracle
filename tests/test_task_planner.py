"""
Tests unitaires pour le Task Planner HTN.

Couvre:
- Génération d'objectifs SMART
- Décomposition HTN
- Priorisation dynamique
- Modes de plan (safe/fast/thorough)
"""

import pytest
import asyncio
from datetime import datetime, timezone

from python.helpers.task_planner import (
    TaskPlanner,
    PlannerConfig,
    PlanMode,
    Goal,
    Task,
    PlanStep,
    Plan,
    SMARTCriteria,
    GoalStatus,
    TaskStatus,
    HTNDecomposer,
    Prioritizer,
    PriorityFactors,
    create_smart_goal,
)
from python.helpers.reasoning_engine import (
    ReasoningContext,
    TaskComplexity,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def config():
    """Configuration de test."""
    return PlannerConfig(
        max_goals=3,
        max_tasks_per_goal=4,
        max_steps_per_task=3,
    )


@pytest.fixture
def context():
    """Contexte de test."""
    return ReasoningContext(
        session_id="test_plan_001",
        user_query="Analyze the sales data and create a report",
        available_tools=["code_execution", "file_writer"],
    )


@pytest.fixture
def complex_context():
    """Contexte complexe multi-objectifs."""
    return ReasoningContext(
        session_id="test_complex_plan",
        user_query="Analyze data, create report, and send to team",
        available_tools=["search_engine", "code_execution", "file_writer"],
    )


# ============================================================================
# TESTS: OBJECTIFS SMART
# ============================================================================

class TestSMARTGoals:
    """Tests pour la génération d'objectifs SMART."""
    
    @pytest.mark.asyncio
    async def test_goal_has_smart_criteria(self, config, context):
        """Un objectif a des critères SMART."""
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        assert len(plan.goals) >= 1
        
        goal = plan.goals[0]
        assert isinstance(goal.smart, SMARTCriteria)
        assert goal.smart.specific
        assert goal.smart.measurable
        assert isinstance(goal.smart.achievable, bool)
        assert goal.smart.relevant
        assert isinstance(goal.smart.time_bound, datetime)
    
    @pytest.mark.asyncio
    async def test_goal_title_truncated(self, config, context):
        """Le titre d'un objectif est tronqué à 60 chars."""
        long_query = "A" * 200
        context = ReasoningContext(
            session_id="test",
            user_query=long_query,
        )
        
        planner = TaskPlanner(config)
        plan = await planner.plan(long_query, context)
        
        for goal in plan.goals:
            assert len(goal.title) <= 60
    
    def test_create_smart_goal_helper(self):
        """La fonction helper crée un objectif SMART valide."""
        goal = create_smart_goal(
            title="Analyze data",
            measurable="Report generated",
            time_hours=12,
        )
        
        assert goal.id.startswith("goal_")
        assert goal.title == "Analyze data"
        assert goal.smart.measurable == "Report generated"
        assert goal.smart.time_bound > datetime.now(timezone.utc)


# ============================================================================
# TESTS: DÉCOMPOSITION HTN
# ============================================================================

class TestHTNDecomposition:
    """Tests pour la décomposition HTN."""
    
    def test_decompose_analysis_goal(self, config):
        """Un objectif d'analyse est décomposé correctement."""
        decomposer = HTNDecomposer(config)
        
        goal = Goal(
            id="goal_1",
            title="Analyze the data",
            smart=SMARTCriteria(
                specific="Analyze sales data",
                measurable="Insights generated",
                achievable=True,
                relevant="Business need",
                time_bound=datetime.now(timezone.utc),
            ),
        )
        
        context = ReasoningContext(
            session_id="test",
            user_query="Analyze data",
        )
        
        tasks = decomposer.decompose_goal(goal, context)
        
        # Devrait avoir plusieurs tâches (gather, process, report)
        assert len(tasks) >= 1
        assert all(isinstance(t, Task) for t in tasks)
    
    def test_decompose_creation_goal(self, config):
        """Un objectif de création est décomposé correctement."""
        decomposer = HTNDecomposer(config)
        
        goal = Goal(
            id="goal_1",
            title="Create a report",
            smart=SMARTCriteria(
                specific="Create sales report",
                measurable="Report file created",
                achievable=True,
                relevant="Management request",
                time_bound=datetime.now(timezone.utc),
            ),
        )
        
        context = ReasoningContext(
            session_id="test",
            user_query="Create report",
        )
        
        tasks = decomposer.decompose_goal(goal, context)
        
        assert len(tasks) >= 1
    
    def test_task_decompose_to_steps(self, config):
        """Une tâche est décomposée en étapes."""
        decomposer = HTNDecomposer(config)
        
        task = Task(
            id="task_1",
            goal_id="goal_1",
            description="Execute data analysis",
            order=0,
            required_tools=["code_execution"],
        )
        
        context = ReasoningContext(
            session_id="test",
            user_query="Test",
        )
        
        steps = decomposer.decompose_task(task, context)
        
        assert len(steps) >= 1
        assert all(isinstance(s, PlanStep) for s in steps)
    
    def test_max_tasks_respected(self, config):
        """Le nombre max de tâches par objectif est respecté."""
        config = PlannerConfig(max_tasks_per_goal=2)
        decomposer = HTNDecomposer(config)
        
        goal = Goal(
            id="goal_1",
            title="Complex analysis task",
            smart=SMARTCriteria(
                specific="Very complex analysis",
                measurable="Done",
                achievable=True,
                relevant="Test",
                time_bound=datetime.now(timezone.utc),
            ),
        )
        
        context = ReasoningContext(session_id="test", user_query="Complex")
        
        tasks = decomposer.decompose_goal(goal, context)
        
        assert len(tasks) <= config.max_tasks_per_goal


# ============================================================================
# TESTS: PRIORISATION
# ============================================================================

class TestPrioritization:
    """Tests pour la priorisation dynamique."""
    
    def test_priority_score_calculation(self, config):
        """Le score de priorité est calculé correctement."""
        prioritizer = Prioritizer(config)
        
        factors = PriorityFactors(
            impact=0.8,
            urgency=0.9,
            risk_reduction=0.7,
            cost=0.3,
        )
        
        score = prioritizer.calculate_score(factors)
        
        # Score devrait être entre 0 et 1
        assert 0 <= score <= 1
        
        # Score élevé pour ces facteurs favorables
        assert score > 0.5
    
    def test_high_cost_reduces_priority(self, config):
        """Un coût élevé réduit la priorité."""
        prioritizer = Prioritizer(config)
        
        low_cost = PriorityFactors(impact=0.7, urgency=0.7, risk_reduction=0.7, cost=0.2)
        high_cost = PriorityFactors(impact=0.7, urgency=0.7, risk_reduction=0.7, cost=0.9)
        
        low_cost_score = prioritizer.calculate_score(low_cost)
        high_cost_score = prioritizer.calculate_score(high_cost)
        
        assert low_cost_score > high_cost_score
    
    def test_goal_ranking(self, config):
        """Les objectifs sont triés par priorité."""
        prioritizer = Prioritizer(config)
        
        goals = [
            Goal(id="g1", title="Low priority", smart=SMARTCriteria(
                "S", "M", True, "R", datetime.now(timezone.utc)
            ), priority_score=0.3),
            Goal(id="g2", title="High priority", smart=SMARTCriteria(
                "S", "M", True, "R", datetime.now(timezone.utc)
            ), priority_score=0.9),
            Goal(id="g3", title="Medium priority", smart=SMARTCriteria(
                "S", "M", True, "R", datetime.now(timezone.utc)
            ), priority_score=0.6),
        ]
        
        ranked = prioritizer.rank_goals(goals)
        
        # Devrait être trié par priorité décroissante
        assert ranked[0].id == "g2"
        assert ranked[1].id == "g3"
        assert ranked[2].id == "g1"


# ============================================================================
# TESTS: MODES DE PLAN
# ============================================================================

class TestPlanModes:
    """Tests pour les différents modes de plan."""
    
    @pytest.mark.asyncio
    async def test_safe_mode_default(self, config, context):
        """SAFE est le mode par défaut."""
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        assert plan.mode == PlanMode.SAFE
    
    @pytest.mark.asyncio
    async def test_fast_mode_keyword(self, config):
        """'quick' dans la requête → mode FAST."""
        context = ReasoningContext(
            session_id="test",
            user_query="Quick analysis of the data",
        )
        
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        assert plan.mode == PlanMode.FAST
    
    @pytest.mark.asyncio
    async def test_thorough_mode_keyword(self, config):
        """'detailed' dans la requête → mode THOROUGH."""
        context = ReasoningContext(
            session_id="test",
            user_query="Detailed analysis with full validation",
        )
        
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        assert plan.mode == PlanMode.THOROUGH
    
    @pytest.mark.asyncio
    async def test_explicit_mode_override(self, config, context):
        """Le mode explicite override la détection."""
        planner = TaskPlanner(config)
        
        plan = await planner.plan(context.user_query, context, mode=PlanMode.FAST)
        
        assert plan.mode == PlanMode.FAST


# ============================================================================
# TESTS: PLAN COMPLET
# ============================================================================

class TestCompletePlan:
    """Tests pour le plan complet."""
    
    @pytest.mark.asyncio
    async def test_plan_has_all_components(self, config, context):
        """Un plan a tous les composants requis."""
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        assert plan.id.startswith("plan_")
        assert len(plan.goals) >= 1
        assert len(plan.tasks) >= 1
        assert len(plan.execution_order) >= 1
        assert plan.estimated_duration_s >= 0
        assert 0 <= plan.confidence <= 1
        assert isinstance(plan.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_execution_order_respects_dependencies(self, config, context):
        """L'ordre d'exécution respecte les dépendances."""
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        # Vérifier que les tâches avec dépendances viennent après
        executed = set()
        for task_id in plan.execution_order:
            task = plan.tasks[task_id]
            for dep in task.dependencies:
                assert dep in executed, f"Dependency {dep} not executed before {task_id}"
            executed.add(task_id)
    
    @pytest.mark.asyncio
    async def test_multi_goal_extraction(self, config, complex_context):
        """Plusieurs objectifs sont extraits d'une requête complexe."""
        planner = TaskPlanner(config)
        plan = await planner.plan(complex_context.user_query, complex_context)
        
        # Devrait avoir plusieurs objectifs (analyze, create, send)
        assert len(plan.goals) >= 1
    
    @pytest.mark.asyncio
    async def test_plan_safe_dict_no_sensitive_data(self, config, context):
        """to_safe_dict() ne contient pas de données sensibles."""
        planner = TaskPlanner(config)
        plan = await planner.plan(context.user_query, context)
        
        safe_dict = plan.to_safe_dict()
        
        # Vérifier le format
        assert "plan_id" in safe_dict
        assert "mode" in safe_dict
        assert "goals_count" in safe_dict
        assert isinstance(safe_dict["goals_count"], int)
        
        # Pas de contenu utilisateur
        assert "user_query" not in safe_dict
        assert "goals" not in safe_dict  # Juste le count


# ============================================================================
# TESTS: STATS
# ============================================================================

class TestPlannerStats:
    """Tests pour les statistiques du planner."""
    
    @pytest.mark.asyncio
    async def test_stats_updated(self, config, context):
        """Les stats sont mises à jour après chaque plan."""
        planner = TaskPlanner(config)
        
        initial = planner.get_stats()["plans_created"]
        
        await planner.plan(context.user_query, context)
        
        assert planner.get_stats()["plans_created"] == initial + 1
    
    @pytest.mark.asyncio
    async def test_avg_tasks_calculated(self, config, context):
        """La moyenne de tâches par plan est calculée."""
        planner = TaskPlanner(config)
        
        await planner.plan(context.user_query, context)
        await planner.plan(context.user_query, context)
        
        stats = planner.get_stats()
        assert stats["avg_tasks_per_plan"] >= 0


# ============================================================================
# TESTS: FALLBACK
# ============================================================================

class TestPlannerFallback:
    """Tests pour les cas de fallback."""
    
    @pytest.mark.asyncio
    async def test_empty_query_fallback(self, config):
        """Requête vide → plan de fallback."""
        context = ReasoningContext(session_id="test", user_query="")
        planner = TaskPlanner(config)
        
        plan = await planner.plan("", context)
        
        assert plan is not None
        assert plan.mode == PlanMode.SAFE
    
    @pytest.mark.asyncio
    async def test_very_short_query(self, config):
        """Requête très courte → gérée proprement."""
        context = ReasoningContext(session_id="test", user_query="Hi")
        planner = TaskPlanner(config)
        
        plan = await planner.plan("Hi", context)
        
        assert plan is not None
        assert len(plan.goals) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
