"""
Tests for Strategic Contract — Evidence-grade validation for strategic documents.

Tests KOREV principles:
1. No sourcing = FAIL_CLOSED
2. TAM/SAM/SOM required for market studies
3. Alternatives required for structural decisions
4. UNVERIFIED claims explicitly marked
"""

import pytest
from datetime import datetime

import sys
sys.path.insert(0, '.')

from python.helpers.strategic_contract import (
    # Enums
    StrategicDocumentType,
    SourceType,
    EvidenceGrade,
    StrategicDecision,
    Criticality,
    # Models
    StrategicCitation,
    StrategicClaim,
    HypothesisDeclaration,
    AlternativeAnalysis,
    TAMSAMSOMAnalysis,
    StrategicMeta,
    StrategicStructuredResponse,
    StrategicValidationResult,
    SourceRequirement,
    # Functions
    detect_strategic_document_type,
    validate_strategic_output,
    create_strategic_fail_closed,
    is_strategic_request,
    get_required_agents,
    # Constants
    STRATEGIC_DOCUMENT_PATTERNS,
    DOCUMENT_REQUIREMENTS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrategicDocumentDetection:
    """Test detection of strategic document requests."""
    
    def test_detect_market_study_fr(self):
        """Détecte une demande d'étude de marché en français."""
        query = "Génère une étude de marché pour KOREV Evidence"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.MARKET_STUDY in doc_types
    
    def test_detect_market_study_en(self):
        """Détecte une demande d'étude de marché en anglais."""
        query = "Create a market study for the AI assistant market"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.MARKET_STUDY in doc_types
    
    def test_detect_financial_forecast(self):
        """Détecte une demande de prévisionnel financier."""
        query = "Fais-moi un prévisionnel financier sur 3 ans avec P&L"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.FINANCIAL_FORECAST in doc_types
    
    def test_detect_pricing(self):
        """Détecte une demande de pricing."""
        query = "Définis une stratégie de pricing pour le SaaS"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.PRICING in doc_types
    
    def test_detect_gtm(self):
        """Détecte une demande Go-to-Market."""
        query = "Create a GTM strategy with customer acquisition funnel"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.GTM in doc_types
    
    def test_detect_tam_sam_som(self):
        """Détecte une demande TAM/SAM/SOM."""
        query = "Calcule le TAM, SAM et SOM pour ce marché"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert StrategicDocumentType.MARKET_STUDY in doc_types
    
    def test_non_strategic_request(self):
        """Requête non stratégique détectée correctement."""
        query = "Quelle est la capitale de la France?"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is False
        assert doc_types == []
    
    def test_multiple_types_detected(self):
        """Détecte plusieurs types de documents."""
        query = "Étude de marché avec prévisionnel financier et pricing"
        is_strategic, doc_types = detect_strategic_document_type(query)
        
        assert is_strategic is True
        assert len(doc_types) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICALITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriticalityDetection:
    """Test criticality detection for strategic requests."""
    
    def test_strategic_is_high_by_default(self):
        """Documents stratégiques sont HIGH par défaut."""
        is_strat, types, crit = is_strategic_request("Génère une étude de marché")
        
        assert is_strat is True
        assert crit == Criticality.HIGH
    
    def test_draft_is_medium(self):
        """Un draft/brouillon est MEDIUM."""
        is_strat, types, crit = is_strategic_request("Fais-moi un brouillon d'étude de marché")
        
        assert is_strat is True
        assert crit == Criticality.MEDIUM
    
    def test_internal_is_medium(self):
        """Document interne est MEDIUM."""
        is_strat, types, crit = is_strategic_request("Étude de marché interne")
        
        assert is_strat is True
        assert crit == Criticality.MEDIUM


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIRED AGENTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequiredAgents:
    """Test required agents for strategic documents."""
    
    def test_market_study_requires_agents(self):
        """Market study requires finance, researcher, marketing."""
        agents = get_required_agents([StrategicDocumentType.MARKET_STUDY])
        
        assert "researcher" in agents
        assert "finance" in agents
        assert "marketing" in agents
    
    def test_financial_forecast_requires_finance(self):
        """Financial forecast requires finance agent."""
        agents = get_required_agents([StrategicDocumentType.FINANCIAL_FORECAST])
        
        assert "finance" in agents
        assert "researcher" in agents
    
    def test_business_plan_requires_all(self):
        """Business plan requires multiple agents."""
        agents = get_required_agents([StrategicDocumentType.BUSINESS_PLAN])
        
        assert "finance" in agents
        assert "researcher" in agents
        assert "marketing" in agents
        assert "sales" in agents


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION TESTS — FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationFailClosed:
    """Test FAIL_CLOSED enforcement."""
    
    def test_string_output_fails(self):
        """String output (no structure) = FAIL_CLOSED."""
        result = validate_strategic_output(
            "Voici mon étude de marché en texte libre...",
            document_type=StrategicDocumentType.MARKET_STUDY
        )
        
        assert result.is_valid is False
        assert result.decision == StrategicDecision.FAIL_CLOSED
        assert "plain text" in result.errors[0].lower()
    
    def test_no_sources_fails(self):
        """Document sans sources = FAIL_CLOSED."""
        output = {
            "claims": [
                {"claim_id": "C1", "text": "Le marché vaut 10B€", "source_ids": []}
            ],
            "citations": [],
            "answer_md": "Le marché vaut 10B€",
            "meta": {}
        }
        
        result = validate_strategic_output(
            output,
            document_type=StrategicDocumentType.MARKET_STUDY,
            strict_mode=True
        )
        
        assert result.is_valid is False
        assert result.decision == StrategicDecision.FAIL_CLOSED
        assert result.source_count == 0
    
    def test_insufficient_sources_fails(self):
        """Pas assez de sources = FAIL_CLOSED."""
        output = {
            "claims": [
                {"claim_id": "C1", "text": "Le marché vaut 10B€", "source_ids": ["S1"]}
            ],
            "citations": [
                {"id": "S1", "type": "public_stats", "reference": "Eurostat 2024"}
            ],
            "answer_md": "Content",
            "meta": {}
        }
        
        result = validate_strategic_output(
            output,
            document_type=StrategicDocumentType.MARKET_STUDY,
            strict_mode=True
        )
        
        # Market study requires 5 sources minimum
        assert result.is_valid is False
        assert result.decision == StrategicDecision.FAIL_CLOSED
        assert any("sources" in m.lower() for m in result.missing_requirements)
    
    def test_missing_tam_sam_som_fails(self):
        """Market study sans TAM/SAM/SOM = missing requirement."""
        output = {
            "claims": [],
            "citations": [
                {"id": f"S{i}", "type": "public_stats", "reference": f"Source {i}"}
                for i in range(6)
            ],
            "alternatives": [
                {"id": "A1", "name": "Alt", "description": "Desc", 
                 "rejection_reason": "Reason", "pros": [], "cons": []}
            ],
            # No tam_sam_som
            "answer_md": "Content",
            "meta": {}
        }
        
        result = validate_strategic_output(
            output,
            document_type=StrategicDocumentType.MARKET_STUDY,
            strict_mode=True
        )
        
        assert result.is_valid is False
        assert any("TAM" in m for m in result.missing_requirements)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION TESTS — APPROVED
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationApproved:
    """Test successful validation."""
    
    def test_complete_market_study_passes(self):
        """Complete market study with all requirements passes."""
        output = {
            "decision": "APPROVED",
            "claims": [
                {
                    "claim_id": "C1", 
                    "text": "Le marché de l'IA est estimé à 500B$ en 2025", 
                    "source_ids": ["S1", "S2"],
                    "evidence_grade": "V",
                    "confidence": 0.9,
                    "is_quantitative": True,
                    "is_projection": False
                }
            ],
            "citations": [
                {"id": "S1", "type": "public_stats", "reference": "Eurostat AI Market Report 2024"},
                {"id": "S2", "type": "industry_report", "reference": "Gartner AI Forecast 2025"},
                {"id": "S3", "type": "market_data", "reference": "Statista AI Market Size"},
                {"id": "S4", "type": "competitor_public", "reference": "OpenAI Pricing Page"},
                {"id": "S5", "type": "public_stats", "reference": "INSEE Tech Sector 2024"},
            ],
            "hypotheses": [
                {"id": "H1", "text": "Adoption rate 15%/year", "impact": "HIGH", "verifiable": True}
            ],
            "alternatives": [
                {
                    "id": "A1", 
                    "name": "Focus B2C", 
                    "description": "Consumer market focus",
                    "pros": ["Large volume"],
                    "cons": ["Low ARPA", "High CAC"],
                    "rejection_reason": "Unit economics unfavorable",
                    "source_ids": ["S2"]
                }
            ],
            "tam_sam_som": {
                "tam_value": 500000000000,
                "tam_source_ids": ["S1"],
                "tam_methodology": "Top-down from industry reports",
                "sam_value": 50000000000,
                "sam_percentage_of_tam": 10.0,
                "sam_source_ids": ["S2"],
                "sam_methodology": "B2B segment only",
                "som_value": 1000000000,
                "som_percentage_of_sam": 2.0,
                "som_source_ids": ["S3"],
                "som_methodology": "European market, year 3"
            },
            "answer_md": "## Market Analysis\n\nContent here...",
            "meta": {
                "agents_invoked": ["finance", "researcher", "marketing"],
                "consensus_required": True,
                "consensus_status": "validated"
            }
        }
        
        result = validate_strategic_output(
            output,
            document_type=StrategicDocumentType.MARKET_STUDY,
            strict_mode=True
        )
        
        assert result.is_valid is True
        assert result.decision == StrategicDecision.APPROVED
        assert result.source_count >= 5
        assert result.structured_response is not None


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelValidation:
    """Test Pydantic model validations."""
    
    def test_claim_without_source_is_unverified(self):
        """Claim sans source devient UNVERIFIED automatiquement."""
        claim = StrategicClaim(
            claim_id="C1",
            text="Le marché vaut 10B€",
            source_ids=[],  # No sources
        )
        
        assert claim.evidence_grade == "U"  # Forced to UNVERIFIED
        assert claim.confidence == 0.0
    
    def test_claim_with_one_source_is_partial(self):
        """Claim avec une seule source devient PARTIAL max."""
        claim = StrategicClaim(
            claim_id="C1",
            text="Le marché vaut 10B€",
            source_ids=["S1"],
            evidence_grade="V",  # Will be downgraded
        )
        
        assert claim.evidence_grade == "P"  # Downgraded to PARTIAL
    
    def test_generic_citation_rejected(self):
        """Citation générique rejetée."""
        with pytest.raises(ValueError) as exc_info:
            StrategicCitation(
                id="S1",
                type="public_stats",
                reference="data"  # Too generic
            )
        
        assert "generic" in str(exc_info.value).lower()
    
    def test_tam_greater_than_sam(self):
        """TAM doit être >= SAM."""
        with pytest.raises(ValueError) as exc_info:
            TAMSAMSOMAnalysis(
                tam_value=100,
                tam_source_ids=["S1"],
                sam_value=200,  # Greater than TAM - invalid
                sam_source_ids=["S2"]
            )
        
        assert "TAM" in str(exc_info.value) or "SAM" in str(exc_info.value)
    
    def test_tam_requires_source(self):
        """TAM value requires source_ids."""
        with pytest.raises(ValueError) as exc_info:
            TAMSAMSOMAnalysis(
                tam_value=1000000,
                tam_source_ids=[],  # Missing source
            )
        
        assert "source" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL_CLOSED RESPONSE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosedResponse:
    """Test FAIL_CLOSED response generation."""
    
    def test_fail_closed_has_all_sections(self):
        """FAIL_CLOSED response contains all required information."""
        response = create_strategic_fail_closed(
            reason="Sourcing insufficient",
            document_type=StrategicDocumentType.MARKET_STUDY,
            missing_data=["TAM/SAM/SOM", "Competitor analysis"]
        )
        
        assert response["decision"] == "FAIL_CLOSED"
        assert "FAIL_CLOSED" in response["answer_md"]
        assert "TAM/SAM/SOM" in response["answer_md"]
        assert response["claims"] == []
        assert response["meta"]["criticality"] == "HIGH"
    
    def test_fail_closed_lists_requirements(self):
        """FAIL_CLOSED lists specific requirements."""
        response = create_strategic_fail_closed(
            reason="Test",
            document_type=StrategicDocumentType.MARKET_STUDY,
            missing_data=["Sources publiques", "Analyse TAM"]
        )
        
        # Check requirements table is present
        assert "Sources totales" in response["answer_md"]
        assert "Exigences non remplies" in response["answer_md"]


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentRequirements:
    """Test document requirements configuration."""
    
    def test_market_study_requirements(self):
        """Market study has strict requirements."""
        req = DOCUMENT_REQUIREMENTS[StrategicDocumentType.MARKET_STUDY]
        
        assert req.min_sources == 5
        assert req.min_public_sources == 3
        assert req.require_tam_sam_som is True
        assert req.require_competitor_data is True
        assert req.require_alternatives is True
    
    def test_financial_forecast_requirements(self):
        """Financial forecast requirements."""
        req = DOCUMENT_REQUIREMENTS[StrategicDocumentType.FINANCIAL_FORECAST]
        
        assert req.min_sources >= 4
        assert req.require_financial_basis is True
    
    def test_due_diligence_has_highest_requirements(self):
        """Due diligence has highest sourcing requirements."""
        req = DOCUMENT_REQUIREMENTS[StrategicDocumentType.DUE_DILIGENCE]
        
        assert req.min_sources == 8
        assert req.min_public_sources == 5


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_detect_validate_workflow(self):
        """Full workflow: detect → validate → fail_closed."""
        query = "Génère une étude de marché pour KOREV Evidence"
        
        # Step 1: Detect
        is_strat, types, crit = is_strategic_request(query)
        assert is_strat is True
        assert crit == Criticality.HIGH
        
        # Step 2: Get required agents
        agents = get_required_agents(types)
        assert len(agents) >= 3
        
        # Step 3: Validate unsourced output
        bad_output = {"claims": [], "citations": [], "answer_md": "Pitch content", "meta": {}}
        result = validate_strategic_output(bad_output, types[0], crit, strict_mode=True)
        
        # Step 4: Verify FAIL_CLOSED
        assert result.decision == StrategicDecision.FAIL_CLOSED
        assert result.fail_closed_response is not None
        assert "FAIL_CLOSED" in result.fail_closed_response["answer_md"]


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE PRINCIPLE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvidencePrinciples:
    """Test that Evidence principles are enforced."""
    
    def test_no_invention_principle(self):
        """Zéro invention: claims sans source = UNVERIFIED."""
        claim = StrategicClaim(
            claim_id="C1",
            text="Le marché croît de 25% par an",
            source_ids=[],  # No source = invention
            is_quantitative=True
        )
        
        assert claim.evidence_grade == "U"
        assert claim.confidence == 0.0
    
    def test_traceable_principle(self):
        """Traçabilité: chaque claim lié à des sources."""
        # Valid claim with sources
        claim = StrategicClaim(
            claim_id="C1",
            text="Le marché vaut 10B€",
            source_ids=["S1", "S2"],
            evidence_grade="V",
            confidence=0.9
        )
        
        assert len(claim.source_ids) >= 1
        # Grade stays V because we have multiple sources
        assert claim.evidence_grade in ["V", "P"]
    
    def test_auditable_principle(self):
        """Auditabilité: sortie structurée, pas du texte."""
        # Text output fails
        result = validate_strategic_output(
            "Voici mon analyse...",
            StrategicDocumentType.MARKET_STUDY
        )
        assert result.decision == StrategicDecision.FAIL_CLOSED
        
        # Structured output can pass (if sourcing OK)
        # This proves the structure requirement is enforced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
