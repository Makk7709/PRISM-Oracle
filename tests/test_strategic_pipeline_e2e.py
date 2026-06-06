"""
E2E Tests for Strategic Pipeline Integration.

Tests the full flow:
1. Query detection → Strategic context
2. Route decision enrichment → Required agents added
3. Response validation → FAIL_CLOSED or APPROVED

These tests validate that the Evidence principle "no unsourced strategic docs"
is enforced throughout the pipeline.
"""

import pytest
from datetime import datetime

import sys
sys.path.insert(0, '.')

from python.helpers.router import (
    decide_route,
    RouteDecision,
    RouteVerdict,
    IntentName,
    POLICY_VERSION,
)
from python.helpers.strategic_pipeline import (
    StrategicRouteContext,
    StrategicPipelineResult,
    detect_strategic_context,
    enrich_route_decision,
    validate_strategic_response,
    run_strategic_pipeline,
    should_enforce_strategic_validation,
    get_strategic_requirements_summary,
)
from python.helpers.strategic_contract import (
    StrategicDocumentType,
    StrategicDecision,
    Criticality,
)


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: MARKET STUDY FLOW
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketStudyE2E:
    """E2E tests for market study requests."""
    
    def test_e2e_market_study_detection_to_fail_closed(self):
        """
        E2E: Market study request with unsourced response → FAIL_CLOSED.
        
        This is the core Evidence principle test.
        """
        # Step 1: User query
        query = "Génère une étude de marché pour KOREV Evidence avec TAM/SAM/SOM"
        
        # Step 2: Detect strategic context
        context = detect_strategic_context(query)
        assert context.is_strategic is True
        assert StrategicDocumentType.MARKET_STUDY in context.document_types
        assert context.criticality == Criticality.HIGH
        assert "finance" in context.required_agents
        assert "researcher" in context.required_agents
        
        # Step 3: Initial routing
        base_decision = decide_route(query)
        
        # Step 4: Enrich route with strategic requirements
        enriched = enrich_route_decision(base_decision, context)
        assert enriched.is_board_level is True
        
        # Verify required agents added
        intent_names = [i.name for i in enriched.intents]
        assert IntentName.FINANCE in intent_names
        assert IntentName.RESEARCHER in intent_names
        
        # Step 5: Simulate unsourced agent response (the problem we're solving)
        unsourced_response = {
            "claims": [
                {"claim_id": "C1", "text": "Le marché vaut 10B€", "source_ids": []}
            ],
            "citations": [],
            "answer_md": "Le marché de l'IA vaut 10B€...",
            "meta": {}
        }
        
        # Step 6: Validate response
        validation, fail_closed = validate_strategic_response(
            response=unsourced_response,
            strategic_context=context,
            strict_mode=True
        )
        
        # Step 7: Assert FAIL_CLOSED
        assert validation.is_valid is False
        assert validation.decision == StrategicDecision.FAIL_CLOSED
        assert fail_closed is not None
        assert "FAIL_CLOSED" in fail_closed["answer_md"]
        assert fail_closed["decision"] == "FAIL_CLOSED"
    
    def test_e2e_market_study_with_proper_sources_approved(self):
        """
        E2E: Market study with proper sourcing → APPROVED.
        """
        query = "Génère une étude de marché avec analyse TAM/SAM/SOM"
        
        # Detect and enrich
        context = detect_strategic_context(query)
        base_decision = decide_route(query)
        enrich_route_decision(base_decision, context)
        
        # Properly sourced response
        sourced_response = {
            "decision": "APPROVED",
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Le marché IA vaut 400B$ en 2025",
                    "source_ids": ["S1", "S2"],
                    "evidence_grade": "V",
                    "confidence": 0.9,
                }
            ],
            "citations": [
                {"id": "S1", "type": "public_stats", "reference": "Gartner AI Market Report 2025"},
                {"id": "S2", "type": "industry_report", "reference": "IDC AI Forecast 2025"},
                {"id": "S3", "type": "market_data", "reference": "Statista AI Market Size"},
                {"id": "S4", "type": "competitor_public", "reference": "OpenAI Pricing 2025"},
                {"id": "S5", "type": "public_stats", "reference": "Eurostat Digital Economy 2025"},
            ],
            "hypotheses": [
                {"id": "H1", "text": "Adoption rate 15%", "impact": "HIGH", "verifiable": True}
            ],
            "alternatives": [
                {
                    "id": "A1",
                    "name": "Focus B2C",
                    "description": "Consumer market focus",
                    "pros": ["Volume"],
                    "cons": ["Low ARPA"],
                    "rejection_reason": "Unit economics unfavorable",
                }
            ],
            "tam_sam_som": {
                "tam_value": 400000000000,
                "tam_source_ids": ["S1"],
                "tam_methodology": "Top-down",
                "sam_value": 40000000000,
                "sam_source_ids": ["S2"],
                "sam_methodology": "B2B segment",
                "som_value": 1000000000,
                "som_source_ids": ["S3"],
                "som_methodology": "Europe Y3",
            },
            "answer_md": "## Market Analysis\n\nContent...",
            "meta": {
                "agents_invoked": ["finance", "researcher", "marketing"],
                "consensus_required": True,
            }
        }
        
        # Validate
        validation, fail_closed = validate_strategic_response(
            response=sourced_response,
            strategic_context=context,
            strict_mode=True
        )
        
        # Should be APPROVED
        assert validation.is_valid is True
        assert validation.decision == StrategicDecision.APPROVED
        assert fail_closed is None
        assert validation.source_count >= 5


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: FULL PIPELINE WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipelineE2E:
    """E2E tests using the full pipeline wrapper."""
    
    def test_run_strategic_pipeline_fail_closed(self):
        """Test run_strategic_pipeline returns FAIL_CLOSED for unsourced."""
        query = "Crée un prévisionnel financier sur 3 ans"
        base_decision = decide_route(query)
        
        unsourced = {"claims": [], "citations": [], "answer_md": "Revenue = 1M€", "meta": {}}
        
        result = run_strategic_pipeline(
            query=query,
            base_route_decision=base_decision,
            agent_response=unsourced,
            strict_mode=True
        )
        
        assert result.is_fail_closed is True
        assert result.strategic_context.is_strategic is True
        assert "FAIL_CLOSED" in result.final_response.get("answer_md", "")
    
    def test_run_strategic_pipeline_non_strategic_passthrough(self):
        """Test that non-strategic requests pass through unchanged."""
        query = "Quelle est la capitale de la France?"
        base_decision = decide_route(query)
        
        response = {"content": "Paris est la capitale de la France."}
        
        result = run_strategic_pipeline(
            query=query,
            base_route_decision=base_decision,
            agent_response=response,
            strict_mode=True
        )
        
        assert result.is_fail_closed is False
        assert result.strategic_context.is_strategic is False
        assert result.final_response == response


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: ROUTE ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouteEnrichmentE2E:
    """E2E tests for route decision enrichment."""
    
    def test_enrichment_adds_missing_agents(self):
        """Enrichment adds required agents if not detected by base router."""
        query = "Étude de marché avec analyse concurrentielle"
        
        # Base routing might not detect all agents
        base_decision = decide_route(query)
        context = detect_strategic_context(query)
        
        # Enrich
        enriched = enrich_route_decision(base_decision, context)
        
        # Verify agents were added
        intent_names = [i.name for i in enriched.intents]
        
        # Market study requires finance, researcher, marketing
        for required in context.required_agents:
            agent_intent = {
                "finance": IntentName.FINANCE,
                "researcher": IntentName.RESEARCHER,
                "marketing": IntentName.MARKETING,
            }.get(required)
            
            if agent_intent:
                assert agent_intent in intent_names, f"Missing required agent: {required}"
    
    def test_enrichment_forces_board_level(self):
        """HIGH criticality forces board-level even if not detected."""
        query = "Prévisionnel financier pour levée de fonds"
        
        context = detect_strategic_context(query)
        assert context.criticality == Criticality.HIGH
        
        # Create a base decision that's not board-level
        base_decision = decide_route("simple query")
        
        # Enrich with strategic context
        enriched = enrich_route_decision(base_decision, context)
        
        # Should now be board-level
        assert enriched.is_board_level is True
    
    def test_enrichment_preserves_base_intents(self):
        """Enrichment preserves intents from base routing."""
        query = "Analyse financière et juridique pour étude de marché M&A"
        
        base_decision = decide_route(query)
        context = detect_strategic_context(query)
        
        # Get base intent names
        base_intent_names = {i.name for i in base_decision.intents}
        
        # Enrich
        enriched = enrich_route_decision(base_decision, context)
        enriched_intent_names = {i.name for i in enriched.intents}
        
        # All base intents should still be present
        for intent in base_intent_names:
            assert intent in enriched_intent_names


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctionsE2E:
    """E2E tests for convenience functions."""
    
    def test_should_enforce_strategic_validation(self):
        """Test quick check for strategic enforcement."""
        assert should_enforce_strategic_validation("Étude de marché") is True
        assert should_enforce_strategic_validation("Prévisionnel financier") is True
        assert should_enforce_strategic_validation("Pricing strategy") is True
        assert should_enforce_strategic_validation("Quelle heure est-il?") is False
    
    def test_get_strategic_requirements_summary(self):
        """Test requirements summary for strategic requests."""
        summary = get_strategic_requirements_summary("Étude de marché complète")
        
        assert summary is not None
        assert "market_study" in summary["document_types"]
        assert summary["criticality"] == "HIGH"
        assert "finance" in summary["required_agents"]
        assert "researcher" in summary["required_agents"]
        
        # Non-strategic returns None
        assert get_strategic_requirements_summary("Bonjour") is None


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: ERROR CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorCasesE2E:
    """E2E tests for error handling."""
    
    def test_string_response_becomes_fail_closed(self):
        """String response (unstructured) triggers FAIL_CLOSED."""
        query = "Étude de marché pour startup AI"
        context = detect_strategic_context(query)
        
        # String response (not structured)
        string_response = "Le marché de l'AI est en croissance..."
        
        validation, fail_closed = validate_strategic_response(
            response=string_response,
            strategic_context=context,
            strict_mode=True
        )
        
        assert validation.is_valid is False
        assert validation.decision == StrategicDecision.FAIL_CLOSED
        assert "plain text" in validation.errors[0].lower()
    
    def test_missing_tam_sam_som_fails(self):
        """Market study without TAM/SAM/SOM fails."""
        query = "Étude de marché"
        context = detect_strategic_context(query)
        
        # Has sources but no TAM/SAM/SOM
        response = {
            "claims": [],
            "citations": [
                {"id": f"S{i}", "type": "public_stats", "reference": f"Source {i}"}
                for i in range(6)
            ],
            "alternatives": [
                {"id": "A1", "name": "Alt", "description": "Desc",
                 "rejection_reason": "Reason", "pros": [], "cons": []}
            ],
            # Missing tam_sam_som
            "answer_md": "Market analysis without TAM/SAM/SOM",
            "meta": {}
        }
        
        validation, fail_closed = validate_strategic_response(
            response=response,
            strategic_context=context,
            strict_mode=True
        )
        
        assert validation.is_valid is False
        assert any("TAM" in m for m in validation.missing_requirements)


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: POLICY VERSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyVersionE2E:
    """Test policy version is updated."""
    
    def test_policy_version_updated(self):
        """Policy version should be 1.2.0+ for strategic support."""
        assert POLICY_VERSION >= "1.2.0"


