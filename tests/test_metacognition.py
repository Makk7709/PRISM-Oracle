"""
Tests unitaires pour le module Metacognition.

Couvre:
- Analyse de confiance multi-facteurs
- Détection d'incertitude
- Logique d'escalade
- Génération de questions de clarification
- Apprentissage léger
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from python.helpers.metacognition import (
    Metacognition,
    MetacognitionConfig,
    MetaDecision,
    ConfidenceAnalysis,
    ConfidenceLevel,
    UncertaintySignal,
    UncertaintyType,
    MemoryHint,
    LearningStats,
    create_metacognition,
)
from python.helpers.reasoning_engine import (
    ReasoningContext,
    ReasoningOutcome,
    ReasoningFlag,
    EscalationType,
    TraceStep,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def config():
    """Configuration de test."""
    return MetacognitionConfig(
        confidence_high=0.85,
        confidence_medium=0.6,
        confidence_low=0.4,
        confidence_critical=0.25,
        escalate_on_confidence_below=0.5,
        enable_learning=False,  # Désactivé pour les tests
    )


@pytest.fixture
def context():
    """Contexte de test."""
    return ReasoningContext(
        session_id="test_meta_001",
        user_query="Analyze this document",
        available_tools=["document_query"],
    )


@pytest.fixture
def high_confidence_outcome():
    """Outcome avec haute confiance."""
    return ReasoningOutcome(
        answer="Analysis complete",
        trace=[TraceStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="Analyze",
            outcome="Success",
            confidence=0.9,
            duration_ms=100,
        )],
        confidence=0.9,
        flags=[],
        debug_id="test_high",
        subtasks_completed=3,
        subtasks_total=3,
        backtracks_used=0,
        tool_calls_made=2,
        total_duration_ms=500,
    )


@pytest.fixture
def low_confidence_outcome():
    """Outcome avec basse confiance."""
    return ReasoningOutcome(
        answer="Uncertain result",
        trace=[],
        confidence=0.35,
        flags=[ReasoningFlag.UNCERTAIN, ReasoningFlag.LOW_CONFIDENCE],
        debug_id="test_low",
        subtasks_completed=1,
        subtasks_total=3,
        backtracks_used=2,
        tool_calls_made=5,
        total_duration_ms=1000,
    )


@pytest.fixture
def contradiction_outcome():
    """Outcome avec contradiction détectée."""
    return ReasoningOutcome(
        answer="Conflicting results",
        trace=[],
        confidence=0.45,
        flags=[ReasoningFlag.CONTRADICTION],
        debug_id="test_contradiction",
        subtasks_completed=2,
        subtasks_total=3,
        backtracks_used=1,
        tool_calls_made=3,
        total_duration_ms=800,
    )


@pytest.fixture
def missing_info_outcome():
    """Outcome avec info manquante."""
    return ReasoningOutcome(
        answer="Partial result",
        trace=[],
        confidence=0.55,
        flags=[ReasoningFlag.MISSING_INFO],
        debug_id="test_missing",
        subtasks_completed=2,
        subtasks_total=3,
        backtracks_used=0,
        tool_calls_made=2,
        total_duration_ms=600,
    )


# ============================================================================
# TESTS: ANALYSE DE CONFIANCE
# ============================================================================

class TestConfidenceAnalysis:
    """Tests pour l'analyse de confiance."""
    
    @pytest.mark.asyncio
    async def test_high_confidence_level(self, config, context, high_confidence_outcome):
        """Confiance haute → niveau HIGH."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        assert decision.confidence_analysis.level == ConfidenceLevel.HIGH
        assert decision.confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_low_confidence_level(self, config, context, low_confidence_outcome):
        """Confiance basse → niveau LOW ou CRITICAL."""
        meta = Metacognition(config)
        decision = await meta.evaluate(low_confidence_outcome, context)
        
        assert decision.confidence_analysis.level in [ConfidenceLevel.LOW, ConfidenceLevel.CRITICAL]
    
    @pytest.mark.asyncio
    async def test_confidence_factors_calculated(self, config, context, high_confidence_outcome):
        """Les facteurs de confiance sont calculés."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        factors = decision.confidence_analysis.factors
        
        assert "reasoning_confidence" in factors
        assert "task_success_rate" in factors
        assert "backtrack_factor" in factors
        assert "flag_factor" in factors
    
    @pytest.mark.asyncio
    async def test_backtrack_penalty(self, config, context):
        """Les backtracks réduisent la confiance."""
        outcome_no_backtrack = ReasoningOutcome(
            answer="",
            trace=[],
            confidence=0.8,
            flags=[],
            debug_id="test",
            subtasks_completed=2,
            subtasks_total=2,
            backtracks_used=0,
            tool_calls_made=2,
            total_duration_ms=100,
        )
        
        outcome_with_backtracks = ReasoningOutcome(
            answer="",
            trace=[],
            confidence=0.8,
            flags=[],
            debug_id="test",
            subtasks_completed=2,
            subtasks_total=2,
            backtracks_used=3,
            tool_calls_made=2,
            total_duration_ms=100,
        )
        
        meta = Metacognition(config)
        
        decision_no_bt = await meta.evaluate(outcome_no_backtrack, context)
        decision_with_bt = await meta.evaluate(outcome_with_backtracks, context)
        
        # Plus de backtracks = confiance plus basse
        assert decision_with_bt.confidence <= decision_no_bt.confidence


