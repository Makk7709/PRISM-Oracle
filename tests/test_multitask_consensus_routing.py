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
    """Vérifie que multitask → legal_safe force le consensus."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=True)
    
    def test_legal_safe_always_requires_consensus(self, router):
        """legal_safe requiert TOUJOURS consensus."""
        assessment = router.assess(
            query="Any query at all",
            agent_profile="legal_safe",
        )
        assert assessment.requires_consensus is True
        assert assessment.can_bypass is False
    
    def test_legal_safe_strict_evidence_mode(self, router):
        """legal_safe active strict evidence mode."""
        assessment = router.assess(
            query="Simple question",
            agent_profile="legal_safe",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_legal_safe_domain_is_legal(self, router):
        """legal_safe → domain LEGAL."""
        assessment = router.assess(
            query="Random query",
            agent_profile="legal_safe",
        )
        assert assessment.domain == CriticalDomain.LEGAL
    
    def test_legal_safe_cannot_bypass_in_production(self, router):
        """legal_safe ne peut jamais bypass en production."""
        assessment = router.assess(
            query="Test",
            agent_profile="legal_safe",
            force_consensus=False,  # Tenter de désactiver
        )
        # Doit toujours être True pour legal_safe
        assert assessment.requires_consensus is True
        assert assessment.can_bypass is False


# ═══════════════════════════════════════════════════════════════════════════════
# T2: MULTITASK → RESEARCHER → CONSENSUS OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultitaskResearcherConsensus:
    """Vérifie que multitask → researcher force le consensus."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=True)
    
    def test_researcher_always_requires_consensus(self, router):
        """researcher requiert TOUJOURS consensus."""
        assessment = router.assess(
            query="Any query",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is True
    
    def test_researcher_domain_is_scientific(self, router):
        """researcher → domain SCIENTIFIC."""
        assessment = router.assess(
            query="Random query",
            agent_profile="researcher",
        )
        assert assessment.domain == CriticalDomain.SCIENTIFIC
    
    def test_researcher_strict_evidence_mode(self, router):
        """researcher active strict evidence mode."""
        assessment = router.assess(
            query="Test",
            agent_profile="researcher",
        )
        assert assessment.strict_evidence_mode is True
    
    def test_researcher_cannot_bypass(self, router):
        """researcher ne peut pas bypass."""
        assessment = router.assess(
            query="Test",
            agent_profile="researcher",
        )
        assert assessment.can_bypass is False


# ═══════════════════════════════════════════════════════════════════════════════
# T3: DÉTECTION DOMAINE → CONSENSUS MÊME SANS DÉLÉGATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainDetectionTriggersConsensus:
    """Vérifie que la détection de domaine critique force le consensus."""
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter(is_production=False)
    
    def test_medical_query_triggers_consensus(self, router):
        """Query médicale → consensus même avec agent=default."""
        assessment = router.assess(
            query="What medication should I take for my headache?",
            agent_profile="default",  # Pas un agent critique
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is True
    
    def test_legal_query_triggers_consensus(self, router):
        """Query juridique → consensus même avec agent=default."""
        assessment = router.assess(
            query="Is this contract legally enforceable?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is True
    
    def test_scientific_query_triggers_consensus(self, router):
        """Query scientifique → consensus même avec agent=default."""
        assessment = router.assess(
            query="What does peer-reviewed research say about this hypothesis?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.SCIENTIFIC
        assert assessment.requires_consensus is True
    
    def test_french_medical_detected(self, router):
        """Détection fonctionne en français."""
        assessment = router.assess(
            query="Quel traitement médical me recommandez-vous?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        assert assessment.requires_consensus is True
    
    def test_french_legal_detected(self, router):
        """Détection juridique en français."""
        assessment = router.assess(
            query="Ce contrat est-il juridiquement valide?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.LEGAL
        assert assessment.requires_consensus is True


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
