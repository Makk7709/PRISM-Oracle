"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               TESTS — STRATEGIC DOCUMENT ORCHESTRATOR                        ║
║                                                                              ║
║  Tests du pipeline d'orchestration multi-agent pour documents stratégiques.  ║
║                                                                              ║
║  Vérifie:                                                                    ║
║  - Détection des types de documents                                          ║
║  - Comptage des sources                                                      ║
║  - Validation du contenu                                                     ║
║  - Génération des prompts agents                                             ║
║  - Réponses FAIL_CLOSED                                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.strategic_orchestrator import (
    detect_strategic_document,
    count_sources,
    validate_strategic_content,
    get_agent_prompt,
    consolidate_responses,
    create_fail_closed_response,
    is_strategic_orchestrator_enabled,
    StrategicDetection,
    AgentResponse,
    STRATEGIC_PATTERNS,
    REQUIRED_AGENTS,
    MIN_SOURCES,
)


class TestStrategicDocumentDetection:
    """Tests for strategic document detection."""
    
    def test_detect_market_study_french(self):
        """Test detection of French market study request."""
        query = "Génère une étude de marché pour ma startup"
        result = detect_strategic_document(query)
        
        assert result.is_strategic
        assert result.document_type == "market_study"
        assert "researcher" in result.required_agents
        assert "finance" in result.required_agents
        assert result.min_sources >= 3
    
    def test_detect_financial_forecast(self):
        """Test detection of financial forecast request."""
        query = "Fais moi un prévisionnel financier sur 5 ans"
        result = detect_strategic_document(query)
        
        assert result.is_strategic
        assert result.document_type == "financial_forecast"
        assert "finance" in result.required_agents
    
    def test_detect_pricing_strategy(self):
        """Test detection of pricing strategy request."""
        query = "Propose une stratégie de pricing pour notre SaaS"
        result = detect_strategic_document(query)
        
        assert result.is_strategic
        assert result.document_type == "pricing"
    
    def test_detect_gtm_plan(self):
        """Test detection of go-to-market request."""
        query = "Définis notre stratégie GTM pour le lancement"
        result = detect_strategic_document(query)
        
        assert result.is_strategic
        assert result.document_type == "go_to_market"
        assert "marketing" in result.required_agents
    
    def test_non_strategic_query(self):
        """Test that non-strategic queries are correctly identified."""
        queries = [
            "Quelle est la capitale de la France?",
            "Explique-moi le machine learning",
            "Comment faire une omelette?",
        ]
        
        for query in queries:
            result = detect_strategic_document(query)
            assert not result.is_strategic, f"'{query}' should not be strategic"


class TestSourceCounting:
    """Tests for source counting functionality."""
    
    def test_count_ref_citations(self):
        """Test counting [REF-XX] citations."""
        text = "Le marché vaut 500M$ [REF-01] et croît de 15% [REF-02]"
        count = count_sources(text)
        assert count >= 2
    
    def test_count_institutional_sources(self):
        """Test counting institutional source names."""
        text = "Selon Gartner et McKinsey, le marché européen (Eurostat 2024)"
        count = count_sources(text)
        assert count >= 3
    
    def test_count_urls(self):
        """Test counting URL sources."""
        text = "See https://example.com/report and https://data.gov"
        count = count_sources(text)
        assert count >= 2
    
    def test_count_year_citations(self):
        """Test counting year citations."""
        text = "Market report (2024) shows growth (2023)"
        count = count_sources(text)
        assert count >= 2
    
    def test_empty_text_returns_zero(self):
        """Test that empty text returns zero sources."""
        assert count_sources("") == 0


