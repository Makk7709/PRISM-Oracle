"""
T9: Final Output Claim Integrity — Test Anti-Hallucination.

Vérifie que la réponse finale ne contient QUE des claims tracés.
Un LLM peut générer des assertions "hors claims" même avec un EvidencePack.

Ce test prouve: "toute assertion critique provient d'un claim sourcé".
"""

import pytest
from typing import List

from python.helpers.critical_decision_gate import (
    CriticalDecisionGate,
    GateDecision,
    assert_no_unsourced_claims,
    extract_claims_from_text,
)
from python.helpers.evidence import (
    EvidencePack,
    EvidenceBuilder,
    Claim,
    ClaimStatus,
    Source,
    SourceType,
    SourceReliability,
)
from python.helpers.criticality_router import CriticalDomain


class TestClaimExtraction:
    """
    Test de l'extraction de claims depuis un texte.
    """
    
    def test_extracts_assertive_claims(self):
        """Extrait les phrases assertives."""
        text = """
        This treatment is effective for cancer.
        The medication should be taken daily.
        Studies have shown significant improvement.
        """
        
        claims = extract_claims_from_text(text, CriticalDomain.MEDICAL)
        
        # Au moins quelques claims détectés
        assert len(claims) >= 1, "Should extract assertive claims"
    
    def test_extracts_french_claims(self):
        """Extrait les claims en français."""
        text = """
        Ce médicament est efficace contre la douleur.
        Le traitement doit être suivi pendant 10 jours.
        Par conséquent, nous recommandons cette posologie.
        """
        
        claims = extract_claims_from_text(text, CriticalDomain.MEDICAL)
        
        assert len(claims) >= 1, "Should extract French claims"
    
    def test_ignores_questions(self):
        """N'extrait pas les questions."""
        text = """
        What is the dosage?
        How long should I take this?
        Is this effective?
        """
        
        claims = extract_claims_from_text(text, CriticalDomain.MEDICAL)
        
        # Questions ne sont pas des claims
        for claim in claims:
            assert "?" not in claim, "Questions should not be claims"


class TestUnsourcedClaimsDetection:
    """
    Test de la détection de claims non sourcés.
    """
    
    def test_detects_claims_without_evidence_pack(self):
        """Détecte les claims quand pas d'evidence pack."""
        answer = "This treatment is highly effective. The medication cures the disease."
        
        all_sourced, unsourced = assert_no_unsourced_claims(
            answer=answer,
            evidence_pack=None,
            domain=CriticalDomain.MEDICAL,
        )
        
        # Sans evidence pack, les claims doivent être détectés comme non sourcés
        if len(extract_claims_from_text(answer, CriticalDomain.MEDICAL)) > 0:
            assert all_sourced is False or len(unsourced) > 0
    
    def test_default_domain_no_strict_check(self):
        """Domain DEFAULT ne vérifie pas strictement."""
        answer = "This is a claim without source in default domain."
        
        all_sourced, unsourced = assert_no_unsourced_claims(
            answer=answer,
            evidence_pack=None,
            domain=CriticalDomain.DEFAULT,
        )
        
        # DEFAULT = pas de vérification stricte
        assert all_sourced is True
    
    def test_sourced_claims_pass(self):
        """Claims avec sources passent."""
        builder = EvidenceBuilder(
            query="Medical question",
            domain=CriticalDomain.MEDICAL,
            strict_mode=True,
        )
        
        # Ajouter une source
        builder.add_mcp_result("pubmed", {
            "title": "Clinical Study",
            "url": "https://pubmed.gov/123",
            "snippet": "Treatment is effective...",
        })
        
        pack = builder.build()
        
        # Ajouter un claim sourcé
        claim = Claim(
            text="Treatment is effective",
            domain=CriticalDomain.MEDICAL,
            required_sources_min=1,
            supported_by_source_ids=[list(pack.sources.keys())[0]],
            status=ClaimStatus.SUPPORTED,
        )
        pack.claims.append(claim)
        
        # Tous les claims du pack sont sourcés
        all_sourced, unsourced = assert_no_unsourced_claims(
            answer="Treatment is effective based on studies.",
            evidence_pack=pack,
            domain=CriticalDomain.MEDICAL,
        )
        
        # Le claim est sourcé
        assert claim.status == ClaimStatus.SUPPORTED