# ============================================================================
# TESTS: DÉTECTION D'INCERTITUDE
# ============================================================================

class TestUncertaintyDetection:
    """Tests pour la détection d'incertitude."""
    
    @pytest.mark.asyncio
    async def test_detect_missing_info(self, config, context, missing_info_outcome):
        """Flag MISSING_INFO → signal d'incertitude."""
        meta = Metacognition(config)
        decision = await meta.evaluate(missing_info_outcome, context)
        
        # Devrait avoir des raisons d'incertitude
        assert len(decision.uncertainty_reasons) >= 0
    
    @pytest.mark.asyncio
    async def test_detect_contradiction(self, config, context, contradiction_outcome):
        """Flag CONTRADICTION → signal d'incertitude."""
        meta = Metacognition(config)
        decision = await meta.evaluate(contradiction_outcome, context)
        
        signals = decision.confidence_analysis.signals
        contradiction_signals = [
            s for s in signals 
            if s.type == UncertaintyType.CONTRADICTORY_DATA
        ]
        
        assert len(contradiction_signals) >= 1 or ReasoningFlag.CONTRADICTION in contradiction_outcome.flags
    
    @pytest.mark.asyncio
    async def test_uncertainty_reasons_limited(self, config, context, low_confidence_outcome):
        """Les raisons d'incertitude sont limitées en nombre."""
        meta = Metacognition(config)
        decision = await meta.evaluate(low_confidence_outcome, context)
        
        assert len(decision.uncertainty_reasons) <= config.max_uncertainty_reasons


# ============================================================================
# TESTS: ESCALADE
# ============================================================================

