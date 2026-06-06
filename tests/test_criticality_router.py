"""
Tests pour CriticalityRouter — Détection de domaine critique.

Coverage:
- Détection domaine LEGAL/MEDICAL/SCIENTIFIC
- Profils agents critiques (legal_safe, researcher)
- Actions critiques (publish, recommend, diagnose)
- Mode production vs dev
"""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityAssessment,
    CriticalDomain,
    DecisionTypeForDomain,
    CONSENSUS_REQUIRED_PROFILES,
    get_criticality_router,
    assess_criticality,
)


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
    """Vérifie que legal_safe et researcher respectent L1/L3."""
    
    def test_legal_safe_level1_bypasses_consensus(self, router):
        """legal_safe + L1 -> no consensus."""
        assessment = router.assess(
            query="What is a contract?",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is False
        assert assessment.strict_evidence_mode is False
        assert assessment.domain == CriticalDomain.LEGAL
    
    def test_researcher_level1_bypasses_consensus(self, router):
        """researcher + L1 -> no consensus."""
        assessment = router.assess(
            query="Define hypothesis testing",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is False
        assert assessment.domain == CriticalDomain.SCIENTIFIC
    
    def test_legal_safe_cannot_bypass(self, prod_router):
        """Debug bypass not allowed in prod."""
        assessment = prod_router.assess(
            query="Define contract",
            agent_profile="legal_safe",
        )
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
        """Domain detected without forcing consensus."""
        assessment = router.assess(
            query="Explain what makes a contract binding.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is False
    
    def test_legal_domain_detected_french(self, router):
        """Domain detected without forcing consensus."""
        assessment = router.assess(
            query="Explique la validite juridique d'un contrat.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is False
    
    def test_medical_domain_detected(self, router):
        """Domain detected without forcing consensus."""
        assessment = router.assess(
            query="Explain symptoms of diabetes.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is False
    
    def test_scientific_domain_detected(self, router):
        """Domain detected without forcing consensus."""
        assessment = router.assess(
            query="Summarize peer-reviewed research on climate change.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.SCIENTIFIC
        assert assessment.requires_consensus is False
    
    def test_finance_high_risk_detected(self, router):
        """Domain detected without forcing consensus."""
        assessment = router.assess(
            query="Explain crypto investment risks.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.FINANCE_HIGH_RISK
        assert assessment.requires_consensus is False
    
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
            query="Dois-je signer ce contrat?",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_medical_strict_evidence(self, router):
        """MEDICAL → strict evidence mode."""
        assessment = router.assess(
            query="Dois-je consulter pour ces symptomes?",
            agent_profile="default",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_scientific_strict_evidence(self, router):
        """SCIENTIFIC → strict evidence mode."""
        assessment = router.assess(
            query="Should I publish this research finding?",
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
# T6: LEVEL 1 DEFINITIONS (NO CONSENSUS)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("query", [
    "Qu'est-ce qu'un contrat synallagmatique?",
    "Définition d'un accord de confidentialité",
    "Que signifie 'faute lourde'?",
    "What is a medical diagnosis?",
    "Define risk management",
    "What is a balance sheet?",
    "C'est quoi un taux d'interet?",
    "Explain the difference between tort and contract",
    "Qu'appelle-t-on jurisprudence?",
    "Define GDPR",
    "What is an insurance premium?",
    "Explain how vaccines work",
    "Define inflation",
    "What is a mortgage?",
    "Qu'est-ce qu'une clause pénale?",
    "Explique la difference entre civil et penal",
    "What is an audit?",
    "Define market volatility",
    "C'est quoi une ordonnance médicale?",
    "Que signifie 'due diligence'?",
])
def test_level1_definitions_bypass_consensus(router, query):
    assessment = router.assess(query=query, agent_profile="default")
    assert assessment.requires_consensus is False


# ═══════════════════════════════════════════════════════════════════════════════
# T7: LEVEL 3 ACTIONABLE (CONSENSUS REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("query", [
    "Dois-je signer ce contrat de travail?",
    "Can I sue my employer for wrongful dismissal?",
    "Should I appeal this court decision?",
    "Je dois contester une mise en demeure, que faire?",
    "Should I invest all my savings in crypto?",
    "Peux-tu diagnostiquer mes symptomes et dire si je dois consulter?",
    "Faut-il publier ces conclusions maintenant?",
    "Quelle decision dois-je prendre pour ce litige?",
    "Puis-je contester cette facture medicale?",
    "Is it safe to approve this security change in production?",
])
def test_level3_actionables_require_consensus(router, query):
    assessment = router.assess(query=query, agent_profile="default")
    assert assessment.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# T6: CONVENIENCE METHODS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    """Vérifie les méthodes de convenance."""
    
    def test_should_require_consensus(self, router):
        """should_require_consensus() retourne bool."""
        assert router.should_require_consensus("Legal question", "legal_safe") is False
        assert router.should_require_consensus("Dois-je signer ce contrat?", "legal_safe") is True
        assert router.should_require_consensus("Hello", "default") is False
    
    def test_detect_domain(self, router):
        """detect_domain() retourne le domaine."""
        domain = router.detect_domain("Medical symptoms question")
        assert domain == CriticalDomain.MEDICAL
    
    def test_decision_type_for(self, router):
        """decision_type_for() retourne le bon type."""
        dt = router.decision_type_for(CriticalDomain.LEGAL)
        assert dt == DecisionTypeForDomain.LEGAL_DECISION


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
            query="Dois-je signer ce contrat?",
            agent_profile="legal_safe",
        )
        assert isinstance(assessment, CriticalityAssessment)
        assert assessment.requires_consensus is True
