"""
Tests E2E — Legal Pipeline Evidence

P0.6 Scénarios:
1. LOW: Question simple article → approved
2. BOARD: Cas DICA (Gayssot) → approved ou safe_analysis si pièce manque
3. HIGH: M&A → refuse/human review

Ces tests valident le pipeline complet:
Router → Agent (Draft) → Judge → Consensus → Output
"""

import pytest
from datetime import datetime

# Import legal pipeline components
from python.helpers.legal_pipeline import (
    # P0.1 - Routing
    LegalRiskTier,
    DecisionScope,
    Jurisdiction,
    LegalRouteContext,
    detect_legal_context,
    # P0.2 - Draft
    ClaimType,
    LegalClaim,
    LegalDraft,
    generate_draft_id,
    # P0.3 - Judge
    JudgeCheckResult,
    JudgeCheck,
    LegalJudgeVerdict,
    LegalJudgeResult,
    judge_legal_draft,
    # P0.4 - Consensus
    LegalConsensusType,
    LegalConsensusProposal,
    build_legal_consensus_proposal,
    # P0.5 - Output
    LegalOutputMode,
    LegalOutput,
    build_legal_output,
    # P0.7 - Premium Gate
    MissingInfoCode,
    requires_consensus,
    generate_audit_bundle_id,
)

from python.helpers.legal_retrieval import (
    extract_legal_identifiers,
    LegalRetriever,
    RetrievalResult,
    RetrievalContext,
)