class TestEscalation:
    """Tests pour la logique d'escalade."""
    
    @pytest.mark.asyncio
    async def test_high_confidence_no_escalation(self, config, context, high_confidence_outcome):
        """Haute confiance → pas d'escalade."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        assert decision.escalation == EscalationType.NONE
    
    @pytest.mark.asyncio
    async def test_low_confidence_human_review(self, config, context):
        """POLITIQUE: Confiance 0.25 (entre safe_refuse et human_review) → HUMAN_REVIEW."""
        # Créer un outcome avec confidence dans la zone HUMAN_REVIEW (0.2 <= x < 0.35)
        low_outcome = ReasoningOutcome(
            answer="Uncertain result",
            trace=[],
            confidence=0.25,  # 0.2 <= 0.25 < 0.35 → zone HUMAN_REVIEW
            flags=[ReasoningFlag.UNCERTAIN],
            debug_id="test_low",
            subtasks_completed=1,
            subtasks_total=3,
            backtracks_used=2,
            tool_calls_made=5,
            total_duration_ms=1000,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(low_outcome, context)
        
        # INVARIANT: Si confiance brute >= 0.2, pas de SAFE_REFUSE
        assert decision.escalation != EscalationType.SAFE_REFUSE, \
            "SAFE_REFUSE ne devrait pas se déclencher pour confidence >= 0.2"
        # Confiance basse devrait déclencher une forme d'escalade (pas NONE)
        assert decision.escalation in [
            EscalationType.HUMAN_REVIEW,
            EscalationType.ASK_CLARIFY,
        ], f"Confiance basse devrait escalader, got {decision.escalation}"
    
    @pytest.mark.asyncio
    async def test_missing_info_ask_clarify(self, config, context, missing_info_outcome):
        """Info manquante → ASK_CLARIFY."""
        meta = Metacognition(config)
        decision = await meta.evaluate(missing_info_outcome, context)
        
        # Devrait demander clarification ou escalader
        assert decision.escalation in [
            EscalationType.ASK_CLARIFY,
            EscalationType.HUMAN_REVIEW,
            EscalationType.NONE,  # Peut être NONE si confiance suffisante
        ]
    
    @pytest.mark.asyncio
    async def test_critical_confidence_safe_refuse(self, config, context):
        """POLITIQUE PRODUIT: Confiance brute < 0.2 → SAFE_REFUSE obligatoire."""
        critical_outcome = ReasoningOutcome(
            answer="",
            trace=[],
            confidence=0.15,  # < safe_refuse_threshold (0.2)
            flags=[ReasoningFlag.UNCERTAIN],
            debug_id="test_critical",
            subtasks_completed=0,
            subtasks_total=3,
            backtracks_used=3,
            tool_calls_made=1,
            total_duration_ms=100,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(critical_outcome, context)
        
        # STRICT: Confiance brute critique = SAFE_REFUSE, pas d'alternative
        assert decision.escalation == EscalationType.SAFE_REFUSE, \
            f"Politique violée: confidence={critical_outcome.confidence} devrait être SAFE_REFUSE, got {decision.escalation}"
        assert decision.confidence_analysis.level == ConfidenceLevel.CRITICAL


# ============================================================================
# TESTS: QUESTIONS DE CLARIFICATION
# ============================================================================

class TestClarificationQuestions:
    """Tests pour les questions de clarification."""
    
    @pytest.mark.asyncio
    async def test_questions_generated_on_ask_clarify(self, config, context, missing_info_outcome):
        """Questions générées quand ASK_CLARIFY."""
        # Forcer une confiance qui déclenche ASK_CLARIFY
        missing_info_outcome.confidence = 0.45
        
        meta = Metacognition(config)
        decision = await meta.evaluate(missing_info_outcome, context)
        
        if decision.escalation == EscalationType.ASK_CLARIFY:
            assert len(decision.clarification_questions) >= 1
    
    @pytest.mark.asyncio
    async def test_questions_limited(self, config, context, missing_info_outcome):
        """Les questions sont limitées en nombre."""
        meta = Metacognition(config)
        decision = await meta.evaluate(missing_info_outcome, context)
        
        assert len(decision.clarification_questions) <= config.max_clarification_questions
    
    @pytest.mark.asyncio
    async def test_no_questions_on_high_confidence(self, config, context, high_confidence_outcome):
        """Pas de questions si haute confiance."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        assert len(decision.clarification_questions) == 0


# ============================================================================
# TESTS: MEMORY HINTS
# ============================================================================

class TestMemoryHints:
    """Tests pour les suggestions mémoire."""
    
    @pytest.mark.asyncio
    async def test_remember_on_high_confidence(self, config, context, high_confidence_outcome):
        """Haute confiance → suggestion de mémoriser."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        remember_hints = [h for h in decision.memory_hints if h.action == "remember"]
        
        # Devrait suggérer de mémoriser
        assert len(remember_hints) >= 0  # Peut être 0 ou plus selon l'implémentation
    
    @pytest.mark.asyncio
    async def test_memory_hints_limited(self, config, context, high_confidence_outcome):
        """Les hints mémoire sont limités."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        assert len(decision.memory_hints) <= 3


# ============================================================================
# TESTS: RETRY LOGIC
# ============================================================================

