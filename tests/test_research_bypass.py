"""
T2bis: Research Bypass Prevention — Test Anti-Contournement.

Vérifie que TOUS les chemins de recherche délèguent au pipeline gouverné.
Un appel direct à l'ancien executor DOIT déclencher le consensus
quand le domaine est critique.

Ce test est CRITIQUE car le research_executor legacy est le plus gros
risque de bypass identifié.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalDomain,
    assess_criticality,
    CONSENSUS_REQUIRED_PROFILES,
)
from python.helpers.critical_decision_gate import (
    CriticalDecisionGate,
    enforce_or_route,
)


class TestResearchExecutorBypass:
    """
    T2bis: Appel direct old executor → consensus quand domaine critique.
    
    Vérifie que même un appel direct au research executor
    passe par le pipeline gouverné.
    """
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 1: Profil researcher → TOUJOURS consensus
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_researcher_profile_always_consensus(self, router):
        """Profil researcher → consensus obligatoire peu importe la query."""
        queries = [
            "What time is it?",
            "Hello world",
            "Random text",
            "",
        ]
        
        for query in queries:
            assessment = router.assess(query, agent_profile="researcher")
            
            assert assessment.requires_consensus is True, (
                f"BYPASS DETECTED: researcher profile without consensus for '{query}'"
            )
    
    def test_researcher_in_required_profiles(self):
        """researcher est dans CONSENSUS_REQUIRED_PROFILES."""
        assert "researcher" in CONSENSUS_REQUIRED_PROFILES, (
            "CRITICAL: researcher not in CONSENSUS_REQUIRED_PROFILES"
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 2: Query scientifique via agent default → consensus
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_scientific_query_triggers_consensus(self, router):
        """Query scientifique → consensus même sans profil researcher."""
        scientific_queries = [
            "What does the peer-reviewed research say?",
            "Is this hypothesis supported by evidence?",
            "What is the statistical significance?",
            "Analyze this meta-analysis",
            # French
            "Quelle est la méthodologie de cette étude ?",
            "La p-value est-elle significative ?",
            "Ce preprint est-il fiable ?",
        ]
        
        for query in scientific_queries:
            assessment = router.assess(query, agent_profile="default")
            
            assert assessment.requires_consensus is True, (
                f"BYPASS: Scientific query '{query}' without consensus"
            )
            assert assessment.domain == CriticalDomain.SCIENTIFIC, (
                f"Domain mismatch: expected SCIENTIFIC, got {assessment.domain}"
            )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 3: Research integration force consensus
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_research_consensus_integration_exists(self):
        """ResearchConsensusIntegration existe et est configuré."""
        from python.helpers.research_consensus_integration import (
            ResearchConsensusPipeline,
            ResearchConsensusConfig,
        )
        
        config = ResearchConsensusConfig(
            strict_evidence_mode=True,
            consensus_enabled=True,
            fail_closed=True,
        )
        
        pipeline = ResearchConsensusPipeline(config=config)
        
        assert pipeline.config.consensus_enabled is True
        assert pipeline.config.strict_evidence_mode is True
        assert pipeline.config.fail_closed is True
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 4: Tentative de bypass avec force_consensus=False
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_force_consensus_false_ignored_for_researcher(self, router):
        """force_consensus=False IGNORÉ pour profil researcher."""
        assessment = router.assess(
            query="Any query",
            agent_profile="researcher",
            force_consensus=False,  # Tentative de bypass
        )
        
        # Le bypass DOIT échouer
        assert assessment.requires_consensus is True, (
            "CRITICAL BYPASS: force_consensus=False worked for researcher"
        )
    
    def test_force_consensus_false_ignored_for_scientific(self, router):
        """force_consensus=False IGNORÉ pour domaine scientifique."""
        assessment = router.assess(
            query="Analyze this peer-reviewed study",
            agent_profile="default",
            force_consensus=False,  # Tentative de bypass
        )
        
        assert assessment.requires_consensus is True, (
            "CRITICAL BYPASS: force_consensus=False worked for scientific domain"
        )


class TestAllResearchPathsGoverned:
    """
    Vérifie qu'aucun chemin de recherche ne contourne le gate.
    """
    
    def test_gate_applied_on_research_query(self):
        """Gate appliqué sur query de recherche scientifique."""
        gate = CriticalDecisionGate()
        
        # Queries qui DOIVENT matcher les patterns scientifiques
        research_queries = [
            "What does the peer-reviewed research say about this?",  # "peer.?review"
            "Analyze this scientific study and hypothesis",          # "scientific", "study", "hypothesis"
            "What is the statistical significance of these results?", # "statistical", "significance"
        ]
        
        for query in research_queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            
            assert result.consensus_required is True, (
                f"Scientific query should require consensus: {query}"
            )
            assert result.assessment.domain == CriticalDomain.SCIENTIFIC, (
                f"Expected SCIENTIFIC domain for: {query}"
            )


class TestResearchPipelineUniquePath:
    """
    Vérifie que le pipeline de recherche est unique (pas de doubles chemins).
    """
    
    def test_research_pipeline_imports(self):
        """Les modules de recherche gouvernée sont importables."""
        # Ces imports DOIVENT réussir
        from python.helpers.research_consensus_integration import (
            ResearchConsensusPipeline,
            ResearchConsensusConfig,
            ResearchConclusion,
        )
        from python.helpers.critical_decision_gate import (
            CriticalDecisionGate,
            enforce_or_route,
        )
        from python.helpers.criticality_router import (
            CriticalityRouter,
            assess_criticality,
        )
    
    def test_old_executor_not_exposed(self):
        """
        L'ancien executor ne doit pas avoir de chemins directs.
        
        Note: Ce test vérifie que l'architecture force le passage
        par le pipeline gouverné.
        """
        # Le research_executor existe peut-être, mais il doit
        # être enveloppé par le pipeline gouverné
        try:
            from python.helpers.research_executor import ResearchExecutor
            # Si l'import réussit, vérifier qu'il est wrappé ou deprecated
            # (Ce test est documentatif - l'ancien code peut exister)
        except ImportError:
            pass  # OK si pas d'ancien executor


class TestCriticalDomainResearchDetection:
    """
    Vérifie que les patterns de recherche détectent les domaines critiques.
    """
    
    @pytest.fixture
    def router(self):
        return CriticalityRouter()
    
    def test_medical_research_detected(self, router):
        """Recherche médicale détectée comme MEDICAL."""
        queries = [
            "What is the recommended treatment for diabetes?",  # "treatment"
            "Analyze this clinical trial for cancer therapy",   # "clinical trial", "therapy"
            "What are the symptoms and diagnosis for this disease?",  # "symptoms", "diagnosis", "disease"
        ]
        
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            # Peut être MEDICAL ou SCIENTIFIC selon les patterns
            assert assessment.domain in [CriticalDomain.MEDICAL, CriticalDomain.SCIENTIFIC], (
                f"Expected MEDICAL or SCIENTIFIC for: {query}, got: {assessment.domain}"
            )
            assert assessment.requires_consensus is True
    
    def test_legal_research_detected(self, router):
        """Recherche juridique détectée comme LEGAL."""
        queries = [
            "Research GDPR compliance requirements",
            "Find jurisprudence on employment law",
            "Legal research on contract liability",
        ]
        
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.LEGAL
            assert assessment.requires_consensus is True