class TestContentValidation:
    """Tests for strategic content validation."""
    
    def test_valid_market_study_passes(self):
        """Test that properly sourced market study passes validation."""
        text = """
        TAM: 500 Md$ selon Gartner [REF-01]
        SAM: 50 Md$ (Europe) [REF-02]
        SOM: 5 Md$ (France) [REF-03]
        Source: Eurostat, McKinsey 2024
        Hypothèse: croissance 10%/an
        Alternative écartée: marché US car barrières réglementaires
        """
        is_valid, missing = validate_strategic_content(text, "market_study", 3)
        assert is_valid, f"Should pass, got missing: {missing}"
    
    def test_unsourced_market_study_fails(self):
        """Test that unsourced market study fails validation."""
        text = "Le marché est énorme. On va réussir. Go!"
        is_valid, missing = validate_strategic_content(text, "market_study", 3)
        
        assert not is_valid
        assert any("Sources" in m for m in missing)
    
    def test_missing_tam_fails(self):
        """Test that missing TAM fails for market study."""
        text = """
        SAM: 50 Md$ [REF-01]
        SOM: 5 Md$ [REF-02]
        Source: Gartner, McKinsey
        Hypothèse: croissance stable
        Alternative écartée: autre segment
        """
        is_valid, missing = validate_strategic_content(text, "market_study", 2)
        
        assert not is_valid
        assert any("TAM" in m for m in missing)
    
    def test_missing_alternatives_fails(self):
        """Test that missing alternatives fails validation."""
        text = """
        TAM: 500 Md$ [REF-01]
        SAM: 50 Md$ [REF-02]
        SOM: 5 Md$ [REF-03]
        Source: Gartner 2024
        """
        is_valid, missing = validate_strategic_content(text, "market_study", 3)
        
        assert not is_valid
        assert any("Alternative" in m for m in missing)

    def test_alternatives_detected_via_synonym_benchmark(self):
        """Test that 'benchmarking' satisfies the alternatives check."""
        text = """
        Benchmarking des solutions du marché [REF-01]
        Source: Eurostat 2024 [REF-02] [REF-03]
        """
        is_valid, missing = validate_strategic_content(text, "strategic_dossier", 3)
        assert not any("Alternative" in m for m in missing)

    def test_alternatives_detected_via_synonym_concurrent(self):
        """Test that 'concurrentiel' satisfies the alternatives check."""
        text = """
        Analyse concurrentielle du secteur [REF-01]
        Source: INSEE 2024 [REF-02] [REF-03]
        """
        is_valid, missing = validate_strategic_content(text, "strategic_dossier", 3)
        assert not any("Alternative" in m for m in missing)

    def test_alternatives_detected_via_synonym_swot(self):
        """Test that 'SWOT' satisfies the alternatives check."""
        text = """
        SWOT du positionnement [REF-01]
        Source: Bpifrance 2024 [REF-02] [REF-03]
        """
        is_valid, missing = validate_strategic_content(text, "strategic_dossier", 3)
        assert not any("Alternative" in m for m in missing)

    def test_alternatives_detected_via_comparaison(self):
        """Test that 'comparaison' (French) satisfies the alternatives check."""
        text = """
        Comparaison des acteurs du marché [REF-01]
        Source: IDC Europe 2024 [REF-02] [REF-03]
        """
        is_valid, missing = validate_strategic_content(text, "strategic_dossier", 3)
        assert not any("Alternative" in m for m in missing)

    def test_alternatives_detected_via_vs(self):
        """Test that 'vs' satisfies the alternatives check."""
        text = """
        Solution A vs Solution B [REF-01]
        Source: Gartner Europe 2024 [REF-02] [REF-03]
        """
        is_valid, missing = validate_strategic_content(text, "strategic_dossier", 3)
        assert not any("Alternative" in m for m in missing)


class TestAgentPrompts:
    """Tests for agent prompt generation."""
    
    def test_researcher_prompt_has_sourcing_requirements(self):
        """Test that researcher prompt includes sourcing requirements."""
        prompt = get_agent_prompt(
            document_type="market_study",
            agent_profile="researcher",
            user_query="Analyse le marché SaaS B2B",
            previous_responses=[],
        )
        
        assert "REF-" in prompt.lower() or "source" in prompt.lower()
        assert "recherch" in prompt.lower() or "research" in prompt.lower()
    
    def test_finance_prompt_has_hypothesis_requirements(self):
        """Test that finance prompt includes hypothesis requirements."""
        prompt = get_agent_prompt(
            document_type="financial_forecast",
            agent_profile="finance",
            user_query="Crée un prévisionnel",
            previous_responses=[],
        )
        
        assert "hypothèse" in prompt.lower() or "hypothesis" in prompt.lower()
    
    def test_prompt_includes_previous_responses(self):
        """Test that prompts include previous agent responses."""
        previous = [
            AgentResponse(
                agent_name="Evidence-researcher",
                profile="researcher",
                response="TAM: 500M$ selon Gartner",
                sources_count=1,
                duration_ms=100,
                success=True,
            )
        ]
        
        prompt = get_agent_prompt(
            document_type="market_study",
            agent_profile="finance",
            user_query="Analyse",
            previous_responses=previous,
        )
        
        assert "researcher" in prompt.lower() or "précédent" in prompt.lower()


class TestResponseConsolidation:
    """Tests for response consolidation."""
    
    def test_consolidation_includes_all_agents(self):
        """Test that consolidated response includes all agent contributions."""
        responses = [
            AgentResponse(
                agent_name="Evidence-researcher",
                profile="researcher",
                response="Market data: 500M$ [REF-01]",
                sources_count=1,
                duration_ms=100,
                success=True,
            ),
            AgentResponse(
                agent_name="Evidence-finance",
                profile="finance",
                response="Financial analysis [REF-02]",
                sources_count=1,
                duration_ms=100,
                success=True,
            ),
        ]
        
        consolidated = consolidate_responses(
            responses=responses,
            document_type="market_study",
            query="Test query",
            correlation_id="test-123",
        )
        
        assert "researcher" in consolidated.lower()
        assert "finance" in consolidated.lower()
        assert "test-123" in consolidated
    
    def test_consolidation_has_governance_section(self):
        """Test that consolidated response has governance section."""
        responses = []
        consolidated = consolidate_responses(
            responses=responses,
            document_type="market_study",
            query="Test",
            correlation_id="test-456",
        )
        
        assert "Governance" in consolidated or "governance" in consolidated.lower()