# ═══════════════════════════════════════════════════════════════════════════════
# P0.1 — ROUTING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalRouteContext:
    """Tests for legal context detection."""
    
    def test_low_risk_simple_question(self):
        """Question simple = LOW risk, INFO scope."""
        text = "Qu'est-ce que l'article 1134 du code civil ?"
        
        ctx = detect_legal_context(text)
        
        assert ctx.risk_tier == LegalRiskTier.LOW
        assert ctx.scope == DecisionScope.INFO
        assert ctx.jurisdiction == Jurisdiction.FR
        assert "1134" in ctx.detected_articles
    
    def test_medium_risk_contract(self):
        """Question contrat = MEDIUM risk, OPERATIONAL scope."""
        text = "Quelle clause de non-concurrence est valide dans ce contrat de travail ?"
        
        ctx = detect_legal_context(text)
        
        assert ctx.risk_tier == LegalRiskTier.MEDIUM
        assert ctx.scope == DecisionScope.OPERATIONAL
    
    def test_high_risk_ma(self):
        """M&A = HIGH risk, BOARD scope."""
        text = "Analyse juridique de l'acquisition d'entreprise avec due diligence"
        
        ctx = detect_legal_context(text)
        
        assert ctx.risk_tier == LegalRiskTier.HIGH
        assert ctx.scope == DecisionScope.BOARD
    
    def test_high_risk_contentieux(self):
        """Contentieux majeur = HIGH risk."""
        text = "Stratégie de défense pour le contentieux en cassation"
        
        ctx = detect_legal_context(text)
        
        assert ctx.risk_tier == LegalRiskTier.HIGH
        assert ctx.is_contentieux == True
    
    def test_jurisdiction_fr(self):
        """Code civil = FR jurisdiction."""
        text = "Application de l'article L132-8 du code civil"
        
        ctx = detect_legal_context(text)
        
        assert ctx.jurisdiction == Jurisdiction.FR
    
    def test_jurisdiction_eu(self):
        """RGPD = EU jurisdiction."""
        text = "Conformité au RGPD et au règlement européen"
        
        ctx = detect_legal_context(text)
        
        # RGPD triggers both FR and EU patterns, so it should be MIXED
        # Actually, RGPD is in EU patterns
        assert ctx.jurisdiction in [Jurisdiction.EU, Jurisdiction.MIXED]
    
    def test_jurisdiction_mixed(self):
        """Mix FR + EU = MIXED, requires clarification."""
        text = "Application du code civil français et du règlement européen GDPR"
        
        ctx = detect_legal_context(text)
        
        assert ctx.jurisdiction == Jurisdiction.MIXED
        assert ctx.requires_jurisdiction_clarification == True
    
    def test_article_extraction(self):
        """Extract article references."""
        text = "L'article L132-8 et l'article 1134 du code civil"
        
        ctx = detect_legal_context(text)
        
        # Should find both articles
        assert len(ctx.detected_articles) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# P0.2 — DRAFT + CLAIMS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalDraft:
    """Tests for LegalDraft structure."""
    
    def test_create_draft(self):
        """Create a basic draft."""
        draft = LegalDraft(
            draft_id="draft_001",
            query="Test query",
            facts=["Fait 1", "Fait 2"],
            rules=["Article 1134 Code civil"],
            application="L'article s'applique car...",
        )
        
        assert draft.draft_id == "draft_001"
        assert len(draft.facts) == 2
        assert len(draft.rules) == 1
    
    def test_add_cited_claim(self):
        """Add a cited claim."""
        draft = LegalDraft(draft_id="draft_002", query="Test")
        
        draft.add_cited_claim(
            text="Le contrat est valide",
            citation="Art. 1134 C. civ.",
            chunk_id="chunk_123"
        )
        
        assert len(draft.claims) == 1
        assert draft.claims[0].claim_type == ClaimType.CITED
        assert draft.claims[0].citation == "Art. 1134 C. civ."
        assert draft.claims[0].is_valid == True
    
    def test_add_hypothesis_claim(self):
        """Add a hypothesis claim."""
        draft = LegalDraft(draft_id="draft_003", query="Test")
        
        draft.add_hypothesis_claim(
            text="Hypothèse: le délai est de 5 ans",
            basis="Non spécifié dans les faits fournis"
        )
        
        assert len(draft.claims) == 1
        assert draft.claims[0].claim_type == ClaimType.HYPOTHESIS
        assert draft.claims[0].is_valid == True
    
    def test_unsupported_claim_invalid(self):
        """Unsupported claims are invalid."""
        claim = LegalClaim(
            id="claim_1",
            text="Affirmation sans preuve",
            claim_type=ClaimType.UNSUPPORTED,
        )
        
        assert claim.is_valid == False
    
    def test_cited_claim_without_citation_invalid(self):
        """Cited claim without citation is invalid."""
        claim = LegalClaim(
            id="claim_1",
            text="Claim prétendu cité",
            claim_type=ClaimType.CITED,
            citation=None,  # Missing!
        )
        
        assert claim.is_valid == False
    
    def test_draft_has_unsupported_claims(self):
        """Detect unsupported claims in draft."""
        draft = LegalDraft(draft_id="draft_004", query="Test")
        
        # Add valid claim
        draft.add_cited_claim("Valid", "Art. 1", "chunk_1")
        
        # Add unsupported claim
        draft.claims.append(LegalClaim(
            id="claim_bad",
            text="Unsupported",
            claim_type=ClaimType.UNSUPPORTED,
        ))
        
        assert draft.has_unsupported_claims == True
        assert len(draft.unsupported_claims) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# P0.3 — JUDGE CHECKLIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgeChecklist:
    """Tests for judge binary checklist."""
    
    def test_judge_complete_draft_approve(self):
        """Complete draft = APPROVE."""
        ctx = detect_legal_context("Article 1134 code civil")
        
        draft = LegalDraft(
            draft_id="draft_complete",
            query="Validité du contrat",
            facts=["Le contrat a été signé le 1er janvier 2024"],
            rules=["Article 1134 Code civil: les conventions légalement formées tiennent lieu de loi"],
            application="L'article 1134 s'applique car le contrat a été formé légalement entre les parties.",
            citations=["Art. 1134 C. civ."],
            legal_context=ctx,
        )
        draft.add_cited_claim(
            "Le contrat est valide",
            "Art. 1134 C. civ.",
        )
        
        result = judge_legal_draft(draft)
        
        assert result.verdict == LegalJudgeVerdict.APPROVE
        assert len(result.critical_failures) == 0
    
    def test_judge_no_facts_reject(self):
        """No facts = REJECT (FACTS_SEPARATED fails)."""
        draft = LegalDraft(
            draft_id="draft_no_facts",
            query="Test",
            facts=[],  # Empty!
            rules=["Article 1134"],
            application="Application...",
            citations=["Art. 1134"],
        )
        
        result = judge_legal_draft(draft)
        
        assert result.verdict == LegalJudgeVerdict.REJECT
        assert "FACTS_SEPARATED" in result.critical_failures
    
    def test_judge_no_rules_reject(self):
        """No rules = REJECT (SOURCES_PRESENT fails)."""
        draft = LegalDraft(
            draft_id="draft_no_rules",
            query="Test",
            facts=["Fait 1"],
            rules=[],  # Empty!
            application="Application...",
        )
        
        result = judge_legal_draft(draft)
        
        assert result.verdict == LegalJudgeVerdict.REJECT
        assert "SOURCES_PRESENT" in result.critical_failures
    
    def test_judge_no_application_reject(self):
        """No application = REJECT (APPLICATION_PRESENT fails)."""
        draft = LegalDraft(
            draft_id="draft_no_app",
            query="Test",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="",  # Empty!
            citations=["Art. 1134"],
        )
        
        result = judge_legal_draft(draft)
        
        assert result.verdict == LegalJudgeVerdict.REJECT
        assert "APPLICATION_PRESENT" in result.critical_failures
    
    def test_judge_unsupported_claims_reject(self):
        """Unsupported claims = REJECT."""
        draft = LegalDraft(
            draft_id="draft_unsupported",
            query="Test",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="Application détaillée qui fait plus de 50 caractères...",
            citations=["Art. 1134"],
        )
        draft.claims.append(LegalClaim(
            id="bad_claim",
            text="Affirmation non étayée",
            claim_type=ClaimType.UNSUPPORTED,
        ))
        
        result = judge_legal_draft(draft)
        
        assert result.verdict == LegalJudgeVerdict.REJECT
        assert "NO_UNSUPPORTED_CLAIMS" in result.critical_failures
    
    def test_judge_check_pass_rate(self):
        """Calculate pass rate correctly."""
        draft = LegalDraft(
            draft_id="draft_partial",
            query="Test",
            facts=["Fait 1"],
            rules=[],  # Will fail SOURCES_PRESENT
            application="Application détaillée qui fait plus de 50 caractères...",
        )
        
        result = judge_legal_draft(draft)
        
        # Should have some passes and some fails
        assert result.total_count >= 6
        assert result.passed_count < result.total_count
        assert 0.0 < result.pass_rate < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# P0.4 — CONSENSUS ON CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusOnContract:
    """Tests for consensus on contract (not opinion)."""
    
    def test_build_consensus_proposal(self):
        """Build consensus proposal from draft."""
        ctx = detect_legal_context("Article 1134")
        
        draft = LegalDraft(
            draft_id="draft_consensus",
            query="Test",
            facts=["Fait"],
            rules=["Rule"],
            application="Application...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim", "Art. 1134")
        
        judge_result = judge_legal_draft(draft)
        proposal = build_legal_consensus_proposal(draft, judge_result)
        
        # Should have 3 items
        assert len(proposal.items) == 3
        
        # Items should be contract-based, not opinion-based
        item_types = {i.item_type for i in proposal.items}
        assert LegalConsensusType.CONTRACT_COMPLIANCE in item_types
        assert LegalConsensusType.CLAIM_SUPPORT in item_types
        assert LegalConsensusType.RISK_TIER_CONSISTENCY in item_types
    
    def test_quorum_low_risk(self):
        """LOW risk = 2/3 quorum."""
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_low",
            query="Test",
            legal_context=ctx,
        )
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        proposal = build_legal_consensus_proposal(draft, judge_result)
        
        assert proposal.required_approvals == 2
        assert proposal.require_unanimity == False
    
    def test_quorum_high_risk(self):
        """HIGH risk = unanimity."""
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_high",
            query="M&A due diligence",
            legal_context=ctx,
        )
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        proposal = build_legal_consensus_proposal(draft, judge_result)
        
        assert proposal.required_approvals == 3
        assert proposal.require_unanimity == True


