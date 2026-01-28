"""
Tests pour le routing consensus dans multitask.

T1: multitask → legal_safe → consensus requis, impossible à bypass
T2: multitask → researcher → consensus requis
T3: Détection domaine médical/juridique → consensus même sans délégation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalDomain,
    assess_criticality,
    CONSENSUS_REQUIRED_PROFILES,
)


# ═══════════════════════════════════════════════════════════════════════════════
# T1: MULTITASK → LEGAL_SAFE → CONSENSUS OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultitaskLegalSafeConsensus:
    """Vérifie que legal_safe respecte L1/L3 routing."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=True)
    
    def test_legal_safe_level1_bypasses_consensus(self, router):
        """legal_safe + L1 simple -> no consensus."""
        assessment = router.assess(
            query="Qu'est-ce qu'un contrat synallagmatique?",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is False
        assert assessment.can_bypass is True
    
    def test_legal_safe_level3_requires_consensus(self, router):
        """legal_safe + L3 action -> consensus required."""
        assessment = router.assess(
            query="Dois-je signer ce contrat de travail?",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is True
        assert assessment.strict_evidence_mode is True
    
    def test_legal_safe_domain_is_legal(self, router):
        """legal_safe → domain LEGAL even without consensus."""
        assessment = router.assess(
            query="Definition d'une clause penale",
            agent_profile="legal_safe",
        )
        assert assessment.domain == CriticalDomain.LEGAL
    
    def test_legal_safe_cannot_bypass_in_production(self, router):
        """L1 bypass is still allowed but no debug bypass in prod."""
        assessment = router.assess(
            query="Test",
            agent_profile="legal_safe",
            force_consensus=False,  # Tenter de désactiver
        )
        assert assessment.can_bypass is False


# ═══════════════════════════════════════════════════════════════════════════════
# T2: MULTITASK → RESEARCHER → CONSENSUS OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultitaskResearcherConsensus:
    """Vérifie que researcher respecte L1/L3 routing."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=True)
    
    def test_researcher_level1_bypasses_consensus(self, router):
        """researcher + L1 simple -> no consensus."""
        assessment = router.assess(
            query="What is a neural network?",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is False
    
    def test_researcher_level3_requires_consensus(self, router):
        """researcher + L3 action -> consensus required."""
        assessment = router.assess(
            query="Should I publish this clinical finding?",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is True
        assert assessment.domain == CriticalDomain.SCIENTIFIC
    
    def test_researcher_strict_evidence_mode(self, router):
        """researcher L3 -> strict evidence mode."""
        assessment = router.assess(
            query="We should publish this study, do you recommend?",
            agent_profile="researcher",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_researcher_cannot_bypass(self, router):
        """researcher cannot debug bypass in prod."""
        assessment = router.assess(
            query="Test",
            agent_profile="researcher",
        )
        assert assessment.can_bypass is False


# ═══════════════════════════════════════════════════════════════════════════════
# T3: DÉTECTION DOMAINE → CONSENSUS MÊME SANS DÉLÉGATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainDetectionTriggersConsensus:
    """Vérifie que le domaine n'entraine pas le consensus sans L3."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=False)
    
    def test_medical_query_no_consensus_for_l2(self, router):
        """Query medical L2 -> no consensus."""
        assessment = router.assess(
            query="Explain common headache medications.",
            agent_profile="default",  # Pas un agent critique
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is False
    
    def test_legal_query_no_consensus_for_l2(self, router):
        """Query legal L2 -> no consensus."""
        assessment = router.assess(
            query="Explain what makes a contract enforceable.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is False
    
    def test_scientific_query_no_consensus_for_l2(self, router):
        """Query scientific L2 -> no consensus."""
        assessment = router.assess(
            query="Summarize peer-reviewed research on this hypothesis.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.SCIENTIFIC
        assert assessment.requires_consensus is False
    
    def test_french_medical_detected(self, router):
        """Detection works in French (no consensus for L2)."""
        assessment = router.assess(
            query="Explique les traitements medicaux courants.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is False
    
    def test_french_legal_detected(self, router):
        """Detection works in French (no consensus for L2)."""
        assessment = router.assess(
            query="Explique la validite d'un contrat.",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is False


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS D'INTÉGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusRoutingIntegration:
    """Tests d'intégration du routing."""
    
    def test_consensus_required_profiles_complete(self):
        """Tous les profils critiques sont dans la liste."""
        assert "legal_safe" in CONSENSUS_REQUIRED_PROFILES
        assert "researcher" in CONSENSUS_REQUIRED_PROFILES
    
    def test_assess_criticality_function(self):
        """La fonction raccourci fonctionne."""
        assessment = assess_criticality(
            query="Legal question",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is True
    
    def test_multiple_triggers_combine(self):
        """Plusieurs triggers combinés."""
        router = CriticalityRouter()
        
        # Query médicale + agent researcher
        assessment = router.assess(
            query="What are the symptoms of this disease?",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is True
        # Peut être MEDICAL ou SCIENTIFIC selon la détection
        assert assessment.domain in [CriticalDomain.MEDICAL, CriticalDomain.SCIENTIFIC]
    
    def test_simple_query_default_agent_no_consensus(self):
        """Query simple + agent default → pas de consensus."""
        router = CriticalityRouter()
        
        assessment = router.assess(
            query="What is the capital of France?",
            agent_profile="default",
        )
        assert assessment.requires_consensus is False
        assert assessment.domain == CriticalDomain.DEFAULT
