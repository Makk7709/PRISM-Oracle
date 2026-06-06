"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P4.5: INTER-AGENT CONTRACT TESTS                          ║
║                                                                              ║
║  Tests for P4 Sources Officielles + Collaboration Inter-Agents:             ║
║  - Publisher whitelist enforcement                                          ║
║  - CITED claims must have SourceNote                                        ║
║  - Sub-agents cannot produce final answers                                   ║
║  - Provenance validation                                                    ║
║                                                                              ║
║  Version: 1.0.0 (P4)                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from unittest.mock import MagicMock, patch


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_WHITELIST_ENFORCEMENT"] = "1"
    # P5: Disable version enforcement for P4 tests (tested in test_legal_versioning.py)
    os.environ["LEGAL_VERSION_ENFORCEMENT"] = "0"
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)


# ═══════════════════════════════════════════════════════════════════════════════
# P4.1: ARTIFACT CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactExtraction:
    """Tests for FactExtraction artifact."""
    
    def test_valid_fact_extraction(self):
        """Valid FactExtraction should be accepted."""
        from python.helpers.legal_agent_contracts import FactExtraction
        
        fe = FactExtraction(
            facts=["Le contrat a été signé le 1er janvier 2024"],
            ambiguities=["Date d'effet non précisée"],
            parties=["Société A", "Société B"],
        )
        
        assert len(fe.facts) == 1
        assert len(fe.ambiguities) == 1
    
    def test_empty_facts_rejected(self):
        """FactExtraction with no facts should be rejected."""
        from python.helpers.legal_agent_contracts import FactExtraction, ContractValidationError
        
        with pytest.raises(ContractValidationError) as exc_info:
            FactExtraction(facts=[])
        
        assert "Must have at least one fact" in str(exc_info.value)
    
    def test_final_answer_in_facts_rejected(self):
        """FactExtraction with final answer pattern should be rejected."""
        from python.helpers.legal_agent_contracts import FactExtraction, FinalAnswerDetectedError
        
        with pytest.raises(FinalAnswerDetectedError):
            FactExtraction(
                facts=["En conclusion, le contrat est valide"],  # Final answer pattern
            )


class TestSourceNote:
    """Tests for SourceNote artifact."""
    
    def test_valid_source_note(self):
        """Valid SourceNote should be accepted."""
        from python.helpers.legal_agent_contracts import SourceNote, compute_excerpt_hash
        
        excerpt = "Les contrats légalement formés tiennent lieu de loi."
        
        sn = SourceNote(
            origin_url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006436298",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt=excerpt,
            excerpt_hash=compute_excerpt_hash(excerpt),
            chunk_id="chunk_001",
        )
        
        assert sn.publisher == "legifrance"
        assert sn.jurisdiction == "fr"
    
    def test_non_whitelisted_publisher_rejected(self):
        """SourceNote with non-whitelisted publisher should be rejected."""
        from python.helpers.legal_agent_contracts import (
            SourceNote, 
            NonWhitelistedPublisherError,
            compute_excerpt_hash,
        )
        
        excerpt = "Test excerpt"
        
        with pytest.raises(NonWhitelistedPublisherError) as exc_info:
            SourceNote(
                origin_url="https://example.com/doc",
                publisher="random_blog",  # Not whitelisted
                jurisdiction="fr",
                excerpt=excerpt,
                excerpt_hash=compute_excerpt_hash(excerpt),
                chunk_id="chunk_001",
            )
        
        assert "random_blog" in str(exc_info.value)
        assert "whitelist" in str(exc_info.value).lower()
    
    def test_invalid_excerpt_hash_rejected(self):
        """SourceNote with wrong excerpt hash should be rejected."""
        from python.helpers.legal_agent_contracts import SourceNote, ContractValidationError
        
        with pytest.raises(ContractValidationError) as exc_info:
            SourceNote(
                origin_url="https://www.legifrance.gouv.fr/test",
                publisher="legifrance",
                jurisdiction="fr",
                excerpt="Real excerpt",
                excerpt_hash="wrong_hash",  # Wrong hash
                chunk_id="chunk_001",
            )
        
        assert "Hash mismatch" in str(exc_info.value)
    
    def test_source_note_create_factory(self):
        """SourceNote.create() should auto-compute hash."""
        from python.helpers.legal_agent_contracts import SourceNote, compute_excerpt_hash
        
        excerpt = "Test excerpt for factory"
        
        sn = SourceNote.create(
            origin_url="https://www.legifrance.gouv.fr/test",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt=excerpt,
            chunk_id="chunk_001",
        )
        
        assert sn.excerpt_hash == compute_excerpt_hash(excerpt)