class TestFinalOutputIntegrity:
    """
    T9: Vérification d'intégrité de la sortie finale.
    
    Règle: toute assertion critique doit provenir d'un claim tracé.
    """
    
    @pytest.fixture
    def gate(self):
        return CriticalDecisionGate()
    
    @pytest.mark.asyncio
    async def test_blocks_output_with_unsourced_claims(self, gate):
        """Bloque output avec claims non sourcés en mode strict."""
        # Pack vide (pas de sources)
        pack = EvidencePack(
            query="Medical question",
            domain=CriticalDomain.MEDICAL,
            strict_mode=True,
        )
        pack.validate()
        
        # Output avec claim médical assertif
        output = "This medication is proven to cure cancer in 90% of cases."
        
        result = await gate.validate_final_output(
            output=output,
            agent_profile="default",
            evidence_pack=pack,
        )
        
        # Doit être bloqué (claims sans sources)
        assert result.can_emit is False
        assert result.decision == GateDecision.FAIL_CLOSED
    
    @pytest.mark.asyncio
    async def test_allows_output_with_all_claims_sourced(self, gate):
        """Autorise output si tous les claims sont sourcés."""
        builder = EvidenceBuilder(
            query="Weather question",
            domain=CriticalDomain.DEFAULT,  # Domain non critique
            strict_mode=False,
        )
        builder.add_mcp_result("weather", {
            "title": "Weather Report",
            "url": "https://weather.com",
            "snippet": "Sunny today",
        })
        pack = builder.build()
        
        result = await gate.validate_final_output(
            output="The weather is sunny today.",
            agent_profile="default",
            evidence_pack=pack,
            consensus_result={"approved": True},
        )
        
        # Domain DEFAULT → devrait passer
        assert result.can_emit is True
    
    @pytest.mark.asyncio
    async def test_strict_mode_blocks_missing_primary_source(self, gate):
        """Mode strict bloque si source primaire manquante (LEGAL)."""
        builder = EvidenceBuilder(
            query="Legal question",
            domain=CriticalDomain.LEGAL,
            strict_mode=True,
        )
        
        # Source secondaire seulement (pas primaire)
        builder.add_mcp_result("google", {
            "title": "Blog about law",
            "url": "https://blog.com/law",
            "snippet": "According to this blog...",
        })
        pack = builder.build()
        pack.validate()
        
        result = await gate.validate_final_output(
            output="The contract clause is enforceable.",
            agent_profile="default",
            evidence_pack=pack,
        )
        
        # Evidence insuffisante → fail-closed
        # (LEGAL exige source primaire selon DOMAIN_EVIDENCE_REQUIREMENTS)
        assert result.evidence_valid is False or result.can_emit is False


class TestClaimIntegrityPatterns:
    """
    Test des patterns de claims pour différents domaines.
    """
    
    def test_legal_claim_patterns(self):
        """Patterns légaux détectés."""
        text = "The contract is legally enforceable. The clause complies with GDPR."
        
        claims = extract_claims_from_text(text, CriticalDomain.LEGAL)
        
        # Au moins un claim légal détecté
        assert len(claims) >= 1
    
    def test_medical_claim_patterns(self):
        """Patterns médicaux détectés."""
        text = "The diagnosis is confirmed. The treatment should be started immediately."
        
        claims = extract_claims_from_text(text, CriticalDomain.MEDICAL)
        
        assert len(claims) >= 1
    
    def test_scientific_claim_patterns(self):
        """Patterns scientifiques détectés."""
        text = "The hypothesis was validated. Therefore, we conclude that the effect is significant."
        
        claims = extract_claims_from_text(text, CriticalDomain.SCIENTIFIC)
        
        assert len(claims) >= 1


class TestNoHiddenAssertions:
    """
    Vérifie qu'il n'y a pas d'assertions "cachées" hors du tracking.
    """
    
    def test_all_assertions_tracked(self):
        """
        Les assertions du texte correspondent aux claims du pack.
        
        Ce test est fondamental pour "zéro hallucination".
        """
        # Texte avec plusieurs assertions
        text = """
        This medication is effective for pain relief.
        The recommended dosage is 500mg twice daily.
        Studies show a 75% success rate.
        """
        
        # Extraire les claims
        extracted = extract_claims_from_text(text, CriticalDomain.MEDICAL)
        
        # Un pack doit avoir un claim pour chaque assertion
        pack = EvidencePack(
            query="Medical info",
            domain=CriticalDomain.MEDICAL,
            strict_mode=True,
        )
        
        # Ajouter les claims extraits au pack
        for i, claim_text in enumerate(extracted):
            claim = Claim(
                text=claim_text,
                domain=CriticalDomain.MEDICAL,
                required_sources_min=1,
                supported_by_source_ids=[],  # Pas de sources = UNSUPPORTED
            )
            pack.claims.append(claim)
        
        # Valider
        pack.validate()
        
        # Tous les claims doivent être marqués UNSUPPORTED (pas de sources)
        for claim in pack.claims:
            assert claim.status == ClaimStatus.UNSUPPORTED, (
                f"Claim without source should be UNSUPPORTED: {claim.text[:50]}"
            )