# ═══════════════════════════════════════════════════════════════════════════════
# P0.5 — OUTPUT MODES + BANNER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputModes:
    """Tests for 3 output modes + banners."""
    
    def test_approved_position_mode(self):
        """Test APPROVED_POSITION mode."""
        ctx = detect_legal_context("Article 1134")
        
        draft = LegalDraft(
            draft_id="draft_approved",
            query="Test",
            facts=["Fait"],
            rules=["Rule"],
            application="Application complète...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        consensus_result = {"status": "APPROVED", "proposal_id": "prop_123"}
        
        output = build_legal_output(draft, judge_result, consensus_result)
        
        assert output.mode == LegalOutputMode.APPROVED_POSITION
        assert "POSITION VALIDÉE" in output.get_banner()
        assert output.audit_bundle_id != ""
    
    def test_safe_analysis_mode(self):
        """Test SAFE_ANALYSIS mode (judge OK, no consensus)."""
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,  # LOW doesn't require consensus
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_safe",
            query="Test",
            facts=["Fait"],
            rules=["Rule"],
            application="Application...",
            legal_context=ctx,
        )
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        output = build_legal_output(draft, judge_result, None)
        
        assert output.mode == LegalOutputMode.SAFE_ANALYSIS
        assert "ANALYSE SÉCURISÉE" in output.get_banner()
    
    def test_refusal_mode(self):
        """Test REFUSAL mode (judge REJECT)."""
        draft = LegalDraft(
            draft_id="draft_refusal",
            query="Test",
            facts=[],  # Will fail
            rules=[],
            application="",
        )
        
        judge_result = judge_legal_draft(draft)
        
        output = build_legal_output(draft, judge_result, None)
        
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO
        assert "REFUS" in output.get_banner()
        assert len(output.missing_info) > 0
    
    def test_audit_bundle_always_present(self):
        """Audit bundle ID always present, even in refusal."""
        draft = LegalDraft(
            draft_id="draft_any",
            query="Test",
        )
        
        judge_result = LegalJudgeResult(
            verdict=LegalJudgeVerdict.REJECT,
            missing_info_required=["facts_list"],
        )
        
        output = build_legal_output(draft, judge_result, None)
        
        assert output.audit_bundle_id != ""
        assert output.audit_bundle_id.startswith("audit_")
    
    def test_disclaimer_always_present(self):
        """Disclaimer always present."""
        draft = LegalDraft(draft_id="draft_disclaimer", query="Test")
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        output = build_legal_output(draft, judge_result, None)
        
        assert "provenance" in output.disclaimer.lower()
        assert "traçabilité" in output.disclaimer.lower()
    
    def test_output_validation(self):
        """Test output validation."""
        # Valid APPROVED_POSITION
        output = LegalOutput(
            mode=LegalOutputMode.APPROVED_POSITION,
            answer="Réponse",
            citations=["Art. 1134"],
            consensus_status="APPROVED",
            audit_bundle_id="audit_123",
        )
        is_valid, errors = output.validate()
        assert is_valid == True
        
        # Invalid APPROVED_POSITION (no citations)
        output_bad = LegalOutput(
            mode=LegalOutputMode.APPROVED_POSITION,
            answer="Réponse",
            citations=[],  # Missing!
            consensus_status="APPROVED",
            audit_bundle_id="audit_123",
        )
        is_valid, errors = output_bad.validate()
        assert is_valid == False
    
    def test_markdown_output(self):
        """Test markdown formatting."""
        ctx = detect_legal_context("Article 1134")
        
        draft = LegalDraft(
            draft_id="draft_md",
            query="Test",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="L'article s'applique...",
            risks=["Risque de nullité"],
            citations=["Art. 1134 C. civ."],
            legal_context=ctx,
        )
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        output = build_legal_output(draft, judge_result, None)
        
        md = output.to_markdown()
        
        assert "##" in md  # Has headers
        assert "Faits" in md
        assert "Règles" in md
        assert "Avertissement" in md


