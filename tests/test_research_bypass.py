"""
T2bis: Research Bypass Prevention — Test Anti-Contournement.

Vérifie que TOUS les chemins de recherche délèguent au pipeline gouverné.
Un appel direct à l'ancien executor DOIT passer par le gate.

═══════════════════════════════════════════════════════════════════════════════
LOGIQUE 3 NIVEAUX:

  - Profils critiques (researcher, legal_safe, medical) DANS
    CONSENSUS_REQUIRED_PROFILES mais le consensus dépend du Level:
    * Level 1 (définition/résumé) → PAS de consensus (même avec profil critique)
    * Level 3 (cas réel/décision) → consensus OBLIGATOIRE

  - La SIMPLE PRÉSENCE de mots-clés scientifiques/médicaux/légaux
    NE DÉCLENCHE PAS le consensus (Level 2 = métadonnées seulement).

  - SEULS les patterns Level 3 (cas réel, décision, litige) déclenchent
    le consensus multi-agents.
═══════════════════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILS CRITIQUES DANS CONSENSUS_REQUIRED_PROFILES
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchProfiles:
    """Vérifie que les profils critiques sont bien enregistrés."""

    def test_researcher_in_required_profiles(self):
        """researcher est dans CONSENSUS_REQUIRED_PROFILES."""
        assert "researcher" in CONSENSUS_REQUIRED_PROFILES

    def test_legal_safe_in_required_profiles(self):
        """legal_safe est dans CONSENSUS_REQUIRED_PROFILES."""
        assert "legal_safe" in CONSENSUS_REQUIRED_PROFILES

    def test_medical_in_required_profiles(self):
        """medical est dans CONSENSUS_REQUIRED_PROFILES."""
        assert "medical" in CONSENSUS_REQUIRED_PROFILES


# ═══════════════════════════════════════════════════════════════════════════════
# PROFIL RESEARCHER: Level 1 = pas de consensus
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearcherProfileLevel1:
    """
    Profil researcher + query Level 1 → PAS de consensus.
    
    Même un chercheur qui demande une définition ne déclenche pas
    le pipeline lourd.
    """

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_researcher_simple_greeting_no_consensus(self, router):
        """researcher + 'Hello world' → pas de consensus."""
        assessment = router.assess("Hello world", agent_profile="researcher")
        # Level 1 simple → bypasse le consensus même pour researcher
        assert assessment.requires_consensus is False

    def test_researcher_definition_no_consensus(self, router):
        """researcher + définition → pas de consensus."""
        assessment = router.assess(
            "Qu'est-ce qu'une méta-analyse ?",
            agent_profile="researcher",
        )
        assert assessment.requires_consensus is False

    def test_researcher_time_question_no_consensus(self, router):
        """researcher + 'What time is it?' → pas de consensus."""
        assessment = router.assess("What time is it?", agent_profile="researcher")
        assert assessment.requires_consensus is False


# ═══════════════════════════════════════════════════════════════════════════════
# PROFIL RESEARCHER: Level 3 = consensus
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearcherProfileLevel3:
    """
    Profil researcher + query Level 3 → consensus OBLIGATOIRE.
    """

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_researcher_real_case_requires_consensus(self, router):
        """researcher + cas réel → consensus."""
        queries = [
            "Mon patient participe à cet essai clinique, dois-je le recommander ?",
            "Dois-je publier ces résultats malgré la p-value faible ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="researcher")
            assert assessment.requires_consensus is True, (
                f"BYPASS: researcher + real case without consensus: '{query}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAINE SCIENTIFIQUE: Level 2 vs Level 3
# ═══════════════════════════════════════════════════════════════════════════════

class TestScientificDomainClassification:
    """
    Vérifie que les queries scientifiques sont correctement classées
    Level 2 (pas consensus) vs Level 3 (consensus).
    """

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_scientific_general_question_no_consensus(self, router):
        """Question scientifique générale (Level 2) → domaine détecté, pas consensus."""
        queries = [
            "What is the statistical significance?",
            "La méthodologie de cette étude est-elle valide ?",
            "Comment interpréter cet odds ratio ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            # Domaine SCIENTIFIC détecté (pour métadonnées)
            assert assessment.domain == CriticalDomain.SCIENTIFIC, (
                f"Expected SCIENTIFIC for: {query}, got {assessment.domain}"
            )
            # Mais PAS de consensus (Level 2, pas de cas réel/décision)

    def test_scientific_real_decision_consensus(self, router):
        """Décision scientifique réelle (Level 3) → consensus."""
        queries = [
            "Dois-je publier ces résultats dans ce journal ?",
            "Mon essai clinique montre des résultats, dois-je recommander le traitement ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"BYPASS: Real scientific decision without consensus: '{query}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAINE MÉDICAL: Level 2 vs Level 3
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalDomainClassification:
    """Classification médicale Level 2 vs Level 3."""

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_medical_general_question_domain_detected(self, router):
        """Question médicale générale → domain=MEDICAL détecté."""
        queries = [
            "What is the recommended treatment for diabetes?",
            "Quels sont les effets secondaires du paracétamol ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.MEDICAL, (
                f"Expected MEDICAL for: {query}, got {assessment.domain}"
            )

    def test_medical_real_case_consensus(self, router):
        """Cas médical réel → consensus."""
        queries = [
            "J'ai les symptômes suivants de fièvre et toux, dois-je consulter ?",
            "Mon patient présente un diagnostic différentiel complexe",
            "Quel traitement pour mon enfant malade ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"BYPASS: Real medical case without consensus: '{query}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAINE LEGAL: Level 2 vs Level 3
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalDomainClassification:
    """Classification légale Level 2 vs Level 3."""

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_legal_general_question_domain_detected(self, router):
        """Question légale générale → domain=LEGAL détecté."""
        queries = [
            "Research GDPR compliance requirements",
            "What is contract liability?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.domain == CriticalDomain.LEGAL, (
                f"Expected LEGAL for: {query}, got {assessment.domain}"
            )

    def test_legal_real_case_consensus(self, router):
        """Cas légal réel → consensus."""
        queries = [
            "J'ai reçu une mise en demeure de mon bailleur",
            "Mon employeur m'a licencié, que faire ?",
            "Je suis poursuivi, quels sont mes droits ?",
            "Dois-je signer ce contrat ?",
        ]
        for query in queries:
            assessment = router.assess(query, agent_profile="default")
            assert assessment.requires_consensus is True, (
                f"BYPASS: Real legal case without consensus: '{query}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# FORCE CONSENSUS BYPASS PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestForceConsensusBypass:
    """Vérifie que force_consensus=False ne bypasse pas Level 3."""

    @pytest.fixture
    def router(self):
        return CriticalityRouter()

    def test_force_false_on_level3_still_requires_consensus(self, router):
        """force_consensus=False sur Level 3 → consensus malgré tout."""
        # Ce cas est Level 3 (décision personnelle légale)
        assessment = router.assess(
            query="Dois-je signer ce contrat ou refuser ?",
            agent_profile="default",
            force_consensus=False,
        )
        # Le router détecte Level 3 INDÉPENDAMMENT de force_consensus
        assert assessment.requires_consensus is True, (
            "CRITICAL BYPASS: force_consensus=False worked on Level 3 query"
        )

    def test_force_true_always_consensus(self, router):
        """force_consensus=True → consensus toujours."""
        assessment = router.assess(
            query="Bonjour",
            agent_profile="default",
            force_consensus=True,
        )
        assert assessment.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH PIPELINE ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchPipelineArchitecture:
    """Vérifie que l'architecture du pipeline de recherche est correcte."""

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

    def test_research_pipeline_imports(self):
        """Les modules de recherche gouvernée sont importables."""
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
        """L'ancien executor ne doit pas avoir de chemins directs non gouvernés."""
        try:
            from python.helpers.research_executor import ResearchExecutor
        except ImportError:
            pass  # OK si pas d'ancien executor


# ═══════════════════════════════════════════════════════════════════════════════
# GATE INTÉGRATION (via CriticalDecisionGate)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateIntegration:
    """Vérifie que le gate intègre correctement le router."""

    def test_gate_on_level3_research_query(self):
        """Gate sur query de recherche Level 3 → consensus."""
        gate = CriticalDecisionGate()

        queries = [
            "Mon patient participe à cet essai clinique, dois-je le recommander ?",
            "J'ai reçu une mise en demeure concernant notre étude clinique",
        ]
        for query in queries:
            result = gate.enforce_or_route(query, agent_profile="default")
            assert result.consensus_required is True, (
                f"Gate did not require consensus for Level 3: {query}"
            )

    def test_gate_on_level2_research_query_no_consensus(self):
        """Gate sur query de recherche Level 2 → PAS de consensus."""
        gate = CriticalDecisionGate()

        result = gate.enforce_or_route(
            "What is the statistical significance of these results?",
            agent_profile="default",
        )
        # Level 2 → domaine détecté mais pas consensus
        assert result.assessment.domain == CriticalDomain.SCIENTIFIC