class TestFailClosedResponse:
    """Tests for FAIL_CLOSED response generation."""
    
    def test_fail_closed_lists_missing_requirements(self):
        """Test that FAIL_CLOSED response lists missing requirements."""
        detection = StrategicDetection(
            is_strategic=True,
            document_type="market_study",
            patterns_matched=["étude de marché"],
            required_agents=["researcher", "finance"],
            min_sources=5,
        )
        
        responses = [
            AgentResponse(
                agent_name="Evidence-researcher",
                profile="researcher",
                response="Some analysis without sources",
                sources_count=0,
                duration_ms=100,
                success=True,
            ),
        ]
        
        missing = ["Sources insuffisantes (0/5)", "TAM non chiffré"]
        
        fail_response = create_fail_closed_response(
            detection=detection,
            responses=responses,
            missing=missing,
            correlation_id="test-fail-123",
        )
        
        assert "FAIL_CLOSED" in fail_response
        assert "Sources insuffisantes" in fail_response
        assert "test-fail-123" in fail_response
    
    def test_fail_closed_has_actionable_suggestions(self):
        """Test that FAIL_CLOSED response has actionable suggestions."""
        detection = StrategicDetection(
            is_strategic=True,
            document_type="financial_forecast",
            patterns_matched=["prévisionnel"],
            required_agents=["finance"],
            min_sources=3,
        )
        
        fail_response = create_fail_closed_response(
            detection=detection,
            responses=[],
            missing=["Sources insuffisantes"],
            correlation_id="test-789",
        )
        
        # Should have suggestions for improvement
        assert "Comment" in fail_response or "Pourquoi" in fail_response


class TestOrchestratorConfiguration:
    """Tests for orchestrator configuration."""
    
    def test_all_document_types_have_required_agents(self):
        """Test that all document types have required agents defined."""
        for doc_type in STRATEGIC_PATTERNS.keys():
            assert doc_type in REQUIRED_AGENTS, f"{doc_type} missing from REQUIRED_AGENTS"
            assert len(REQUIRED_AGENTS[doc_type]) > 0, f"{doc_type} has no required agents"
    
    def test_all_document_types_have_min_sources(self):
        """Test that all document types have minimum sources defined."""
        for doc_type in STRATEGIC_PATTERNS.keys():
            assert doc_type in MIN_SOURCES, f"{doc_type} missing from MIN_SOURCES"
            assert MIN_SOURCES[doc_type] >= 1, f"{doc_type} min_sources too low"
    
    def test_orchestrator_enabled_by_default(self):
        """Test that orchestrator is enabled by default."""
        # Clear env var if set
        original = os.environ.get("STRATEGIC_ORCHESTRATOR_ENABLED")
        os.environ.pop("STRATEGIC_ORCHESTRATOR_ENABLED", None)
        
        try:
            assert is_strategic_orchestrator_enabled()
        finally:
            # Restore
            if original is not None:
                os.environ["STRATEGIC_ORCHESTRATOR_ENABLED"] = original
    
    def test_orchestrator_can_be_disabled(self):
        """Test that orchestrator can be disabled via env var."""
        original = os.environ.get("STRATEGIC_ORCHESTRATOR_ENABLED")
        os.environ["STRATEGIC_ORCHESTRATOR_ENABLED"] = "0"
        
        try:
            assert not is_strategic_orchestrator_enabled()
        finally:
            # Restore
            if original is not None:
                os.environ["STRATEGIC_ORCHESTRATOR_ENABLED"] = original
            else:
                os.environ.pop("STRATEGIC_ORCHESTRATOR_ENABLED", None)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_query_not_strategic(self):
        """Test that empty query is not strategic."""
        result = detect_strategic_document("")
        assert not result.is_strategic
    
    def test_case_insensitive_detection(self):
        """Test that detection is case insensitive."""
        queries = [
            "ÉTUDE DE MARCHÉ",
            "Étude De Marché",
            "étude de marché",
        ]
        
        for query in queries:
            result = detect_strategic_document(query)
            assert result.is_strategic, f"'{query}' should be detected"
    
    def test_partial_match_detection(self):
        """Test detection with partial/embedded patterns."""
        query = "Je voudrais une analyse de marché approfondie"
        result = detect_strategic_document(query)
        assert result.is_strategic
    
    def test_source_counting_handles_special_chars(self):
        """Test source counting handles special characters."""
        text = "Données [REF-01] et (2024) avec Gartner®"
        count = count_sources(text)
        assert count >= 2