class TestClaimProposal:
    """Tests for ClaimProposal artifact."""
    
    def test_cited_claim_requires_source_note(self):
        """CITED claim without SourceNote should be rejected."""
        from python.helpers.legal_agent_contracts import (
            ClaimProposal, 
            ClaimType,
            ContractValidationError,
        )
        
        with pytest.raises(ContractValidationError) as exc_info:
            ClaimProposal(
                claim_text="Les contrats sont obligatoires",
                claim_type=ClaimType.CITED,
                citation="Art. 1103 C. civ.",
                # Missing source_note
            )
        
        assert "CITED claim must have a SourceNote" in str(exc_info.value)
    
    def test_hypothesis_claim_requires_basis(self):
        """HYPOTHESIS claim without basis should be rejected."""
        from python.helpers.legal_agent_contracts import (
            ClaimProposal, 
            ClaimType,
            ContractValidationError,
        )
        
        with pytest.raises(ContractValidationError) as exc_info:
            ClaimProposal(
                claim_text="Il est probable que...",
                claim_type=ClaimType.HYPOTHESIS,
                # Missing basis_if_hypothesis
            )
        
        assert "HYPOTHESIS claim must have a basis" in str(exc_info.value)
    
    def test_valid_cited_claim(self):
        """Valid CITED claim with SourceNote should be accepted."""
        from python.helpers.legal_agent_contracts import (
            ClaimProposal, 
            ClaimType,
            SourceNote,
            compute_excerpt_hash,
        )
        
        excerpt = "Les contrats légalement formés..."
        source_note = SourceNote(
            origin_url="https://www.legifrance.gouv.fr/test",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt=excerpt,
            excerpt_hash=compute_excerpt_hash(excerpt),
            chunk_id="chunk_001",
        )
        
        claim = ClaimProposal(
            claim_text="Les contrats sont obligatoires",
            claim_type=ClaimType.CITED,
            citation="Art. 1103 C. civ.",
            source_note=source_note,
            source_chunk_id="chunk_001",
        )
        
        assert claim.claim_type == ClaimType.CITED
        assert claim.source_note is not None


class TestCritique:
    """Tests for Critique artifact."""
    
    def test_critique_requires_findings(self):
        """Critique with no findings should be rejected."""
        from python.helpers.legal_agent_contracts import Critique, ContractValidationError
        
        with pytest.raises(ContractValidationError) as exc_info:
            Critique()  # All lists empty
        
        assert "Must have at least one finding" in str(exc_info.value)
    
    def test_valid_critique(self):
        """Valid Critique should be accepted."""
        from python.helpers.legal_agent_contracts import Critique
        
        critique = Critique(
            issues=["Absence de citation pour l'affirmation principale"],
            severity="high",
        )
        
        assert critique.is_blocking is True
        assert critique.total_findings == 1