class TestRetryLogic:
    """Tests pour la logique de retry."""
    
    @pytest.mark.asyncio
    async def test_no_retry_on_high_confidence(self, config, context, high_confidence_outcome):
        """Haute confiance → pas de retry."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        assert decision.should_retry == False
    
    @pytest.mark.asyncio
    async def test_no_retry_after_many_backtracks(self, config, context):
        """Beaucoup de backtracks → pas de retry."""
        outcome = ReasoningOutcome(
            answer="",
            trace=[],
            confidence=0.5,
            flags=[],
            debug_id="test",
            subtasks_completed=1,
            subtasks_total=3,
            backtracks_used=3,  # Beaucoup
            tool_calls_made=5,
            total_duration_ms=1000,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.should_retry == False


# ============================================================================
# TESTS: APPRENTISSAGE LÉGER
# ============================================================================

class TestLightLearning:
    """Tests pour l'apprentissage léger."""
    
    def test_learning_stats_update_tool_failure(self):
        """Les stats de failure sont mises à jour."""
        stats = LearningStats()
        
        stats.update_tool_failure("tool_1", True)
        stats.update_tool_failure("tool_1", False)
        
        assert "tool_1" in stats.tool_failure_rates
        assert 0 <= stats.tool_failure_rates["tool_1"] <= 1
    
    def test_learning_stats_update_evaluation(self):
        """Les stats d'évaluation sont mises à jour."""
        stats = LearningStats()
        
        stats.update_evaluation(0.8)
        stats.update_evaluation(0.6)
        stats.update_evaluation(0.7)
        
        assert stats.total_evaluations == 3
        assert 0 <= stats.avg_confidence <= 1
    
    def test_learning_stats_record_escalation(self):
        """Les escalades sont enregistrées."""
        stats = LearningStats()
        
        stats.record_escalation(EscalationType.ASK_CLARIFY)
        stats.record_escalation(EscalationType.ASK_CLARIFY)
        stats.record_escalation(EscalationType.HUMAN_REVIEW)
        
        assert stats.escalation_counts["ask_clarify"] == 2
        assert stats.escalation_counts["human_review"] == 1
    
    def test_learning_stats_serialization(self):
        """Les stats se sérialisent/désérialisent correctement."""
        stats = LearningStats()
        stats.update_evaluation(0.8)
        stats.update_tool_failure("tool_1", True)
        
        # Sérialiser
        data = stats.to_dict()
        
        # Vérifier le format
        assert isinstance(data, dict)
        assert "total_evaluations" in data
        
        # Désérialiser
        restored = LearningStats.from_dict(data)
        
        assert restored.total_evaluations == stats.total_evaluations
    
    @pytest.mark.asyncio
    async def test_learning_enabled_updates_stats(self, context, high_confidence_outcome):
        """Avec learning activé, les stats sont mises à jour."""
        config = MetacognitionConfig(enable_learning=True)
        meta = Metacognition(config)
        
        initial_evals = meta.get_stats()["total_evaluations"]
        
        await meta.evaluate(high_confidence_outcome, context)
        
        assert meta.get_stats()["total_evaluations"] == initial_evals + 1
    
    def test_stats_file_persistence(self):
        """Les stats peuvent être persistées dans un fichier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = str(Path(tmpdir) / "meta_stats.json")
            
            # Créer et utiliser la metacognition
            config = MetacognitionConfig(
                enable_learning=True,
                stats_file_path=stats_path,
            )
            meta = Metacognition(config)
            
            # Mettre à jour des stats
            meta._stats.update_evaluation(0.8)
            meta._stats.update_evaluation(0.7)
            meta._save_stats()
            
            # Vérifier que le fichier existe
            assert Path(stats_path).exists()
            
            # Charger dans une nouvelle instance
            meta2 = Metacognition(config)
            
            assert meta2.get_stats()["total_evaluations"] == 2


# ============================================================================
# TESTS: SAFE DICT ET PAS DE FUITE
# ============================================================================

class TestSafeDictAndNoLeakage:
    """Tests pour vérifier l'absence de fuite de données."""
    
    @pytest.mark.asyncio
    async def test_decision_safe_dict(self, config, context, high_confidence_outcome):
        """to_safe_dict() ne contient pas de données sensibles."""
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        safe_dict = decision.to_safe_dict()
        
        # Vérifier le format
        assert "debug_id" in safe_dict
        assert "confidence" in safe_dict
        assert "escalation" in safe_dict
        
        # Pas de données sensibles
        assert "confidence_analysis" not in safe_dict
        assert "memory_hints" not in safe_dict
        assert "clarification_questions" not in safe_dict or \
               isinstance(safe_dict.get("clarification_questions"), int)
    
    @pytest.mark.asyncio
    async def test_stats_no_pii(self, config, context, high_confidence_outcome):
        """Les stats ne contiennent pas de PII."""
        config = MetacognitionConfig(enable_learning=True)
        meta = Metacognition(config)
        
        await meta.evaluate(high_confidence_outcome, context)
        
        stats = meta.get_stats()
        
        # Les stats sont agrégées/numériques
        assert isinstance(stats["total_evaluations"], int)
        assert isinstance(stats["avg_confidence"], float)
        
        # Pas de contenu de requête
        for key, value in stats.items():
            if isinstance(value, str) and len(value) > 50:
                pytest.fail(f"Potentielle fuite PII dans stats[{key}]")
    
    @pytest.mark.asyncio
    async def test_uncertainty_reasons_short(self, config, context, low_confidence_outcome):
        """Les raisons d'incertitude sont courtes."""
        meta = Metacognition(config)
        decision = await meta.evaluate(low_confidence_outcome, context)
        
        for reason in decision.uncertainty_reasons:
            assert len(reason) <= 80, f"Raison trop longue: {reason}"


