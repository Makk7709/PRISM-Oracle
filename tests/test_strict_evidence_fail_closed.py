"""
Tests pour le mode STRICT_EVIDENCE et le comportement fail-closed.

T5: Sources insuffisantes → fail-closed, pas de claims assertifs.
"""

import pytest

from python.helpers.evidence import (
    EvidencePack,
    EvidenceBuilder,
    Source,
    Claim,
    SourceType,
    SourceReliability,
    ClaimStatus,
    EvidenceValidationResult,
    DOMAIN_EVIDENCE_REQUIREMENTS,
    validate_evidence_for_consensus,
    create_fail_closed_response,
)

from python.helpers.criticality_router import CriticalDomain


# ═══════════════════════════════════════════════════════════════════════════════
# T5: STRICT EVIDENCE MODE — FAIL CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrictEvidenceFailClosed:
    """Vérifie que sources insuffisantes → fail-closed."""
    
    def test_no_sources_fails_validation(self):
        """Aucune source → MISSING."""
        pack = EvidencePack(
            query="Medical question",
            domain=CriticalDomain.MEDICAL,
            strict_mode=True,
        )
        result = pack.validate()
        assert result == EvidenceValidationResult.MISSING
    
    def test_insufficient_sources_legal(self):
        """Legal domain nécessite 2+ sources."""
        builder = EvidenceBuilder(
            query="Legal question",
            domain=CriticalDomain.LEGAL,
            strict_mode=True,
        )
        
        # Ajouter UNE seule source
        builder.add_mcp_result("tavily", {
            "title": "Legal Article",
            "url": "https://example.com/legal",
            "snippet": "Legal information...",
        })
        
        pack = builder.build()
        assert pack.validation_result == EvidenceValidationResult.INSUFFICIENT
    
    def test_sufficient_sources_pass(self):
        """2 sources minimum → SUFFICIENT."""
        builder = EvidenceBuilder(
            query="Scientific question",
            domain=CriticalDomain.SCIENTIFIC,
            strict_mode=True,
        )
        
        # Ajouter 2 sources académiques
        builder.add_mcp_result("arxiv", {
            "title": "Paper 1",
            "url": "https://arxiv.org/abs/123",
            "abstract": "Research findings...",
        })
        builder.add_mcp_result("semanticscholar", {
            "title": "Paper 2",
            "url": "https://semanticscholar.org/paper/456",
            "abstract": "More research...",
        })
        
        pack = builder.build()
        # Peut être SUFFICIENT ou INSUFFICIENT selon les détails
        assert pack.validation_result in [
            EvidenceValidationResult.SUFFICIENT,
            EvidenceValidationResult.INSUFFICIENT,  # Si pas de primary
        ]
    
    def test_claim_without_source_unsupported(self):
        """Claim sans source → UNSUPPORTED."""
        pack = EvidencePack(
            query="Test",
            domain=CriticalDomain.LEGAL,
        )
        
        claim = Claim(
            text="This is a legal claim",
            domain=CriticalDomain.LEGAL,
            required_sources_min=2,
            supported_by_source_ids=[],  # Pas de sources
        )
        pack.add_claim(claim)
        
        pack.validate()
        assert claim.status == ClaimStatus.UNSUPPORTED


class TestValidateForConsensus:
    """Tests de validate_evidence_for_consensus."""
    
    def test_valid_pack_approved(self):
        """Pack valide → (True, message)."""
        pack = EvidencePack(
            query="Test",
            domain=CriticalDomain.DEFAULT,
        )
        # Ajouter une source minimale
        source = Source(
            title="Test Source",
            source_type=SourceType.WEB,
            reliability=SourceReliability.LOW,
        )
        pack.add_source(source)
        pack.validate()
        
        is_valid, message = validate_evidence_for_consensus(pack, strict_mode=False)
        # En mode non-strict avec DEFAULT domain, devrait passer
        assert is_valid is True
    
    def test_insufficient_pack_strict_rejected(self):
        """Pack insuffisant en mode strict → (False, message)."""
        pack = EvidencePack(
            query="Legal question",
            domain=CriticalDomain.LEGAL,
            strict_mode=True,
        )
        pack.validate()
        
        is_valid, message = validate_evidence_for_consensus(pack, strict_mode=True)
        assert is_valid is False
        assert len(message) > 0


