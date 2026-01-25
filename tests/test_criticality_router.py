"""
Tests pour CriticalityRouter — Détection de domaine critique.

Coverage:
- Détection domaine LEGAL/MEDICAL/SCIENTIFIC
- Profils agents critiques (legal_safe, researcher)
- Actions critiques (publish, recommend, diagnose)
- Mode production vs dev
"""

import os
import pytest
from unittest.mock import patch

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityAssessment,
    CriticalDomain,
    DecisionTypeForDomain,
    CONSENSUS_REQUIRED_PROFILES,
    get_criticality_router,
    assess_criticality,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def router():
    """Router frais pour chaque test."""
    return CriticalityRouter(is_production=False)


@pytest.fixture
def prod_router():
    """Router en mode production."""
    return CriticalityRouter(is_production=True)


# ═══════════════════════════════════════════════════════════════════════════════
# T1: PROFILS AGENTS CRITIQUES
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentProfileConsensus:
    """Vérifie que legal_safe et researcher requièrent TOUJOURS consensus."""
    
    def test_legal_safe_always_requires_consensus(self, router):
        """legal_safe → consensus obligatoire, même query banale."""
        assessment = router.assess(
            query="What time is it?",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is True
        assert assessment.strict_evidence_mode is True
        assert assessment.domain == CriticalDomain.LEGAL
    
    def test_researcher_always_requires_consensus(self, router):
        """researcher → consensus obligatoire."""
        assessment = router.assess(
            query="Hello world",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is True
        assert assessment.domain == CriticalDomain.SCIENTIFIC
    
    def test_legal_safe_cannot_bypass(self, prod_router):
        """legal_safe ne peut JAMAIS bypasser en prod."""
        assessment = prod_router.assess(
            query="Simple question",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is True
        assert assessment.can_bypass is False
    
    def test_default_profile_no_consensus_for_simple_query(self, router):
        """Profil default sur query simple → pas de consensus."""
        assessment = router.assess(
            query="What is the weather today?",
            agent_profile="default",
        )
        assert assessment.requires_consensus is False
    
    def test_consensus_required_profiles_constant(self):
        """Vérifie que les profils critiques sont bien définis."""
        assert "legal_safe" in CONSENSUS_REQUIRED_PROFILES
        assert "researcher" in CONSENSUS_REQUIRED_PROFILES


# ═══════════════════════════════════════════════════════════════════════════════
# T2: DÉTECTION DE DOMAINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainDetection:
    """Vérifie la détection de domaines critiques."""
    
    def test_legal_domain_detected_english(self, router):
        """Détection domaine LEGAL en anglais."""
        assessment = router.assess(
            query="Is this contract legally binding?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is True
    
    def test_legal_domain_detected_french(self, router):
        """Détection domaine LEGAL en français."""
        assessment = router.assess(
            query="Ce contrat est-il juridiquement valide?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is True
    
    def test_medical_domain_detected(self, router):
        """Détection domaine MEDICAL."""
        assessment = router.assess(
            query="What are the symptoms of diabetes?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is True
    
    def test_scientific_domain_detected(self, router):
        """Détection domaine SCIENTIFIC."""
        assessment = router.assess(
            query="What does the peer-reviewed research say about climate change?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.SCIENTIFIC
        assert assessment.requires_consensus is True
    
    def test_finance_high_risk_detected(self, router):
        """Détection FINANCE_HIGH_RISK."""
        assessment = router.assess(
            query="Should I invest in cryptocurrency?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.FINANCE_HIGH_RISK
        assert assessment.requires_consensus is True
    
    def test_default_domain_for_simple_query(self, router):
        """Query simple → DEFAULT."""
        assessment = router.assess(
            query="What is the capital of France?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.DEFAULT
        assert assessment.requires_consensus is False


# ═══════════════════════════════════════════════════════════════════════════════
# T3: ACTIONS CRITIQUES
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriticalActions:
    """Vérifie la détection d'actions critiques."""
    
    def test_publish_triggers_consensus(self, router):
        """Action 'publish' → consensus."""
        assessment = router.assess(
            query="Please publish this article",
            agent_profile="default",
        )
        assert assessment.requires_consensus is True
    
    def test_recommend_triggers_consensus(self, router):
        """Action 'recommend' → consensus."""
        assessment = router.assess(
            query="I recommend this treatment",
            agent_profile="default",
        )
        assert assessment.requires_consensus is True
    
    def test_diagnose_triggers_consensus(self, router):
        """Action 'diagnose' → consensus."""
        assessment = router.assess(
            query="Can you diagnose this condition?",
            agent_profile="default",
        )
        assert assessment.requires_consensus is True
    
    def test_conclude_triggers_consensus(self, router):
        """Action 'conclude' → consensus."""
        assessment = router.assess(
            query="Based on this, I conclude that...",
            agent_profile="default",
        )
        assert assessment.requires_consensus is True
    
    def test_validate_triggers_consensus(self, router):
        """Action 'validate' → consensus."""
        assessment = router.assess(
            query="Please validate this claim",
            agent_profile="default",
        )
        assert assessment.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# T4: FORCE CONSENSUS
# ═══════════════════════════════════════════════════════════════════════════════

class TestForceConsensus:
    """Vérifie le flag force_consensus."""
    
    def test_force_consensus_true(self, router):
        """force_consensus=True → consensus même sur query simple."""
        assessment = router.assess(
            query="Hello",
            agent_profile="default",
            force_consensus=True,
        )
        assert assessment.requires_consensus is True
    
    def test_force_consensus_overrides_detection(self, router):
        """force_consensus=True prend le dessus."""
        assessment = router.assess(
            query="Simple non-critical query",
            agent_profile="developer",
            force_consensus=True,
        )
        assert assessment.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# T5: STRICT EVIDENCE MODE
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrictEvidenceMode:
    """Vérifie l'activation du mode strict evidence."""
    
    def test_legal_strict_evidence(self, router):
        """LEGAL → strict evidence mode."""
        assessment = router.assess(
            query="Legal contract question",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_medical_strict_evidence(self, router):
        """MEDICAL → strict evidence mode."""
        assessment = router.assess(
            query="Medical diagnosis question",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_scientific_strict_evidence(self, router):
        """SCIENTIFIC → strict evidence mode."""
        assessment = router.assess(
            query="Scientific research question",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_default_no_strict_evidence(self, router):
        """DEFAULT → pas de strict evidence."""
        assessment = router.assess(
            query="What is 2+2?",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is False


# ═══════════════════════════════════════════════════════════════════════════════
# T6: CONVENIENCE METHODS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    """Vérifie les méthodes de convenance."""
    
    def test_should_require_consensus(self, router):
        """should_require_consensus() retourne bool."""
        assert router.should_require_consensus("Legal question", "legal_safe") is True
        assert router.should_require_consensus("Hello", "default") is False
    
    def test_detect_domain(self, router):
        """detect_domain() retourne le domaine."""
        domain = router.detect_domain("Medical symptoms question")
        assert domain == CriticalDomain.MEDICAL
    
    def test_decision_type_for(self, router):
        """decision_type_for() retourne le bon type."""
        dt = router.decision_type_for(CriticalDomain.LEGAL)
        assert dt == DecisionTypeForDomain.LEGAL_DECISION


# ═══════════════════════════════════════════════════════════════════════════════
# T7: SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Vérifie le pattern singleton."""
    
    def test_get_criticality_router_singleton(self):
        """get_criticality_router() retourne la même instance."""
        router1 = get_criticality_router()
        router2 = get_criticality_router()
        assert router1 is router2
    
    def test_assess_criticality_function(self):
        """assess_criticality() est un raccourci fonctionnel."""
        assessment = assess_criticality(
            query="Legal question",
            agent_profile="legal_safe",
        )
        assert isinstance(assessment, CriticalityAssessment)
        assert assessment.requires_consensus is True