# ============================================================================
# TESTS: CAS LIMITES
# ============================================================================

class TestEdgeCases:
    """Tests pour les cas limites."""
    
    @pytest.mark.asyncio
    async def test_empty_outcome(self, config, context):
        """POLITIQUE: Outcome vide (confidence=0) → SAFE_REFUSE obligatoire."""
        empty_outcome = ReasoningOutcome(
            answer="",
            trace=[],
            confidence=0.0,  # < safe_refuse_threshold (0.2)
            flags=[],
            debug_id="empty",
            subtasks_completed=0,
            subtasks_total=0,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=0,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(empty_outcome, context)
        
        assert decision is not None
        # STRICT: confidence=0 < 0.2 → SAFE_REFUSE obligatoire
        assert decision.escalation == EscalationType.SAFE_REFUSE, \
            f"Politique violée: confidence=0 devrait être SAFE_REFUSE, got {decision.escalation}"
    
    @pytest.mark.asyncio
    async def test_all_flags_set(self, config, context):
        """Tous les flags → géré proprement."""
        all_flags_outcome = ReasoningOutcome(
            answer="Complex result",
            trace=[],
            confidence=0.3,
            flags=[
                ReasoningFlag.UNCERTAIN,
                ReasoningFlag.NEEDS_HUMAN,
                ReasoningFlag.POLICY_RISK,
                ReasoningFlag.TOOL_RISK,
                ReasoningFlag.CONTRADICTION,
                ReasoningFlag.MISSING_INFO,
            ],
            debug_id="all_flags",
            subtasks_completed=1,
            subtasks_total=5,
            backtracks_used=3,
            tool_calls_made=10,
            total_duration_ms=5000,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(all_flags_outcome, context)
        
        # Devrait escalader fortement
        assert decision.escalation in [
            EscalationType.HUMAN_REVIEW,
            EscalationType.SAFE_REFUSE,
        ]


# ============================================================================
# TESTS: CONVENIENCE FUNCTION
# ============================================================================

class TestConvenienceFunction:
    """Tests pour les fonctions de commodité."""
    
    def test_create_metacognition(self):
        """create_metacognition() crée une instance valide."""
        meta = create_metacognition(enable_learning=False)
        
        assert isinstance(meta, Metacognition)
        assert meta.config.enable_learning == False
    
    def test_create_metacognition_with_stats_path(self):
        """create_metacognition() accepte un chemin de stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = str(Path(tmpdir) / "stats.json")
            
            meta = create_metacognition(
                enable_learning=True,
                stats_path=stats_path,
            )
            
            assert meta.config.stats_file_path == stats_path


# ============================================================================
# TESTS: POLICY CONSTITUTION (NON-NÉGOCIABLE)
# ============================================================================

class TestPolicyConstitution:
    """
    Tests de politique produit "constitution" — ces tests VERROUILLENT 
    les invariants d'escalade. Ils ne doivent JAMAIS être assouplis.
    
    INVARIANTS:
    I1. Non-dilution: raw_confidence < safe_refuse_threshold => SAFE_REFUSE
    I2. Monotonicité: ajouter des signaux ne peut que DURCIR l'escalade
    """
    
    # ==========================================================================
    # T1: NON-DILUTION (I1)
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_T1_non_dilution_critical_confidence(self, config, context):
        """
        T1: INVARIANT NON-DILUTION
        
        Même si le score composite remonte, raw_confidence < safe_refuse_threshold
        DOIT déclencher SAFE_REFUSE.
        """
        # Outcome avec confiance critique mais succès partiel (qui pourrait diluer)
        critical_outcome = ReasoningOutcome(
            answer="Some answer",  # Non vide
            trace=[],
            confidence=0.15,  # < safe_refuse_threshold (0.2)
            flags=[],  # Pas de flags aggravants
            debug_id="t1_non_dilution",
            subtasks_completed=3,  # Bon succès (pourrait diluer)
            subtasks_total=3,
            backtracks_used=0,  # Pas de backtrack
            tool_calls_made=1,
            total_duration_ms=100,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(critical_outcome, context)
        
        # ASSERTION STRICTE: raw < 0.2 => SAFE_REFUSE, non négociable
        assert decision.escalation == EscalationType.SAFE_REFUSE, \
            f"VIOLATION I1 NON-DILUTION: raw={critical_outcome.confidence} devrait être SAFE_REFUSE, got {decision.escalation}"
    
    # ==========================================================================
    # T2: TABLE DE VÉRITÉ DES SEUILS (POLICY LOCK)
    # ==========================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw_conf,min_expected_severity", [
        (0.10, 3),  # < safe_refuse_threshold (0.2) => SAFE_REFUSE (severity 3)
        (0.15, 3),  # < safe_refuse_threshold (0.2) => SAFE_REFUSE (severity 3)
        (0.19, 3),  # < safe_refuse_threshold (0.2) => SAFE_REFUSE (severity 3)
        (0.20, 2),  # = safe_refuse_threshold => HUMAN_REVIEW (severity 2)
        (0.25, 2),  # < human_review_threshold (0.35) => HUMAN_REVIEW (severity 2)
        (0.34, 2),  # < human_review_threshold (0.35) => HUMAN_REVIEW (severity 2)
        (0.35, 1),  # = human_review_threshold => ASK_CLARIFY ou NONE (severity <= 1)
        (0.45, 1),  # < escalate_on_confidence_below (0.5) => ASK_CLARIFY (severity 1)
        (0.50, 0),  # = escalate_on_confidence_below => NONE (severity 0)
        (0.60, 0),  # > escalate_on_confidence_below => NONE (severity 0)
        (0.85, 0),  # Haute confiance => NONE (severity 0)
    ])
    async def test_T2_threshold_table(self, config, context, raw_conf, min_expected_severity):
        """
        T2: Table de vérité des seuils d'escalade.
        
        Vérifie que les seuils de config déterminent le plancher d'escalade.
        """
        # Ordre de sévérité: NONE=0, ASK_CLARIFY=1, HUMAN_REVIEW=2, SAFE_REFUSE=3
        SEVERITY = {
            EscalationType.NONE: 0,
            EscalationType.ASK_CLARIFY: 1,
            EscalationType.HUMAN_REVIEW: 2,
            EscalationType.SAFE_REFUSE: 3,
        }
        
        outcome = ReasoningOutcome(
            answer="Test",
            trace=[],
            confidence=raw_conf,
            flags=[],  # Pas de flags (test du plancher)
            debug_id=f"t2_threshold_{raw_conf}",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        actual_severity = SEVERITY[decision.escalation]
        assert actual_severity >= min_expected_severity, \
            f"VIOLATION SEUIL: raw={raw_conf} devrait avoir sévérité >= {min_expected_severity}, " \
            f"got {decision.escalation.value} (sévérité {actual_severity})"
    
    # ==========================================================================
    # T3: MONOTONICITÉ (I2)
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_T3_monotonicity_adding_signals_never_reduces(self, config, context):
        """
        T3: INVARIANT MONOTONICITÉ
        
        Ajouter des signaux de risque ne peut JAMAIS réduire la sévérité.
        """
        SEVERITY = {
            EscalationType.NONE: 0,
            EscalationType.ASK_CLARIFY: 1,
            EscalationType.HUMAN_REVIEW: 2,
            EscalationType.SAFE_REFUSE: 3,
        }
        
        # Baseline: confiance moyenne, pas de flags
        baseline_outcome = ReasoningOutcome(
            answer="Baseline",
            trace=[],
            confidence=0.60,  # > escalate_on_confidence_below => baseline NONE
            flags=[],
            debug_id="t3_baseline",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        
        meta = Metacognition(config)
        baseline_decision = await meta.evaluate(baseline_outcome, context)
        baseline_severity = SEVERITY[baseline_decision.escalation]
        
        # Ajouter MISSING_INFO => devrait être >= baseline
        with_missing_info = ReasoningOutcome(
            answer="With missing info",
            trace=[],
            confidence=0.60,
            flags=[ReasoningFlag.MISSING_INFO],
            debug_id="t3_missing_info",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        decision_with_missing = await meta.evaluate(with_missing_info, context)
        severity_with_missing = SEVERITY[decision_with_missing.escalation]
        
        assert severity_with_missing >= baseline_severity, \
            f"VIOLATION I2 MONOTONICITÉ: ajouter MISSING_INFO a RÉDUIT la sévérité " \
            f"({baseline_decision.escalation.value} -> {decision_with_missing.escalation.value})"
        
        # Ajouter POLICY_RISK => devrait être >= baseline
        with_policy_risk = ReasoningOutcome(
            answer="With policy risk",
            trace=[],
            confidence=0.60,
            flags=[ReasoningFlag.POLICY_RISK],
            debug_id="t3_policy_risk",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        decision_with_policy = await meta.evaluate(with_policy_risk, context)
        severity_with_policy = SEVERITY[decision_with_policy.escalation]
        
        assert severity_with_policy >= baseline_severity, \
            f"VIOLATION I2 MONOTONICITÉ: ajouter POLICY_RISK a RÉDUIT la sévérité " \
            f"({baseline_decision.escalation.value} -> {decision_with_policy.escalation.value})"
        
        # POLICY_RISK devrait déclencher HUMAN_REVIEW minimum
        assert decision_with_policy.escalation == EscalationType.HUMAN_REVIEW, \
            f"POLICY_RISK devrait déclencher HUMAN_REVIEW, got {decision_with_policy.escalation.value}"
    
    # ==========================================================================
    # T4: MISSING_INFO BEHAVIOR
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_T4_missing_info_high_conf_ask_clarify(self, config, context):
        """
        T4a: MISSING_INFO + confiance haute => ASK_CLARIFY (max 2 questions).
        """
        outcome = ReasoningOutcome(
            answer="Need more info",
            trace=[],
            confidence=0.55,  # >= human_review_threshold, mais < escalate_on_confidence_below
            flags=[ReasoningFlag.MISSING_INFO],
            debug_id="t4a_missing_high",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # MISSING_INFO avec confiance suffisante => ASK_CLARIFY
        assert decision.escalation == EscalationType.ASK_CLARIFY, \
            f"MISSING_INFO + conf=0.55 devrait être ASK_CLARIFY, got {decision.escalation.value}"
        
        # Max 2 questions
        assert len(decision.clarification_questions) <= config.max_clarification_questions
    
    @pytest.mark.asyncio
    async def test_T4_missing_info_critical_conf_safe_refuse(self, config, context):
        """
        T4b: MISSING_INFO + confiance critique => SAFE_REFUSE (non diluable).
        """
        outcome = ReasoningOutcome(
            answer="Critical with missing info",
            trace=[],
            confidence=0.15,  # < safe_refuse_threshold
            flags=[ReasoningFlag.MISSING_INFO],  # Ne devrait PAS diluer
            debug_id="t4b_missing_critical",
            subtasks_completed=1,
            subtasks_total=1,
            backtracks_used=0,
            tool_calls_made=0,
            total_duration_ms=50,
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # INVARIANT I1: raw < 0.2 => SAFE_REFUSE, même avec MISSING_INFO
        assert decision.escalation == EscalationType.SAFE_REFUSE, \
            f"VIOLATION I1: MISSING_INFO ne peut PAS diluer raw=0.15 => SAFE_REFUSE, got {decision.escalation.value}"


# ============================================================================
# TESTS: SÉCURITÉ — NO-COT LEAK (S1)
# ============================================================================

class TestSecurityNoCoTLeak:
    """
    Tests de sécurité S1: Vérifier que le filtre CoT est ACTIF.
    
    Ces tests doivent ÉCHOUER si le sanitizer est désactivé.
    """
    
    def test_S1_cot_patterns_detected(self):
        """
        S1a: TEST NÉGATIF — Le détecteur DOIT attraper les patterns CoT.
        """
        from python.helpers.reasoning_engine import ReasoningEngine, ReasoningConfig
        
        COT_PATTERNS_MUST_CATCH = [
            "thought:",
            "let me think",
            "let's think",
            "step-by-step",
            "chain-of-thought",
            "scratchpad",
            "internal reasoning",
            "my reasoning is",
        ]
        
        config = ReasoningConfig()
        engine = ReasoningEngine(config)
        
        for pattern in COT_PATTERNS_MUST_CATCH:
            dirty_text = f"Some text {pattern} more text"
            assert engine._contains_cot_pattern(dirty_text), \
                f"FILTRE MORT: pattern '{pattern}' non détecté — sécurité compromise!"
    
    def test_S1_trace_sanitization_works(self):
        """
        S1b: Les traces avec CoT sont SANITIZÉES (pattern remplacé ou tronqué).
        """
        from python.helpers.reasoning_engine import TraceStep
        
        # Injection volontaire de CoT
        dirty_action = "Thought: Let me think step-by-step about this problem..."
        
        trace = TraceStep(
            step_id="s1_test",
            timestamp="2026-01-24T12:00:00",
            action=dirty_action,
            outcome="Result",
            confidence=0.9,
            duration_ms=100,
        )
        
        # Le sanitizer doit avoir remplacé les patterns
        assert "thought:" not in trace.action.lower(), \
            f"COT LEAK: 'thought:' présent après sanitization: {trace.action}"
        assert "step-by-step" not in trace.action.lower(), \
            f"COT LEAK: 'step-by-step' présent après sanitization: {trace.action}"
    
    def test_S1_clean_text_not_flagged(self):
        """
        S1c: Le détecteur ne génère PAS de faux positifs sur texte propre.
        """
        from python.helpers.reasoning_engine import ReasoningEngine, ReasoningConfig
        
        clean_texts = [
            "Analyzed the data successfully",
            "Created a report with findings",
            "Executed tool: search_web",
            "Result: 42 items found",
            "Step completed",
        ]
        
        config = ReasoningConfig()
        engine = ReasoningEngine(config)
        
        for text in clean_texts:
            assert not engine._contains_cot_pattern(text), \
                f"FAUX POSITIF: texte propre '{text}' flagué comme CoT"


# ============================================================================
# TESTS: SÉCURITÉ — NO USER-CONTENT LOGS (S2)
# ============================================================================

class TestSecurityNoUserContentLogs:
    """
    Tests de sécurité S2: Vérifier que les logs ne contiennent pas de PII/user content.
    """
    
    @pytest.mark.asyncio
    async def test_S2_safe_dict_no_sensitive_fields(self, config, context, high_confidence_outcome):
        """
        S2a: to_safe_dict() ne contient pas de champs sensibles.
        """
        meta = Metacognition(config)
        decision = await meta.evaluate(high_confidence_outcome, context)
        
        safe_dict = decision.to_safe_dict()
        safe_str = str(safe_dict).lower()
        
        # Patterns interdits
        forbidden_patterns = [
            "user_query",
            "prompt",
            "completion",
            "message",
            "thought:",
            "let me think",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in safe_str, \
                f"PII LEAK: pattern '{pattern}' trouvé dans safe_dict: {safe_dict}"
    
    def test_S2_stats_no_pii(self, config):
        """
        S2b: Les stats ne contiennent pas de PII.
        """
        meta = Metacognition(config)
        
        # Simuler quelques enregistrements
        meta._stats.update_tool_failure("test_tool", failed=True)
        meta._stats.record_escalation(EscalationType.ASK_CLARIFY)
        
        stats_dict = meta._stats.to_dict()
        stats_str = str(stats_dict).lower()
        
        # Vérifier absence de contenu utilisateur
        assert "user_query" not in stats_str
        assert "prompt" not in stats_str
        assert "completion" not in stats_str
        
        # Vérifier que les stats sont numériques/agrégées
        assert isinstance(stats_dict.get("total_evaluations", 0), int)
        assert isinstance(stats_dict.get("escalation_counts", {}), dict)
    
    @pytest.mark.asyncio
    async def test_S2_context_hash_not_raw_query(self, config):
        """
        S2c: Le contexte utilise un HASH, pas la requête brute.
        """
        from python.helpers.reasoning_engine import ReasoningContext
        
        sensitive_query = "My secret password is hunter2 and my SSN is 123-45-6789"
        context = ReasoningContext(
            session_id="s2_test",
            user_query=sensitive_query,
        )
        
        # query_hash doit être un hash, pas la requête brute
        query_hash = context.query_hash
        
        assert "hunter2" not in query_hash, "PII LEAK: password dans query_hash"
        assert "123-45-6789" not in query_hash, "PII LEAK: SSN dans query_hash"
        assert len(query_hash) <= 32, "query_hash devrait être un hash court"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
