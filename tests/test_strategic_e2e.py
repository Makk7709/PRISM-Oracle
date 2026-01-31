#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             TEST E2E — Strategic Document Pipeline                           ║
║                                                                              ║
║  Vérifie que le pipeline stratégique fonctionne de bout en bout:            ║
║  1. Détection des requêtes stratégiques                                      ║
║  2. Appel des agents spécialisés                                             ║
║  3. Validation du sourcing                                                   ║
║  4. FAIL_CLOSED si sourcing insuffisant                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python.helpers.strategic_orchestrator import (
    detect_strategic_document,
    count_sources,
    validate_strategic_content,
    StrategicDetection,
    STRATEGIC_PATTERNS,
    REQUIRED_AGENTS,
    MIN_SOURCES,
)


class TestStrategicDetection:
    """Tests for strategic document detection."""
    
    def test_detect_market_study_french(self):
        """Test detection of market study request in French."""
        queries = [
            "Je veux une étude de marché pour KOREV Evidence",
            "Fais-moi une analyse de marché SaaS B2B",
            "Calcule le TAM SAM SOM pour notre produit",
        ]
        
        for query in queries:
            detection = detect_strategic_document(query)
            assert detection.is_strategic, f"Should detect: {query}"
            assert detection.document_type == "market_study", f"Type should be market_study: {query}"
            assert "researcher" in detection.required_agents
            assert "finance" in detection.required_agents
    
    def test_detect_financial_forecast_french(self):
        """Test detection of financial forecast in French."""
        queries = [
            "Fais-moi un prévisionnel financier sur 5 ans",
            "Je veux un forecast de revenus",
            "Crée un P&L prévisionnel",
            "business plan financier",
        ]
        
        for query in queries:
            detection = detect_strategic_document(query)
            assert detection.is_strategic, f"Should detect: {query}"
            assert detection.document_type == "financial_forecast", f"Type should be financial_forecast: {query}"
            assert "finance" in detection.required_agents
    
    def test_detect_pricing_strategy(self):
        """Test detection of pricing strategy request."""
        queries = [
            "Définis une stratégie de pricing",
            "Aide-moi à fixer le tarif",
            "Analyse de pricing concurrentiel",
        ]
        
        for query in queries:
            detection = detect_strategic_document(query)
            assert detection.is_strategic, f"Should detect: {query}"
            assert detection.document_type == "pricing", f"Type should be pricing: {query}"
    
    def test_detect_gtm_strategy(self):
        """Test detection of go-to-market strategy."""
        queries = [
            "Plan go-to-market pour la France",
            "Stratégie GTM B2B",
            "Plan de lancement produit",
        ]
        
        for query in queries:
            detection = detect_strategic_document(query)
            assert detection.is_strategic, f"Should detect: {query}"
            assert detection.document_type == "go_to_market", f"Type should be go_to_market: {query}"
    
    def test_non_strategic_queries(self):
        """Test that non-strategic queries are not detected."""
        queries = [
            "Quelle heure est-il?",
            "Explique-moi le machine learning",
            "Comment écrire une fonction Python",
            "Bonjour comment ça va",
        ]
        
        for query in queries:
            detection = detect_strategic_document(query)
            assert not detection.is_strategic, f"Should NOT detect: {query}"


class TestSourceCounting:
    """Tests for source counting functionality."""
    
    def test_count_ref_markers(self):
        """Test counting [REF-XX] markers."""
        text = """
        Le marché IA B2B en France représente 1.5 Md€ [REF-01].
        La croissance est de 30% [REF-02] selon les projections [REF-03].
        """
        count = count_sources(text)
        assert count >= 3, "Should count at least 3 references"
    
    def test_count_eu_sources(self):
        """Test counting EU source mentions."""
        text = """
        Selon Eurostat, 8% des entreprises utilisent l'IA.
        L'INSEE recense 5800 ETI en France.
        Bpifrance indique 15% de PME avec budget IA.
        """
        count = count_sources(text)
        assert count >= 3, "Should count EU sources"
    
    def test_count_eu_urls(self):
        """Test counting EU URLs."""
        text = """
        Source: https://ec.europa.eu/eurostat/data/12345
        Voir aussi: https://www.insee.fr/statistiques/entreprises
        """
        count = count_sources(text)
        assert count >= 2, "Should count EU URLs"
    
    def test_unsourced_text(self):
        """Test that unsourced text has zero or minimal count."""
        text = """
        Le marché est en croissance.
        Les entreprises adoptent l'IA rapidement.
        Le potentiel est énorme.
        """
        count = count_sources(text)
        assert count == 0, "Unsourced text should have 0 sources"