# ═══════════════════════════════════════════════════════════════════════════════
# P0.6 — E2E INTEGRATION TESTS (3 SCÉNARIOS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EScenarios:
    """
    E2E tests for 3 scenarios:
    1. LOW: Question simple article → approved
    2. BOARD: Cas complexe → approved ou safe_analysis si pièce manque
    3. HIGH: M&A → refuse/human review
    """
    
    def test_scenario_1_low_simple_article(self):
        """
        SCENARIO 1: LOW
        Question: "Qu'est-ce que l'article 1134 du code civil ?"
        Expected: APPROVED ou SAFE_ANALYSIS
        """
        query = "Qu'est-ce que l'article 1134 du code civil ?"
        
        # STEP 1: Router
        ctx = detect_legal_context(query)
        assert ctx.risk_tier == LegalRiskTier.LOW
        assert ctx.scope == DecisionScope.INFO
        assert ctx.jurisdiction == Jurisdiction.FR
        
        # STEP 2: Draft (simulated agent output)
        draft = LegalDraft(
            draft_id=generate_draft_id(query, datetime.now().timestamp()),
            query=query,
            facts=["L'utilisateur demande une explication de l'article 1134"],
            rules=["Article 1134 Code civil (ancien): Les conventions légalement formées tiennent lieu de loi à ceux qui les ont faites"],
            application="Cet article fondamental pose le principe de la force obligatoire du contrat. Il signifie que les parties sont liées par le contrat qu'elles ont conclu.",
            risks=[],
            next_action="Aucune action requise - question informationnelle",
            citations=["Art. 1134 C. civ. (ancien, recodifié art. 1103 nouveau)"],
            legal_context=ctx,
        )
        draft.add_cited_claim(
            "Les conventions légalement formées ont force de loi",
            "Art. 1134 C. civ.",
        )
        
        # STEP 3: Judge
        judge_result = judge_legal_draft(draft)
        assert judge_result.verdict == LegalJudgeVerdict.APPROVE
        
        # STEP 4: Consensus (not required for LOW)
        # LOW risk + INFO scope = no consensus needed
        
        # STEP 5: Output
        output = build_legal_output(draft, judge_result, None)
        
        # For LOW risk, should be SAFE_ANALYSIS (no consensus required)
        assert output.mode == LegalOutputMode.SAFE_ANALYSIS
        assert output.audit_bundle_id != ""
        assert len(output.citations) > 0
        
        print(f"\n=== SCENARIO 1: LOW ===")
        print(f"Query: {query}")
        print(f"Risk: {ctx.risk_tier.value}, Scope: {ctx.scope.value}")
        print(f"Judge: {judge_result.verdict.value}")
        print(f"Output: {output.mode.value}")
        print(f"Banner: {output.get_banner()}")
    
    def test_scenario_2_board_complex(self):
        """
        SCENARIO 2: BOARD (MEDIUM risk)
        Question: Analyse clause de non-concurrence (stratégique mais pas M&A)
        Expected: APPROVED si complet, SAFE_ANALYSIS si pièce manque
        """
        # Query without HIGH triggers like "due diligence" or "M&A"
        query = "Analyse stratégique de la clause de non-concurrence dans le contrat commercial (droit français, code du travail)"
        
        # STEP 1: Router
        ctx = detect_legal_context(query)
        assert ctx.risk_tier == LegalRiskTier.MEDIUM, f"Expected MEDIUM, got {ctx.risk_tier.value} (score={ctx.risk_score})"
        assert ctx.scope in [DecisionScope.OPERATIONAL, DecisionScope.BOARD]
        
        # STEP 2: Draft (complet)
        draft = LegalDraft(
            draft_id=generate_draft_id(query, datetime.now().timestamp()),
            query=query,
            facts=[
                "Cession d'entreprise en cours",
                "Clause de non-concurrence proposée: 2 ans, territoire national",
                "Cédant: dirigeant fondateur avec know-how critique",
            ],
            rules=[
                "Article L. 1121-1 Code du travail: la clause doit être limitée",
                "Jurisprudence Cass. soc.: critères de validité (durée, espace, activité, contrepartie)",
            ],
            application="La clause de non-concurrence de 2 ans sur le territoire national paraît proportionnée. Elle doit prévoir une contrepartie financière (indemnité de non-concurrence).",
            risks=[
                "Absence de contrepartie = nullité de la clause",
                "Durée excessive pourrait être réduite judiciairement",
            ],
            next_action="Vérifier la présence d'une contrepartie financière dans le projet de contrat",
            citations=[
                "Art. L. 1121-1 C. trav.",
                "Cass. soc., 10 juill. 2002, n° 00-45.135",
            ],
            legal_context=ctx,
        )
        draft.add_cited_claim(
            "La clause doit être limitée dans le temps et l'espace",
            "Art. L. 1121-1 C. trav.",
        )
        draft.add_cited_claim(
            "Une contrepartie financière est exigée",
            "Cass. soc., 10 juill. 2002",
        )
        
        # STEP 3: Judge
        judge_result = judge_legal_draft(draft)
        
        # Should pass judge
        assert judge_result.verdict == LegalJudgeVerdict.APPROVE, f"Failed checks: {judge_result.critical_failures}"
        
        # STEP 4: Consensus
        proposal = build_legal_consensus_proposal(draft, judge_result)
        
        # BOARD level should require 2/3
        assert proposal.required_approvals == 2
        
        # Simulate consensus APPROVED
        consensus_result = {
            "status": "APPROVED",
            "proposal_id": proposal.proposal_id,
            "votes": {"arbiter_1": "approve", "arbiter_2": "approve", "arbiter_3": "abstain"},
        }
        
        # STEP 5: Output
        output = build_legal_output(draft, judge_result, consensus_result)
        
        assert output.mode == LegalOutputMode.APPROVED_POSITION
        assert output.audit_bundle_id != ""
        
        print(f"\n=== SCENARIO 2: BOARD ===")
        print(f"Query: {query[:50]}...")
        print(f"Risk: {ctx.risk_tier.value}, Scope: {ctx.scope.value}")
        print(f"Judge: {judge_result.verdict.value} ({judge_result.pass_rate:.0%})")
        print(f"Consensus: {proposal.required_approvals}/3 required")
        print(f"Output: {output.mode.value}")
        print(f"Banner: {output.get_banner()}")
    
    def test_scenario_2b_board_missing_info(self):
        """
        SCENARIO 2b: BOARD with missing info
        Expected: REFUSAL_REQUEST_INFO
        """
        query = "Analyse de la clause de non-concurrence"
        
        ctx = detect_legal_context(query)
        
        # Draft incomplet (pas de faits)
        draft = LegalDraft(
            draft_id=generate_draft_id(query, datetime.now().timestamp()),
            query=query,
            facts=[],  # Missing!
            rules=["Article L. 1121-1"],
            application="",  # Missing!
            legal_context=ctx,
        )
        
        # Judge should reject
        judge_result = judge_legal_draft(draft)
        assert judge_result.verdict == LegalJudgeVerdict.REJECT
        
        # Output should be REFUSAL
        output = build_legal_output(draft, judge_result, None)
        
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO
        assert len(output.missing_info) > 0
        
        print(f"\n=== SCENARIO 2b: BOARD MISSING INFO ===")
        print(f"Judge: {judge_result.verdict.value}")
        print(f"Missing: {output.missing_info}")
        print(f"Output: {output.mode.value}")
    
    def test_scenario_3_high_ma(self):
        """
        SCENARIO 3: HIGH (M&A)
        Question: Due diligence M&A
        Expected: Consensus unanime requis, APPROVED ou REFUSAL selon résultat
        """
        query = "Analyse juridique stratégique pour l'acquisition d'entreprise XYZ - due diligence M&A LBO avec valorisation et risques (droit français, code de commerce)"
        
        # STEP 1: Router
        ctx = detect_legal_context(query)
        assert ctx.risk_tier == LegalRiskTier.HIGH, f"Expected HIGH, got {ctx.risk_tier.value} (score={ctx.risk_score})"
        assert ctx.scope == DecisionScope.BOARD, f"Expected BOARD, got {ctx.scope.value} (score={ctx.scope_score})"
        
        # STEP 2: Draft (complet pour M&A)
        draft = LegalDraft(
            draft_id=generate_draft_id(query, datetime.now().timestamp()),
            query=query,
            facts=[
                "Cible: entreprise XYZ, SAS au capital de 1M€",
                "Acquéreur: fonds d'investissement",
                "Valorisation proposée: 10M€",
                "Mécanisme: LBO avec effet de levier",
            ],
            rules=[
                "Article L. 223-1 et suivants C. com.: régime des SAS",
                "Article L. 228-11 C. com.: actions de préférence",
                "Directive 2017/1132: opérations transfrontalières",
            ],
            application=(
                "L'acquisition nécessite: (1) audit des passifs sociaux et environnementaux, "
                "(2) garantie de passif standard, (3) earn-out éventuel, "
                "(4) pacte d'actionnaires avec clause de sortie."
            ),
            risks=[
                "Risque fiscal: vérifier les déficits reportables",
                "Risque social: due diligence RH (PSE antérieur?)",
                "Risque environnemental: sites ICPE?",
                "Risque concurrence: notification à l'Autorité si seuils atteints",
            ],
            next_action="Recommandation: mandater un audit juridique complet avant signing",
            citations=[
                "Art. L. 223-1 C. com.",
                "Art. L. 228-11 C. com.",
                "Directive 2017/1132/UE",
            ],
            legal_context=ctx,
        )
        draft.add_cited_claim(
            "Le régime des SAS permet une grande flexibilité statutaire",
            "Art. L. 223-1 C. com.",
        )
        draft.add_cited_claim(
            "Les actions de préférence peuvent être utilisées pour le management package",
            "Art. L. 228-11 C. com.",
        )
        draft.add_hypothesis_claim(
            "Les seuils de notification concurrence pourraient être atteints",
            "Dépend du CA consolidé non fourni"
        )
        
        # STEP 3: Judge
        judge_result = judge_legal_draft(draft)
        
        # Should pass with HIGH risk draft
        assert judge_result.verdict == LegalJudgeVerdict.APPROVE, f"Failed: {judge_result.critical_failures}"
        
        # STEP 4: Consensus
        proposal = build_legal_consensus_proposal(draft, judge_result)
        
        # HIGH risk requires unanimity
        assert proposal.required_approvals == 3
        assert proposal.require_unanimity == True
        
        # Test case A: Consensus unanime → APPROVED
        consensus_approved = {
            "status": "APPROVED",
            "proposal_id": proposal.proposal_id,
            "votes": {"arbiter_1": "approve", "arbiter_2": "approve", "arbiter_3": "approve"},
        }
        
        output_approved = build_legal_output(draft, judge_result, consensus_approved)
        assert output_approved.mode == LegalOutputMode.APPROVED_POSITION
        
        # Test case B: Consensus rejeté → REFUSAL (P0.7: HIGH risk requires consensus)
        consensus_rejected = {
            "status": "REJECTED",
            "proposal_id": proposal.proposal_id,
            "votes": {"arbiter_1": "approve", "arbiter_2": "reject", "arbiter_3": "approve"},
        }
        
        output_rejected = build_legal_output(draft, judge_result, consensus_rejected)
        # P0.7 Invariant C: HIGH risk with rejected consensus = REFUSAL
        assert output_rejected.mode == LegalOutputMode.REFUSAL_REQUEST_INFO
        assert MissingInfoCode.CONSENSUS_REJECTED in output_rejected.missing_info
        
        print(f"\n=== SCENARIO 3: HIGH (M&A) ===")
        print(f"Query: {query[:50]}...")
        print(f"Risk: {ctx.risk_tier.value}, Scope: {ctx.scope.value}")
        print(f"Judge: {judge_result.verdict.value} ({judge_result.pass_rate:.0%})")
        print(f"Consensus required: {proposal.required_approvals}/3, unanimity={proposal.require_unanimity}")
        print(f"Output (approved consensus): {output_approved.mode.value}")
        print(f"Output (rejected consensus): {output_rejected.mode.value}")


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalIdentifierExtraction:
    """Tests for legal identifier extraction."""
    
    def test_extract_legiarti(self):
        """Extract LEGIARTI identifiers."""
        text = "Voir LEGIARTI000006438532 pour l'article 1134"
        
        ids = extract_legal_identifiers(text)
        
        assert len(ids["legiarti"]) == 1
        assert "LEGIARTI000006438532" in ids["legiarti"]
    
    def test_extract_pourvoi(self):
        """Extract pourvoi numbers."""
        text = "Arrêt de cassation n° 19-25.123 et 2020-12345"
        
        ids = extract_legal_identifiers(text)
        
        assert len(ids["pourvoi"]) == 2
    
    def test_extract_ecli(self):
        """Extract ECLI."""
        text = "ECLI:FR:CCASS:2020:C00123"
        
        ids = extract_legal_identifiers(text)
        
        assert len(ids["ecli"]) == 1
    
    def test_extract_articles(self):
        """Extract article references."""
        text = "Articles L132-8 et 1134 du code civil"
        
        ids = extract_legal_identifiers(text)
        
        assert len(ids["articles"]) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# P0.7 — PREMIUM GATE INVARIANT TESTS (8 tests obligatoires)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPremiumGateInvariants:
    """
    P0.7 Premium Gate — 8 invariants, 8 tests.
    
    Ces tests PROUVENT les propriétés du système, pas juste l'implémentation.
    Chaque test doit échouer si l'invariant est réintroduit.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # T1: audit_bundle_id is deterministic (no timestamp)
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_audit_bundle_id_is_deterministic(self):
        """
        T1 — Invariant A: même draft + mêmes citations/chunks => même audit_bundle_id.
        
        PREUVE: Appeler generate_audit_bundle_id 2x avec mêmes inputs doit
        retourner la même valeur. Aucun timestamp ou random.
        """
        draft_id = "draft_test_deterministic"
        output_mode = "approved_position"
        chunk_ids = ["chunk_abc", "chunk_def", "chunk_xyz"]
        citations = ["Art. 1134 C. civ.", "Cass. soc. 2020"]
        
        # Call twice
        audit_id_1 = generate_audit_bundle_id(draft_id, output_mode, chunk_ids, citations)
        audit_id_2 = generate_audit_bundle_id(draft_id, output_mode, chunk_ids, citations)
        
        assert audit_id_1 == audit_id_2, "audit_bundle_id must be deterministic"
        
        # Call with different order (should still be same due to sorting)
        audit_id_3 = generate_audit_bundle_id(
            draft_id, output_mode,
            ["chunk_xyz", "chunk_abc", "chunk_def"],  # Different order
            ["Cass. soc. 2020", "Art. 1134 C. civ."],  # Different order
        )
        
        assert audit_id_1 == audit_id_3, "audit_bundle_id must be stable regardless of input order"
        
        # Different inputs = different ID
        audit_id_different = generate_audit_bundle_id(draft_id, "safe_analysis", chunk_ids, citations)
        assert audit_id_1 != audit_id_different, "Different inputs must produce different IDs"
    
    # ─────────────────────────────────────────────────────────────────────────
    # T2: non-REFUSAL requires provenance
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_non_refusal_requires_provenance(self):
        """
        T2 — Invariant B: build output SAFE/APPROVED sans provenance => REFUSAL.
        
        PREUVE: Un draft avec source_chunk_ids mais sans provenance_map
        doit produire REFUSAL avec missing_info contenant "provenance_missing".
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,  # LOW = no consensus required
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_provenance_test",
            query="Test",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="Application détaillée qui fait plus de 50 caractères pour passer le check...",
            citations=["Art. 1134"],
            source_chunk_ids=["chunk_123", "chunk_456"],  # Chunks without provenance
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim valide", "Art. 1134")
        
        judge_result = judge_legal_draft(draft)
        assert judge_result.verdict == LegalJudgeVerdict.APPROVE, "Judge should approve this draft"
        
        # Build output WITHOUT provenance_map (simulates missing provenance)
        # Since resolve_provenance_for_chunks will return empty dicts, validation fails
        output = build_legal_output(draft, judge_result, None, provenance_map=None)
        
        # With chunks but no provenance, should be REFUSAL
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO, \
            "Without provenance, output must be REFUSAL"
        assert MissingInfoCode.PROVENANCE_MISSING in output.missing_info, \
            "missing_info must contain 'provenance_missing'"
    
    # ─────────────────────────────────────────────────────────────────────────
    # T3: BOARD scope requires consensus
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_board_scope_requires_consensus(self):
        """
        T3 — Invariant C: ctx.scope=BOARD + judge APPROVE + consensus=None => REFUSAL.
        
        PREUVE: BOARD scope ne peut jamais sortir SAFE_ANALYSIS sans consensus.
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,  # Even LOW risk...
            scope=DecisionScope.BOARD,   # ...with BOARD scope requires consensus
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_board_no_consensus",
            query="Stratégie de board",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="Application détaillée qui fait plus de 50 caractères pour passer le check...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim valide", "Art. 1134")
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        # No consensus provided
        output = build_legal_output(draft, judge_result, consensus_result=None)
        
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO, \
            "BOARD scope without consensus must produce REFUSAL"
        assert MissingInfoCode.CONSENSUS_REQUIRED in output.missing_info, \
            "missing_info must contain 'consensus_required'"
        
        # Verify requires_consensus function
        assert requires_consensus(ctx) == True, "BOARD scope must require consensus"
    
    # ─────────────────────────────────────────────────────────────────────────
    # T4: MEDIUM risk requires consensus
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_medium_risk_requires_consensus(self):
        """
        T4 — Invariant C: ctx.risk=MEDIUM + scope OPERATIONAL + judge APPROVE + consensus=None => REFUSAL.
        
        PREUVE: MEDIUM risk ne peut jamais sortir sans consensus.
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_medium_no_consensus",
            query="Clause contractuelle",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="Application détaillée qui fait plus de 50 caractères pour passer le check...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim valide", "Art. 1134")
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        # No consensus provided
        output = build_legal_output(draft, judge_result, consensus_result=None)
        
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO, \
            "MEDIUM risk without consensus must produce REFUSAL"
        assert MissingInfoCode.CONSENSUS_REQUIRED in output.missing_info
        
        # Verify requires_consensus function
        assert requires_consensus(ctx) == True, "MEDIUM risk must require consensus"
    
    # ─────────────────────────────────────────────────────────────────────────
    # T5: OPERATIONAL requires claims
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_operational_requires_claims(self):
        """
        T5 — Invariant D: scope OPERATIONAL + draft.claims=[] => judge REJECT + CLAIMS_REQUIRED.
        
        PREUVE: Les scopes OPERATIONAL/BOARD exigent des claims explicites.
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_no_claims_operational",
            query="Clause de non-concurrence",
            facts=["Fait 1"],
            rules=["Article L. 1121-1"],
            application="Application détaillée qui fait plus de 50 caractères pour passer le check...",
            citations=["Art. L. 1121-1 C. trav."],
            claims=[],  # NO CLAIMS!
            legal_context=ctx,
        )
        
        judge_result = judge_legal_draft(draft)
        
        assert judge_result.verdict == LegalJudgeVerdict.REJECT, \
            "OPERATIONAL scope without claims must be REJECTED"
        assert "CLAIMS_REQUIRED" in judge_result.critical_failures, \
            "critical_failures must contain 'CLAIMS_REQUIRED'"
        assert MissingInfoCode.CLAIMS_REQUIRED in judge_result.missing_info_required
    
    # ─────────────────────────────────────────────────────────────────────────
    # T6: OPERATIONAL SOURCES_PRESENT cannot WARN
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_operational_sources_present_cannot_warn(self):
        """
        T6 — Invariant E: scope OPERATIONAL + rules non vides + citations vides => SOURCES_PRESENT FAIL.
        
        PREUVE: En OPERATIONAL, rules sans citations = FAIL critique, pas WARN.
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_rules_no_citations",
            query="Test",
            facts=["Fait 1"],
            rules=["Article 1134", "Article 1135"],  # Rules present
            application="Application détaillée qui fait plus de 50 caractères...",
            citations=[],  # NO CITATIONS!
            source_chunk_ids=[],
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim", "Art. 1134")  # Has claim to pass CLAIMS_REQUIRED
        
        judge_result = judge_legal_draft(draft)
        
        # Find SOURCES_PRESENT check
        sources_check = next(
            (c for c in judge_result.checks if c.name == "SOURCES_PRESENT"),
            None
        )
        
        assert sources_check is not None, "SOURCES_PRESENT check must exist"
        assert sources_check.result == JudgeCheckResult.FAIL, \
            "OPERATIONAL with rules but no citations must FAIL (not WARN)"
        assert "SOURCES_PRESENT" in judge_result.critical_failures
    
    # ─────────────────────────────────────────────────────────────────────────
    # T7: APPROVED_POSITION only when consensus APPROVED
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_approved_position_only_when_consensus_approved(self):
        """
        T7 — Invariant F: consensus APPROVED => mode APPROVED_POSITION, sinon jamais.
        
        PREUVE: Le mode APPROVED_POSITION n'est possible que si consensus_status == "APPROVED".
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="draft_approved_test",
            query="Test",
            facts=["Fait"],
            rules=["Rule"],
            application="Application détaillée qui fait plus de 50 caractères...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        # INFO scope doesn't require claims, but let's add one anyway
        
        judge_result = LegalJudgeResult(verdict=LegalJudgeVerdict.APPROVE)
        
        # Case 1: Consensus APPROVED => APPROVED_POSITION
        consensus_approved = {"status": "APPROVED", "proposal_id": "prop_123"}
        output_1 = build_legal_output(draft, judge_result, consensus_approved)
        assert output_1.mode == LegalOutputMode.APPROVED_POSITION, \
            "Consensus APPROVED must produce APPROVED_POSITION"
        
        # Case 2: Consensus REJECTED => REFUSAL (because LOW requires consensus when provided and rejected)
        # Actually, LOW+INFO doesn't require consensus, so REJECTED should not matter
        # Let's use MEDIUM to test this properly
        ctx_medium = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        draft_medium = LegalDraft(
            draft_id="draft_medium_rejected",
            query="Test",
            facts=["Fait"],
            rules=["Rule"],
            application="Application détaillée qui fait plus de 50 caractères...",
            citations=["Art. 1134"],
            legal_context=ctx_medium,
        )
        draft_medium.add_cited_claim("Claim", "Art. 1134")
        
        consensus_rejected = {"status": "REJECTED", "proposal_id": "prop_456"}
        output_2 = build_legal_output(draft_medium, judge_result, consensus_rejected)
        assert output_2.mode == LegalOutputMode.REFUSAL_REQUEST_INFO, \
            "Consensus REJECTED must produce REFUSAL for MEDIUM risk"
        assert output_2.mode != LegalOutputMode.APPROVED_POSITION, \
            "APPROVED_POSITION must never occur with REJECTED consensus"
    
    # ─────────────────────────────────────────────────────────────────────────
    # T8: BOARD requires explicit jurisdiction (no silent FR presumption)
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_board_requires_explicit_jurisdiction(self):
        """
        T8 — Invariant H: scope BOARD + jurisdiction UNKNOWN => judge REQUEST_INFO/REJECT.
        
        PREUVE: En BOARD, la présomption FR silencieuse est interdite.
        """
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.UNKNOWN,  # NO JURISDICTION!
        )
        
        draft = LegalDraft(
            draft_id="draft_board_no_jurisdiction",
            query="Stratégie M&A",
            facts=["Fait 1"],
            rules=["Article 1134"],
            application="Application détaillée qui fait plus de 50 caractères...",
            citations=["Art. 1134"],
            legal_context=ctx,
        )
        draft.add_cited_claim("Claim", "Art. 1134")
        
        judge_result = judge_legal_draft(draft)
        
        # BOARD + UNKNOWN jurisdiction must not APPROVE
        assert judge_result.verdict != LegalJudgeVerdict.APPROVE, \
            "BOARD with UNKNOWN jurisdiction must NOT approve (no silent FR presumption)"
        
        # Check that JURISDICTION_CLEAR failed
        jurisdiction_check = next(
            (c for c in judge_result.checks if c.name == "JURISDICTION_CLEAR"),
            None
        )
        assert jurisdiction_check is not None
        assert jurisdiction_check.result == JudgeCheckResult.FAIL, \
            "JURISDICTION_CLEAR must FAIL for BOARD + UNKNOWN"
        assert "JURISDICTION_CLEAR" in judge_result.critical_failures
        assert MissingInfoCode.JURISDICTION in judge_result.missing_info_required


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
