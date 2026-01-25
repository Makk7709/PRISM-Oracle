# -*- coding: utf-8 -*-
"""
Tests "Constitution" pour la politique d'escalade Metacognition.

Ces tests verrouillent les INVARIANTS de la politique produit.
NE PAS MODIFIER ces tests pour "faire passer" le code.
Si un test échoue, CORRIGER LE CODE, pas le test.

INVARIANTS:
I1. Non-dilution: raw_confidence < safe_refuse_threshold => SAFE_REFUSE
I2. Monotonicité: signaux ne peuvent que DURCIR l'escalade
I4. No-PII: aucun contenu user dans les logs/exceptions
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from python.helpers.metacognition import (
    Metacognition,
    MetacognitionConfig,
    EscalationType,
    ConfidenceLevel,
    MetaDecision,
    InvariantViolationError,
)
from python.helpers.reasoning_engine import (
    ReasoningContext,
    ReasoningOutcome,
    ReasoningFlag,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def config():
    """Configuration par défaut avec seuils documentés."""
    return MetacognitionConfig(
        safe_refuse_threshold=0.2,
        human_review_threshold=0.35,
        escalate_on_confidence_below=0.5,
    )


@pytest.fixture
def context():
    """Contexte de raisonnement minimal."""
    return ReasoningContext(
        session_id="test_policy",
        user_query="Test query",
    )


def make_outcome(
    confidence: float,
    flags: list = None,
    subtasks_completed: int = 1,
    subtasks_total: int = 1,
    backtracks_used: int = 0,
) -> ReasoningOutcome:
    """Factory pour créer des outcomes de test."""
    return ReasoningOutcome(
        answer="Test answer",
        trace=[],
        confidence=confidence,
        flags=flags or [],
        debug_id=f"test_{confidence}",
        subtasks_completed=subtasks_completed,
        subtasks_total=subtasks_total,
        backtracks_used=backtracks_used,
        tool_calls_made=0,
        total_duration_ms=100,
    )


# ============================================================================
# T1: NON-DILUTION (INVARIANT I1)
# ============================================================================

class TestNonDilution:
    """
    INVARIANT I1: raw_confidence < safe_refuse_threshold => SAFE_REFUSE
    
    Aucun score composite ne peut lever cette escalade.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw_confidence", [0.0, 0.05, 0.10, 0.15, 0.19])
    async def test_critical_confidence_always_safe_refuse(
        self, config, context, raw_confidence
    ):
        """
        POLITIQUE STRICTE: raw < 0.2 => SAFE_REFUSE, peu importe le composite.
        """
        outcome = make_outcome(confidence=raw_confidence)
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.SAFE_REFUSE, (
            f"VIOLATION I1: raw={raw_confidence} devrait être SAFE_REFUSE, "
            f"got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_non_dilution_with_high_composite(self, config, context):
        """
        Même si les facteurs composites sont excellents, 
        raw < threshold => SAFE_REFUSE.
        """
        # Outcome avec raw=0.15 mais facteurs qui pourraient remonter le composite
        outcome = make_outcome(
            confidence=0.15,  # < safe_refuse_threshold (0.2)
            subtasks_completed=3,  # 100% success
            subtasks_total=3,
            backtracks_used=0,  # Pas de backtrack
            flags=[],  # Pas de flags négatifs
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.SAFE_REFUSE, (
            "VIOLATION I1: raw=0.15 avec facteurs excellents "
            "devrait quand même être SAFE_REFUSE"
        )
    
    @pytest.mark.asyncio
    async def test_boundary_at_threshold(self, config, context):
        """
        raw == threshold (0.2) n'est PAS < threshold, donc pas SAFE_REFUSE.
        """
        outcome = make_outcome(confidence=0.2)  # == threshold, pas <
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # 0.2 est >= safe_refuse (0.2), donc ne devrait PAS être SAFE_REFUSE
        # mais < human_review (0.35), donc HUMAN_REVIEW ou ASK_CLARIFY
        assert decision.escalation != EscalationType.SAFE_REFUSE or \
               decision.escalation in [EscalationType.HUMAN_REVIEW, EscalationType.ASK_CLARIFY], (
            f"raw=0.2 (== threshold) devrait être HUMAN_REVIEW ou ASK_CLARIFY, "
            f"got {decision.escalation.value}"
        )


# ============================================================================
# T2: TABLE DE VÉRITÉ DES THRESHOLDS (POLICY LOCK)
# ============================================================================

class TestThresholdTruthTable:
    """
    Table de vérité pour les seuils de la politique.
    
    Les seuils viennent de config, pas de valeurs magiques.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw,expected_min", [
        (0.10, EscalationType.SAFE_REFUSE),
        (0.19, EscalationType.SAFE_REFUSE),
        (0.20, EscalationType.HUMAN_REVIEW),  # >= safe_refuse, < human_review
        (0.25, EscalationType.HUMAN_REVIEW),
        (0.34, EscalationType.HUMAN_REVIEW),
        (0.35, EscalationType.ASK_CLARIFY),   # >= human_review, < escalate_on
        (0.45, EscalationType.ASK_CLARIFY),
        (0.50, EscalationType.NONE),          # >= escalate_on
        (0.60, EscalationType.NONE),
        (0.90, EscalationType.NONE),
    ])
    async def test_threshold_truth_table(
        self, config, context, raw, expected_min
    ):
        """
        Vérifie que les seuils de config sont respectés.
        
        expected_min = escalade MINIMUM (signaux peuvent durcir)
        """
        outcome = make_outcome(confidence=raw, flags=[])
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # Ordre de sévérité
        severity_order = {
            EscalationType.NONE: 0,
            EscalationType.ASK_CLARIFY: 1,
            EscalationType.HUMAN_REVIEW: 2,
            EscalationType.SAFE_REFUSE: 3,
        }
        
        actual_severity = severity_order[decision.escalation]
        expected_severity = severity_order[expected_min]
        
        assert actual_severity >= expected_severity, (
            f"VIOLATION: raw={raw} attendu >= {expected_min.value}, "
            f"got {decision.escalation.value}"
        )


# ============================================================================
# T3: MONOTONICITÉ (INVARIANT I2)
# ============================================================================

class TestMonotonicity:
    """
    INVARIANT I2: Les signaux ne peuvent que DURCIR l'escalade.
    
    Ordre: NONE < ASK_CLARIFY < HUMAN_REVIEW < SAFE_REFUSE
    """
    
    SEVERITY_ORDER = {
        EscalationType.NONE: 0,
        EscalationType.ASK_CLARIFY: 1,
        EscalationType.HUMAN_REVIEW: 2,
        EscalationType.SAFE_REFUSE: 3,
    }
    
    @pytest.mark.asyncio
    async def test_baseline_none_at_high_confidence(self, config, context):
        """Confiance haute sans flags => NONE."""
        outcome = make_outcome(confidence=0.8, flags=[])
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.NONE, (
            f"raw=0.8 sans flags devrait être NONE, got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_adding_missing_info_hardens_to_ask_clarify(self, config, context):
        """MISSING_INFO sur baseline NONE => ASK_CLARIFY."""
        outcome = make_outcome(
            confidence=0.8, 
            flags=[ReasoningFlag.MISSING_INFO]
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.ASK_CLARIFY, (
            f"MISSING_INFO devrait durcir vers ASK_CLARIFY, "
            f"got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_adding_policy_risk_hardens_to_human_review(self, config, context):
        """POLICY_RISK => HUMAN_REVIEW minimum."""
        outcome = make_outcome(
            confidence=0.8, 
            flags=[ReasoningFlag.POLICY_RISK]
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        actual_severity = self.SEVERITY_ORDER[decision.escalation]
        min_expected = self.SEVERITY_ORDER[EscalationType.HUMAN_REVIEW]
        
        assert actual_severity >= min_expected, (
            f"POLICY_RISK devrait être >= HUMAN_REVIEW, "
            f"got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_monotonicity_never_decreases(self, config, context):
        """
        Test systématique: ajouter des flags ne diminue jamais la sévérité.
        """
        meta = Metacognition(config)
        
        # Baseline sans flags
        baseline_outcome = make_outcome(confidence=0.55, flags=[])
        baseline_decision = await meta.evaluate(baseline_outcome, context)
        baseline_severity = self.SEVERITY_ORDER[baseline_decision.escalation]
        
        # Ajouter chaque flag et vérifier monotonicité
        all_flags = [
            ReasoningFlag.UNCERTAIN,
            ReasoningFlag.LOW_CONFIDENCE,
            ReasoningFlag.MISSING_INFO,
            ReasoningFlag.NEEDS_HUMAN,
            ReasoningFlag.POLICY_RISK,
        ]
        
        for flag in all_flags:
            flagged_outcome = make_outcome(confidence=0.55, flags=[flag])
            flagged_decision = await meta.evaluate(flagged_outcome, context)
            flagged_severity = self.SEVERITY_ORDER[flagged_decision.escalation]
            
            assert flagged_severity >= baseline_severity, (
                f"VIOLATION I2: ajout de {flag.value} a RÉDUIT la sévérité "
                f"de {baseline_decision.escalation.value} à "
                f"{flagged_decision.escalation.value}"
            )


# ============================================================================
# T4: MISSING_INFO BEHAVIOR
# ============================================================================

class TestMissingInfoBehavior:
    """
    Tests spécifiques pour le flag MISSING_INFO.
    
    - raw=0.55 + missing_info => ASK_CLARIFY (max 2 questions)
    - raw=0.15 + missing_info => SAFE_REFUSE (non diluable)
    """
    
    @pytest.mark.asyncio
    async def test_missing_info_high_confidence_ask_clarify(self, config, context):
        """raw >= human_review + MISSING_INFO => ASK_CLARIFY."""
        outcome = make_outcome(
            confidence=0.55,
            flags=[ReasoningFlag.MISSING_INFO]
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.ASK_CLARIFY, (
            f"raw=0.55 + MISSING_INFO => ASK_CLARIFY, "
            f"got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_missing_info_low_confidence_safe_refuse(self, config, context):
        """raw < safe_refuse + MISSING_INFO => SAFE_REFUSE (I1 prioritaire)."""
        outcome = make_outcome(
            confidence=0.15,
            flags=[ReasoningFlag.MISSING_INFO]
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        assert decision.escalation == EscalationType.SAFE_REFUSE, (
            f"raw=0.15 + MISSING_INFO => SAFE_REFUSE (I1 non-dilution), "
            f"got {decision.escalation.value}"
        )
    
    @pytest.mark.asyncio
    async def test_clarification_questions_limited(self, config, context):
        """Les questions de clarification sont limitées (max 2)."""
        outcome = make_outcome(
            confidence=0.55,
            flags=[ReasoningFlag.MISSING_INFO]
        )
        
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # Si ASK_CLARIFY, vérifier limite questions
        if decision.escalation == EscalationType.ASK_CLARIFY:
            assert len(decision.clarification_questions) <= config.max_clarification_questions, (
                f"Trop de questions: {len(decision.clarification_questions)} > "
                f"{config.max_clarification_questions}"
            )


# ============================================================================
# T5: PROD-SAFE INVARIANTS (pas d'assert optimizable)
# ============================================================================

class TestProdSafeInvariants:
    """
    Vérifie que les invariants sont PROD-SAFE:
    - InvariantViolationError est utilisé (pas assert)
    - L'exception n'est pas supprimable via python -O
    """
    
    def test_invariant_violation_error_exists(self):
        """InvariantViolationError est importable et utilisable."""
        error = InvariantViolationError(
            invariant_id="TEST",
            message="test message",
            details={"key": "value"},
        )
        assert error.invariant_id == "TEST"
        assert "TEST" in str(error)
    
    def test_invariant_violation_error_no_pii(self):
        """InvariantViolationError.to_safe_dict() ne contient pas de PII."""
        error = InvariantViolationError(
            invariant_id="I2_MONOTONICITY",
            message="user@example.com leaked",  # Simule une fuite
            details={"escalation": "safe_refuse"},
        )
        
        safe_dict = error.to_safe_dict()
        safe_str = str(safe_dict).lower()
        
        # Le message n'est PAS dans safe_dict
        assert "user@example.com" not in safe_str
        assert "invariant_id" in safe_dict
    
    def test_monotonicity_uses_exception_not_assert(self):
        """
        Vérifie que _apply_hardening_signals utilise raise, pas assert.
        
        Ce test échoue si quelqu'un réintroduit un assert pour I2.
        """
        import inspect
        from python.helpers.metacognition import Metacognition
        
        source = inspect.getsource(Metacognition._apply_hardening_signals)
        
        # Doit contenir raise InvariantViolationError
        assert "raise InvariantViolationError" in source, \
            "VIOLATION: _apply_hardening_signals doit utiliser raise, pas assert"
        
        # Ne doit PAS contenir assert pour la monotonicité
        # (les autres asserts de debug sont OK mais pas pour I2)
        lines = source.split('\n')
        for line in lines:
            if 'assert' in line.lower() and 'severity' in line.lower():
                pytest.fail(
                    f"VIOLATION: assert trouvé pour sévérité (non prod-safe): {line}"
                )
    
    def test_exception_not_optimized_away(self):
        """
        Vérifie que InvariantViolationError n'est pas supprimable via -O.
        
        Ce test exécute un sous-process avec python -O.
        """
        test_code = '''
import sys
sys.path.insert(0, ".")
from python.helpers.metacognition import InvariantViolationError

# Simuler une violation (ce code ne devrait jamais s'exécuter en prod)
try:
    raise InvariantViolationError("TEST", "simulated")
except InvariantViolationError as e:
    print(f"CAUGHT:{e.invariant_id}")
    sys.exit(0)

# Si on arrive ici, l'exception a été supprimée
print("SUPPRESSED")
sys.exit(1)
'''
        result = subprocess.run(
            [sys.executable, "-O", "-c", test_code],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=10,
        )
        
        assert "CAUGHT:TEST" in result.stdout, \
            f"InvariantViolationError supprimée en mode -O! stdout={result.stdout}, stderr={result.stderr}"


# ============================================================================
# T6: MERGE GATE GUARD RAIL
# ============================================================================

class TestMergeGateGuardRail:
    """
    Tests qui vérifient que les tests policy critiques sont présents.
    
    Si ce test échoue, c'est que quelqu'un a exclu des tests critiques.
    """
    
    CRITICAL_TEST_MARKERS = [
        "test_critical_confidence_always_safe_refuse",
        "test_non_dilution_with_high_composite",
        "test_monotonicity_never_decreases",
        "test_S2_safe_dict_no_sensitive_fields",
        "test_replay_case",  # Replay harness
        "test_invariant_i1_non_dilution_comprehensive",  # Replay harness
    ]
    
    def test_critical_tests_exist_in_collection(self):
        """
        Vérifie que les tests critiques sont collectés par pytest.
        
        Ce test échoue si un test critique est supprimé ou renommé.
        """
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_metacognition_policy.py",
                "tests/test_metacognition.py",
                "tests/test_replay_harness.py",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=30,
        )
        
        collected = result.stdout
        
        for marker in self.CRITICAL_TEST_MARKERS:
            assert marker in collected, \
                f"GUARD RAIL: Test critique '{marker}' absent de la collection!"
    
    def test_replay_harness_included_in_gate(self):
        """
        Vérifie que test_replay_harness.py est inclus dans le merge gate.
        """
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_replay_harness.py",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=30,
        )
        
        assert "test_replay_case" in result.stdout, \
            "GUARD RAIL: test_replay_harness.py non collecté ou test_replay_case absent!"
        assert "14 tests collected" in result.stdout or "tests collected" in result.stdout, \
            f"GUARD RAIL: Replay harness tests non collectés! stdout={result.stdout}"
    
    def test_minimum_test_count(self):
        """
        Vérifie un nombre minimum de tests policy.
        
        Empêche la suppression silencieuse de tests.
        """
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_metacognition_policy.py",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=30,
        )
        
        # Extraire le nombre de tests collectés
        match = re.search(r"(\d+) tests? collected", result.stdout)
        assert match, f"Impossible de parser la sortie pytest: {result.stdout}"
        
        test_count = int(match.group(1))
        MIN_EXPECTED = 20  # Ajuster si tests ajoutés
        
        assert test_count >= MIN_EXPECTED, \
            f"GUARD RAIL: Seulement {test_count} tests collectés, minimum attendu: {MIN_EXPECTED}"


# ============================================================================
# T7: NO-PII LOG PAYLOADS (SYSTEM-LEVEL)
# ============================================================================

class TestNoPIILogPayloads:
    """
    Tests que les payloads de _log_event() ne contiennent pas de PII.
    
    Patterns PII détectés:
    - Emails: user@example.com
    - Numéros longs: SSN, téléphones (9+ chiffres)
    - URLs avec données: https://...?user=...
    """
    
    PII_PATTERNS = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "long_number": re.compile(r'\b\d{9,}\b'),
        "ssn_format": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "phone_format": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        "url_with_params": re.compile(r'https?://[^\s]+[?&](user|email|token|key|password)='),
    }
    
    @pytest.mark.asyncio
    async def test_log_event_no_email_leak(self, config, context):
        """_log_event ne doit pas contenir d'emails."""
        import json
        from io import StringIO
        import logging
        
        # Capture les logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        meta = Metacognition(config)
        meta._logger.addHandler(handler)
        
        # Exécuter une évaluation
        outcome = make_outcome(confidence=0.5)
        await meta.evaluate(outcome, context)
        
        # Vérifier les logs
        log_output = log_capture.getvalue()
        
        for pattern_name, pattern in self.PII_PATTERNS.items():
            match = pattern.search(log_output)
            assert match is None, \
                f"PII LEAK [{pattern_name}]: trouvé '{match.group()}' dans les logs"
    
    @pytest.mark.asyncio
    async def test_log_event_no_user_query_content(self, config):
        """Le contenu de user_query ne doit pas apparaître dans les logs."""
        import logging
        from io import StringIO
        
        # Query avec contenu identifiable
        sensitive_query = "My password is SuperSecret123 and my email is test@example.com"
        context = ReasoningContext(
            session_id="pii_test",
            user_query=sensitive_query,
        )
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        meta = Metacognition(config)
        meta._logger.addHandler(handler)
        
        outcome = make_outcome(confidence=0.5)
        await meta.evaluate(outcome, context)
        
        log_output = log_capture.getvalue()
        
        # Aucun contenu de la query ne doit être dans les logs
        assert "SuperSecret123" not in log_output, "PASSWORD LEAK dans logs!"
        assert "test@example.com" not in log_output, "EMAIL LEAK dans logs!"
        assert "My password" not in log_output, "USER CONTENT LEAK dans logs!"
    
    def test_to_safe_dict_no_pii_patterns(self, config):
        """to_safe_dict() ne contient aucun pattern PII."""
        from python.helpers.metacognition import MetaDecision, ConfidenceAnalysis
        
        # Créer un decision avec des données simulées
        decision = MetaDecision(
            confidence=0.5,
            confidence_analysis=ConfidenceAnalysis(
                overall=0.5,
                level=ConfidenceLevel.MEDIUM,
                factors={"test": 0.5},
                signals=[],
            ),
            uncertainty_reasons=["reason 1", "reason 2"],
            escalation=EscalationType.NONE,
            clarification_questions=["question?"],
            memory_hints=[],
            should_retry=False,
            debug_id="test_123",
        )
        
        safe_dict = decision.to_safe_dict()
        safe_str = str(safe_dict)
        
        for pattern_name, pattern in self.PII_PATTERNS.items():
            match = pattern.search(safe_str)
            assert match is None, \
                f"PII PATTERN [{pattern_name}] trouvé dans to_safe_dict: {match.group()}"


# ============================================================================
# T8: EXCEPTION SANITIZATION (sanitize_exception)
# ============================================================================

class TestExceptionSanitization:
    """
    Tests que sanitize_exception() supprime correctement les PII des exceptions.
    
    Vérifie que les patterns suivants sont remplacés:
    - Emails -> [EMAIL]
    - SSN -> [SSN]
    - Phones -> [PHONE]
    - Long numbers -> [LONG_NUMBER]
    - URLs -> [URL]
    - Passwords -> [PASSWORD_REDACTED]
    """
    
    def test_sanitize_exception_removes_email(self):
        """sanitize_exception supprime les emails."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = ValueError("Failed for user john.doe@company.com: invalid input")
        result = sanitize_exception(exc)
        
        assert "john.doe@company.com" not in result["message"], \
            f"EMAIL non sanitizé: {result['message']}"
        assert "[EMAIL]" in result["message"], \
            f"EMAIL non remplacé par placeholder: {result['message']}"
        assert result["error_type"] == "ValueError"
    
    def test_sanitize_exception_removes_ssn(self):
        """sanitize_exception supprime les SSN (format xxx-xx-xxxx)."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = RuntimeError("User SSN 123-45-6789 is invalid")
        result = sanitize_exception(exc)
        
        assert "123-45-6789" not in result["message"], \
            f"SSN non sanitizé: {result['message']}"
        assert "[SSN]" in result["message"]
    
    def test_sanitize_exception_removes_phone(self):
        """sanitize_exception supprime les numéros de téléphone."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = Exception("Contact at 555-123-4567 failed")
        result = sanitize_exception(exc)
        
        assert "555-123-4567" not in result["message"], \
            f"PHONE non sanitizé: {result['message']}"
        assert "[PHONE]" in result["message"]
    
    def test_sanitize_exception_removes_long_numbers(self):
        """sanitize_exception supprime les nombres longs (>= 9 chiffres)."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = ValueError("Account 1234567890123456 not found")
        result = sanitize_exception(exc)
        
        assert "1234567890123456" not in result["message"], \
            f"LONG_NUMBER non sanitizé: {result['message']}"
        assert "[LONG_NUMBER]" in result["message"]
    
    def test_sanitize_exception_removes_url(self):
        """sanitize_exception supprime les URLs."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = ConnectionError("Failed to connect to https://api.secret.com/v1/users?token=abc123")
        result = sanitize_exception(exc)
        
        assert "https://api.secret.com" not in result["message"], \
            f"URL non sanitizé: {result['message']}"
        assert "[URL]" in result["message"]
    
    def test_sanitize_exception_removes_password(self):
        """sanitize_exception supprime les passwords dans les messages."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = AuthenticationError("password='MySecretPass123' is wrong")
        result = sanitize_exception(exc)
        
        assert "MySecretPass123" not in result["message"], \
            f"PASSWORD non sanitizé: {result['message']}"
        assert "[PASSWORD_REDACTED]" in result["message"]
    
    def test_sanitize_exception_truncates_long_messages(self):
        """sanitize_exception tronque les messages longs."""
        from python.helpers.metacognition import sanitize_exception
        
        long_message = "A" * 500
        exc = Exception(long_message)
        result = sanitize_exception(exc, max_length=100)
        
        assert len(result["message"]) <= 103  # 100 + "..."
        assert result["message"].endswith("...")
    
    def test_sanitize_exception_combined_pii(self):
        """sanitize_exception gère plusieurs PII dans le même message."""
        from python.helpers.metacognition import sanitize_exception
        
        exc = ValueError(
            "User john@example.com (SSN: 123-45-6789, phone: 555-123-4567) "
            "tried to access https://admin.secret.com"
        )
        result = sanitize_exception(exc)
        
        # Aucun PII ne doit rester
        assert "john@example.com" not in result["message"]
        assert "123-45-6789" not in result["message"]
        assert "555-123-4567" not in result["message"]
        assert "https://admin.secret.com" not in result["message"]
        
        # Tous les placeholders doivent être présents
        assert "[EMAIL]" in result["message"]
        assert "[SSN]" in result["message"]
        assert "[PHONE]" in result["message"]
        assert "[URL]" in result["message"]


class AuthenticationError(Exception):
    """Exception de test pour l'authentification."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