class TestContentValidation:
    """Tests for strategic content validation."""
    
    def test_validate_market_study_with_sources(self):
        """Test validation of properly sourced market study."""
        text = """
        # Étude de Marché
        
        ## TAM: 1.5 Md€ [REF-01]
        Selon Eurostat, le marché IA B2B en Europe représente 50 Md€.
        
        ## SAM: 300 M€ [REF-02]
        INSEE indique 5800 ETI en France avec budget IT.
        
        ## SOM: 45 M€ [REF-03]
        Part réaliste basée sur benchmark Bpifrance.
        
        ## Alternatives analysées
        - Option A: Focus PME — rejetée car cycle vente trop long
        - Option B: Focus grandes entreprises — rejetée car concurrence
        
        ## Sources
        [REF-01] Eurostat 2024
        [REF-02] INSEE 2024
        [REF-03] Bpifrance 2024
        """
        
        is_valid, missing = validate_strategic_content(
            text=text,
            document_type="market_study",
            min_sources=3,
        )
        
        # Should pass if TAM/SAM/SOM present and alternatives analyzed
        assert len(missing) < 3, f"Should have few missing items: {missing}"
    
    def test_validate_market_study_missing_tam(self):
        """Test validation fails when TAM missing."""
        text = """
        # Étude de Marché
        
        Le marché est en croissance.
        Les opportunités sont nombreuses.
        """
        
        is_valid, missing = validate_strategic_content(
            text=text,
            document_type="market_study",
            min_sources=3,
        )
        
        assert not is_valid
        assert any("TAM" in m for m in missing)
        assert any("SAM" in m for m in missing)
        assert any("SOM" in m for m in missing)
    
    def test_validate_financial_forecast_missing_scenarios(self):
        """Test validation fails when scenarios missing."""
        text = """
        # Prévisionnel
        
        Le CA sera de 1M€ en Y1.
        Le break-even en Y3.
        """
        
        is_valid, missing = validate_strategic_content(
            text=text,
            document_type="financial_forecast",
            min_sources=3,
        )
        
        assert not is_valid
        assert any("Hypothèses" in m or "Scénarios" in m for m in missing)


class TestE2EIntegration:
    """Integration tests for the full pipeline."""
    
    @pytest.mark.asyncio
    async def test_strategic_pipeline_detection_and_routing(self):
        """Test that strategic queries trigger the right pipeline."""
        from python.helpers.strategic_orchestrator import (
            detect_strategic_document,
            is_strategic_orchestrator_enabled,
        )
        
        # Ensure orchestrator is enabled
        os.environ["STRATEGIC_ORCHESTRATOR_ENABLED"] = "1"
        
        assert is_strategic_orchestrator_enabled()
        
        query = "Fais-moi une étude de marché complète pour KOREV Evidence"
        detection = detect_strategic_document(query)
        
        assert detection.is_strategic
        assert detection.document_type == "market_study"
        assert len(detection.required_agents) >= 2
        assert detection.min_sources >= 3
    
    @pytest.mark.asyncio
    async def test_fail_closed_on_insufficient_sources(self):
        """Test that FAIL_CLOSED is triggered when sources are insufficient."""
        from python.helpers.strategic_orchestrator import (
            validate_strategic_content,
            create_fail_closed_response,
            StrategicDetection,
        )
        
        # Simulate an agent response without proper sourcing
        unsourced_response = """
        # Étude de Marché
        
        Le marché est prometteur.
        La croissance sera forte.
        Les clients sont nombreux.
        """
        
        is_valid, missing = validate_strategic_content(
            text=unsourced_response,
            document_type="market_study",
            min_sources=5,
        )
        
        assert not is_valid
        assert len(missing) >= 3  # TAM, SAM, SOM missing
        
        # Verify FAIL_CLOSED response is generated
        detection = StrategicDetection(
            is_strategic=True,
            document_type="market_study",
            required_agents=["researcher", "finance", "marketing"],
            min_sources=5,
        )
        
        fail_response = create_fail_closed_response(
            detection=detection,
            responses=[],
            missing=missing,
            correlation_id="test-123",
        )
        
        assert "FAIL_CLOSED" in fail_response
        assert "test-123" in fail_response


class TestRegressionPrevention:
    """Tests to prevent regression to 'chat mode'."""
    
    def test_strategic_detection_not_bypassed(self):
        """Verify strategic detection cannot be bypassed by simple queries."""
        strategic_keywords = [
            "étude de marché",
            "prévisionnel",
            "pricing",
            "go-to-market",
            "business plan",
        ]
        
        for keyword in strategic_keywords:
            # Even simple variations should trigger
            for template in [
                f"Fais-moi un {keyword}",
                f"Je veux un {keyword}",
                f"Crée un {keyword}",
                f"{keyword} pour mon projet",
            ]:
                detection = detect_strategic_document(template)
                assert detection.is_strategic, f"Should detect '{keyword}' in: {template}"
    
    def test_min_sources_enforced(self):
        """Verify minimum sources are enforced per document type."""
        for doc_type, min_sources in MIN_SOURCES.items():
            assert min_sources >= 3, f"{doc_type} should require at least 3 sources"
    
    def test_required_agents_defined(self):
        """Verify each document type has required agents."""
        for doc_type, agents in REQUIRED_AGENTS.items():
            assert len(agents) >= 2, f"{doc_type} should require at least 2 agents"
            assert "researcher" in agents or "finance" in agents, \
                f"{doc_type} should include researcher or finance"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