# ═══════════════════════════════════════════════════════════════════════════════
# P4.2: FINAL ANSWER DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinalAnswerDetection:
    """Tests for final answer detection."""
    
    def test_detect_en_conclusion(self):
        """Should detect 'en conclusion' pattern."""
        from python.helpers.legal_agent_contracts import detect_final_answer
        
        assert detect_final_answer("En conclusion, le contrat est valide.") is True
    
    def test_detect_ma_reponse(self):
        """Should detect 'ma réponse est' pattern."""
        from python.helpers.legal_agent_contracts import detect_final_answer
        
        assert detect_final_answer("Ma réponse est que vous avez raison.") is True
    
    def test_detect_final_answer_label(self):
        """Should detect 'final answer' pattern."""
        from python.helpers.legal_agent_contracts import detect_final_answer
        
        assert detect_final_answer("Final answer: The contract is valid.") is True
    
    def test_normal_text_not_detected(self):
        """Normal factual text should not be detected."""
        from python.helpers.legal_agent_contracts import detect_final_answer
        
        assert detect_final_answer("Le contrat a été signé le 1er janvier.") is False
        assert detect_final_answer("L'article 1103 dispose que...") is False
    
    def test_reject_if_agent_output_contains_final_answer(self):
        """Sub-agent output with final answer should be rejected."""
        from python.helpers.legal_agent_contracts import (
            FactExtraction,
            FinalAnswerDetectedError,
        )
        
        with pytest.raises(FinalAnswerDetectedError):
            FactExtraction(
                facts=["Fait 1"],
                context_hints={"summary": "Pour conclure, voici le résumé"},
            )