# ═══════════════════════════════════════════════════════════════════════════════
# E2E TEST: INTEGRATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationScenariosE2E:
    """Real-world integration scenarios."""
    
    def test_scenario_investor_deck_preparation(self):
        """
        Scenario: User asks for investor deck with market analysis.
        
        Expected: HIGH criticality, multiple agents, strict validation.
        """
        query = "Prépare un pitch deck investisseur avec étude de marché TAM/SAM/SOM et prévisionnel financier"
        
        # Detect
        context = detect_strategic_context(query)
        assert context.is_strategic is True
        assert context.criticality == Criticality.HIGH
        
        # Should require multiple document types
        doc_types = {dt.value for dt in context.document_types}
        assert len(doc_types) >= 1  # At least market study or financial forecast
        
        # Should require finance agent
        assert "finance" in context.required_agents
    
    def test_scenario_competitive_positioning(self):
        """
        Scenario: User asks for competitive analysis with pricing.
        """
        query = "Analyse concurrentielle avec benchmark pricing des concurrents"
        
        context = detect_strategic_context(query)
        
        # Should be strategic (competitive analysis or pricing)
        assert context.is_strategic is True
        
        # Should be HIGH criticality
        assert context.criticality == Criticality.HIGH
    
    def test_scenario_simple_question_not_strategic(self):
        """
        Scenario: Simple question should not trigger strategic pipeline.
        """
        queries = [
            "Qu'est-ce que Python?",
            "Comment configurer Docker?",
            "Explique-moi le machine learning",
        ]
        
        for query in queries:
            context = detect_strategic_context(query)
            assert context.is_strategic is False, f"'{query}' should not be strategic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