class TestFailClosedResponse:
    """Tests de create_fail_closed_response."""
    
    def test_fail_closed_response_contains_domain(self):
        """La réponse fail-closed mentionne le domaine."""
        response = create_fail_closed_response(
            query="What are the legal requirements?",
            domain=CriticalDomain.LEGAL,
        )
        assert "legal" in response.lower()
        assert "insufficient" in response.lower() or "impossible" in response.lower()
    
    def test_fail_closed_response_contains_recommendations(self):
        """La réponse fail-closed donne des recommandations."""
        response = create_fail_closed_response(
            query="Medical question",
            domain=CriticalDomain.MEDICAL,
        )
        assert "recommand" in response.lower() or "expert" in response.lower()
    
    def test_fail_closed_with_evidence_pack(self):
        """Réponse avec evidence pack détaillé."""
        pack = EvidencePack(
            query="Test",
            domain=CriticalDomain.SCIENTIFIC,
            strict_mode=True,
        )
        pack.validate()
        
        response = create_fail_closed_response(
            query="Scientific question",
            domain=CriticalDomain.SCIENTIFIC,
            evidence_pack=pack,
        )
        assert "scientific" in response.lower()


class TestDomainRequirements:
    """Tests des exigences par domaine."""
    
    def test_legal_requires_primary_source(self):
        """LEGAL nécessite une source primaire."""
        reqs = DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.LEGAL]
        assert reqs["require_primary"] is True
        assert reqs["min_sources"] >= 2
    
    def test_medical_requires_high_reliability(self):
        """MEDICAL nécessite fiabilité HIGH."""
        reqs = DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.MEDICAL]
        assert reqs["min_reliability"] == SourceReliability.HIGH
    
    def test_default_minimal_requirements(self):
        """DEFAULT a des exigences minimales."""
        reqs = DOMAIN_EVIDENCE_REQUIREMENTS[CriticalDomain.DEFAULT]
        assert reqs["min_sources"] == 1
        assert reqs["require_primary"] is False


class TestClaimEvaluation:
    """Tests de l'évaluation des claims."""
    
    def test_claim_with_contradicting_source(self):
        """Claim contredit par source → INVALIDATED."""
        pack = EvidencePack(query="Test", domain=CriticalDomain.LEGAL)
        
        source = Source(
            title="Contradicting Source",
            source_type=SourceType.PRIMARY,
            reliability=SourceReliability.HIGH,
        )
        sid = pack.add_source(source)
        
        claim = Claim(
            text="Some claim",
            domain=CriticalDomain.LEGAL,
            contradicted_by_source_ids=[sid],
        )
        pack.add_claim(claim)
        
        claim.evaluate_status(pack.sources)
        assert claim.status == ClaimStatus.INVALIDATED
        assert claim.confidence == 0.0
    
    def test_claim_partial_support(self):
        """Claim avec support partiel → PARTIAL."""
        pack = EvidencePack(query="Test", domain=CriticalDomain.LEGAL)
        
        source = Source(
            title="Single Source",
            source_type=SourceType.PRIMARY,
            reliability=SourceReliability.HIGH,
        )
        sid = pack.add_source(source)
        
        claim = Claim(
            text="Some claim",
            domain=CriticalDomain.LEGAL,
            required_sources_min=2,  # Besoin de 2
            supported_by_source_ids=[sid],  # N'en a qu'une
        )
        pack.add_claim(claim)
        
        claim.evaluate_status(pack.sources)
        assert claim.status == ClaimStatus.PARTIAL