# ═══════════════════════════════════════════════════════════════════════════════
# P4.3: WHITELIST ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublisherWhitelist:
    """Tests for publisher whitelist."""
    
    def test_legifrance_whitelisted(self):
        """Legifrance should be whitelisted."""
        from python.helpers.legal_agent_contracts import Publisher
        
        assert Publisher.is_whitelisted("legifrance") is True
        assert Publisher.is_whitelisted("LEGIFRANCE") is True
        assert Publisher.is_whitelisted("Legifrance") is True
    
    def test_eurlex_whitelisted(self):
        """EUR-Lex should be whitelisted."""
        from python.helpers.legal_agent_contracts import Publisher
        
        assert Publisher.is_whitelisted("eur-lex") is True
        assert Publisher.is_whitelisted("eur_lex") is True
    
    def test_random_publisher_not_whitelisted(self):
        """Random publishers should not be whitelisted."""
        from python.helpers.legal_agent_contracts import Publisher
        
        assert Publisher.is_whitelisted("wikipedia") is False
        assert Publisher.is_whitelisted("random_blog") is False
        assert Publisher.is_whitelisted("") is False
    
    def test_reject_if_non_whitelisted_publisher(self):
        """Sources from non-whitelisted publishers should be rejected."""
        from python.helpers.legal_agent_contracts import (
            SourceNote,
            NonWhitelistedPublisherError,
            compute_excerpt_hash,
        )
        
        excerpt = "Some text"
        
        with pytest.raises(NonWhitelistedPublisherError):
            SourceNote(
                origin_url="https://example.com/doc",
                publisher="blog_juridique",
                jurisdiction="fr",
                excerpt=excerpt,
                excerpt_hash=compute_excerpt_hash(excerpt),
                chunk_id="chunk_001",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# P4: ORCHESTRATOR INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestratorP4Integration:
    """Tests for P4 integration in orchestrator."""
    
    def test_whitelist_enforcement_flag(self):
        """Whitelist enforcement flag should be controllable."""
        from python.helpers.legal_orchestrator import is_whitelist_enforcement_enabled
        
        os.environ["LEGAL_WHITELIST_ENFORCEMENT"] = "1"
        assert is_whitelist_enforcement_enabled() is True
        
        os.environ["LEGAL_WHITELIST_ENFORCEMENT"] = "0"
        assert is_whitelist_enforcement_enabled() is False
    
    def test_p4_contracts_available(self):
        """P4 contracts should be available."""
        from python.helpers.legal_orchestrator import P4_CONTRACTS_AVAILABLE
        
        assert P4_CONTRACTS_AVAILABLE is True
    
    def test_validate_source_whitelist_all_valid(self):
        """Should return empty list when all sources are whitelisted."""
        from python.helpers.legal_orchestrator import validate_source_whitelist
        from python.helpers.legal_retrieval import RetrievalResult
        
        results = [
            RetrievalResult(
                chunk_id="chunk_001",
                doc_id="doc_001",
                source="legi",
                citation="Art. 1103",
                pinpoint="",
                text="Test text",
                text_snippet="Test...",
                provenance={"source": "legifrance"},
            ),
        ]
        
        non_whitelisted = validate_source_whitelist(
            results,
            correlation_id="test_001",
        )
        
        assert non_whitelisted == []
    
    def test_build_source_notes_from_retrieval(self):
        """Should build SourceNote objects from retrieval results."""
        from python.helpers.legal_orchestrator import build_source_notes_from_retrieval
        from python.helpers.legal_retrieval import RetrievalResult
        
        results = [
            RetrievalResult(
                chunk_id="chunk_001",
                doc_id="doc_001",
                source="legi",
                citation="Art. 1103 C. civ.",
                pinpoint="",
                text="Les contrats légalement formés...",
                text_snippet="Les contrats...",
                provenance={
                    "source": "legifrance",
                    "origin_url": "https://www.legifrance.gouv.fr/test",
                    "license_name": "Licence Ouverte 2.0",
                },
            ),
        ]
        
        source_notes = build_source_notes_from_retrieval(
            results,
            correlation_id="test_001",
        )
        
        assert "chunk_001" in source_notes
        assert source_notes["chunk_001"].publisher == "legifrance"


# ═══════════════════════════════════════════════════════════════════════════════
# P4.4: CORPUS VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCorpusValidation:
    """Tests for corpus validation."""
    
    def test_corpus_all_whitelisted(self):
        """All corpus documents should be from whitelisted publishers."""
        from tests.fixtures.legal_corpus import CORPUS
        from python.helpers.legal_agent_contracts import Publisher
        
        for doc in CORPUS:
            prov = doc.get("provenance", {})
            publisher = prov.get("source")
            
            assert Publisher.is_whitelisted(publisher), \
                f"Document {doc.get('origin_id')} has non-whitelisted publisher: {publisher}"
    
    def test_corpus_has_required_provenance(self):
        """All corpus documents should have required provenance fields."""
        from tests.fixtures.legal_corpus import CORPUS
        
        required_fields = ["source", "source_name", "origin_url", "license_name"]
        
        for doc in CORPUS:
            prov = doc.get("provenance", {})
            
            for field in required_fields:
                assert prov.get(field), \
                    f"Document {doc.get('origin_id')} missing provenance.{field}"


# ═══════════════════════════════════════════════════════════════════════════════
# P4: NO REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP4NoRegression:
    """Verify P4 doesn't break P0.7-P3."""
    
    @pytest.mark.asyncio
    async def test_pipeline_still_works(self):
        """Pipeline should still work with P4 additions."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        output = await run_legal_pipeline(
            query="Test query for P4",
            correlation_id="p4_test_001",
        )
        
        assert output is not None
        assert output.mode in list(LegalOutputMode)
    
    def test_p07_invariants_preserved(self):
        """P0.7 invariants should still be enforced."""
        from python.helpers.legal_pipeline import requires_consensus, LegalRouteContext
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope, Jurisdiction
        
        # BOARD scope requires consensus
        board_context = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.FR,
        )
        assert requires_consensus(board_context) is True


# ═══════════════════════════════════════════════════════════════════════════════
# NIGHTLY-ONLY E2E TESTS
# ═══════════════════════════════════════════════════════════════════════════════

nightly = pytest.mark.skipif(
    os.environ.get("CI_NIGHTLY", "0") != "1",
    reason="Nightly-only test (set CI_NIGHTLY=1 to run)"
)


class TestP4NightlyE2E:
    """Nightly E2E tests for P4."""
    
    @nightly
    @pytest.mark.asyncio
    async def test_e2e_with_official_index(self, tmp_path):
        """Full E2E with official index."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from tests.fixtures.legal_corpus import create_test_index
        
        # Build index
        create_test_index(tmp_path)
        
        # Run pipeline
        output = await run_legal_pipeline(
            query="Quelles sont les conditions de validité d'un contrat ?",
            correlation_id="nightly_e2e_p4",
        )
        
        assert output is not None
        assert output.audit_bundle_id is not None
    
    @nightly
    def test_validate_official_sources_script(self):
        """Validation script should pass on corpus."""
        import subprocess
        
        result = subprocess.run(
            ["python", "scripts/validate_legal_sources.py", "--corpus"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Validation failed: {result.stderr}"


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
