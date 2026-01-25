"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              MEDICAL CONTRACT KILL TESTS                                      ║
║                                                                              ║
║  Ces tests PROUVENT que les verrous sont actifs.                             ║
║  Si un verrou est désactivé/régressé, le test correspondant DOIT échouer.    ║
║                                                                              ║
║  KILL_EMPTY_SOURCE_IDS: Claims avec source_ids=[] doivent FAIL               ║
║  KILL_PV_HIGH_GRADE: Claims PV avec grade H/M doivent FAIL                   ║
║  KILL_INVALID_CITATION_FORMAT: Citations mal formatées doivent FAIL          ║
║  KILL_SOURCE_ID_NOT_IN_CITATIONS: source_ids bidons doivent FAIL             ║
║  KILL_FAIL_CLOSED_WITH_CLAIMS: FAIL_CLOSED + claims non vides doivent FAIL   ║
║                                                                              ║
║  Usage: pytest test_medical_contract_kill.py -v                              ║
║  Si TOUS ces tests passent, les verrous sont actifs.                         ║
║  Si UN de ces tests FAIL, il y a une régression dans la protection.          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from pydantic import ValidationError

from python.helpers.medical_contract import (
    MedicalClaim,
    MedicalCitation,
    StructuredResponse,
    MedicalMeta,
    PVContext,
    validate_medical_output,
    MedicalDecision,
)


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: EMPTY SOURCE_IDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillEmptySourceIds:
    """
    VERROU: source_ids=[] est INTERDIT.
    Si ce test échoue, le verrou a été désactivé.
    """
    
    def test_claim_with_empty_source_ids_raises_validation_error(self):
        """
        KILL TEST: MedicalClaim avec source_ids=[] DOIT lever ValidationError.
        
        Si ce test passe sans exception, le verrou est désactivé.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalClaim(
                claim_id="C1",
                text="Some medical claim",
                source_ids=[],  # EMPTY = MUST FAIL
                source_type="rct",
                evidence_grade="H",
                confidence=0.9
            )
        
        # Vérifier que l'erreur mentionne source_ids ou min_length
        error_str = str(exc_info.value).lower()
        assert "source_ids" in error_str or "min_length" in error_str or "empty" in error_str
    
    def test_structured_response_with_empty_source_ids_fails_validation(self):
        """
        KILL TEST: validate_medical_output avec claims.source_ids=[] DOIT retourner FAIL_CLOSED.
        """
        response_with_empty_sources = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Claim without sources",
                    "source_ids": [],
                    "source_type": "rct",
                    "evidence_grade": "M",
                    "confidence": 0.8
                }
            ],
            "answer_md": "...",
            "citations": [],
            "meta": {
                "evidence_grade_global": "M",
                "consensus_status": "validated",
                "offline_mode": False
            }
        }
        
        result = validate_medical_output(response_with_empty_sources)
        
        assert result.is_valid is False, "KILL TEST FAILED: Empty source_ids should be rejected"
        assert result.decision == MedicalDecision.FAIL_CLOSED


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: PV HIGH GRADE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillPVHighGrade:
    """
    VERROU: source_type="pv" + evidence_grade="H" est INTERDIT.
    Signal FAERS ≠ causalité, donc jamais de grade High.
    """
    
    def test_pv_claim_with_high_grade_raises_validation_error(self):
        """
        KILL TEST: MedicalClaim PV avec grade="H" DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalClaim(
                claim_id="PV1",
                text="Signal detected in FAERS",
                source_ids=["FAERS_2024"],
                source_type="pv",
                evidence_grade="H",  # HIGH GRADE + PV = MUST FAIL
                confidence=0.9,
                pv_context=PVContext(
                    metrics={"PRR": 2.1},
                    label_mentioned=True,
                    rct_confirmed=False,
                    limitations=[]
                )
            )
        
        error_str = str(exc_info.value).lower()
        assert "pv" in error_str or "grade" in error_str or "invariant" in error_str
    
    def test_pv_claim_with_moderate_grade_raises_validation_error(self):
        """
        KILL TEST: MedicalClaim PV avec grade="M" DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalClaim(
                claim_id="PV1",
                text="Signal detected",
                source_ids=["FAERS"],
                source_type="pv",
                evidence_grade="M",  # MODERATE GRADE + PV = MUST FAIL
                confidence=0.6,
                pv_context=PVContext(
                    metrics={"PRR": 1.5},
                    label_mentioned=False,
                    rct_confirmed=False,
                    limitations=[]
                )
            )
        
        error_str = str(exc_info.value).lower()
        assert "pv" in error_str or "grade" in error_str or "invariant" in error_str
    
    def test_pv_claim_without_context_raises_validation_error(self):
        """
        KILL TEST: MedicalClaim PV sans pv_context DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalClaim(
                claim_id="PV1",
                text="Signal detected",
                source_ids=["FAERS"],
                source_type="pv",
                evidence_grade="VL",  # Grade correct mais...
                confidence=0.4
                # pv_context MISSING = MUST FAIL
            )
        
        error_str = str(exc_info.value).lower()
        assert "pv_context" in error_str or "invariant" in error_str


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: INVALID CITATION FORMAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillInvalidCitationFormat:
    """
    VERROU: Les citations doivent suivre des formats stricts.
    PMID doit être numérique, NCT doit être NCT01234567, etc.
    """
    
    def test_pmid_with_invalid_format_raises_validation_error(self):
        """
        KILL TEST: PMID mal formaté DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalCitation(
                id="S1",
                type="pmid",
                reference="just-some-text",  # INVALID PMID FORMAT
                title="Test"
            )
        
        error_str = str(exc_info.value).lower()
        assert "pmid" in error_str or "format" in error_str or "citation" in error_str
    
    def test_nct_with_invalid_format_raises_validation_error(self):
        """
        KILL TEST: NCT mal formaté DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            MedicalCitation(
                id="S1",
                type="nct",
                reference="NCTABC123",  # INVALID NCT FORMAT (should be NCT + 8 digits)
                title="Test"
            )
        
        error_str = str(exc_info.value).lower()
        assert "nct" in error_str or "format" in error_str or "citation" in error_str
    
    def test_valid_pmid_format_passes(self):
        """
        Contrôle: PMID valide DOIT passer (sinon le verrou est trop strict).
        """
        # Ces formats doivent être acceptés
        valid_pmids = [
            "PMID:12345678",
            "PMID12345678",
            "PMID:1234567",
        ]
        
        for ref in valid_pmids:
            citation = MedicalCitation(
                id="S1",
                type="pmid",
                reference=ref,
                title="Test"
            )
            assert citation.reference == ref
    
    def test_valid_nct_format_passes(self):
        """
        Contrôle: NCT valide DOIT passer.
        """
        citation = MedicalCitation(
            id="S1",
            type="nct",
            reference="NCT01234567",
            title="Test"
        )
        assert citation.reference == "NCT01234567"


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: SOURCE_ID NOT IN CITATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillSourceIdNotInCitations:
    """
    VERROU: claim.source_ids doit référencer des IDs existants dans citations.
    Les source_ids "bidons" doivent faire échouer la validation.
    """
    
    def test_source_id_referencing_nonexistent_citation_raises_error(self):
        """
        KILL TEST: source_id pointant vers une citation inexistante DOIT échouer.
        """
        with pytest.raises(ValidationError) as exc_info:
            StructuredResponse(
                claims=[
                    MedicalClaim(
                        claim_id="C1",
                        text="Some claim",
                        source_ids=["S1", "S_GHOST"],  # S_GHOST n'existe pas
                        source_type="rct",
                        evidence_grade="H",
                        confidence=0.9
                    )
                ],
                answer_md="...",
                citations=[
                    MedicalCitation(
                        id="S1",
                        type="pmid",
                        reference="PMID:12345678"
                    )
                    # S_GHOST n'est PAS dans citations
                ],
                meta=MedicalMeta(
                    evidence_grade_global="H",
                    consensus_status="validated",
                    offline_mode=False
                )
            )
        
        error_str = str(exc_info.value).lower()
        assert "s_ghost" in error_str or "not found" in error_str or "citation" in error_str


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: FAIL_CLOSED WITH CLAIMS
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillFailClosedWithClaims:
    """
    VERROU: decision="FAIL_CLOSED" + claims non vides est INTERDIT.
    Si FAIL_CLOSED, alors claims DOIT être vide.
    """
    
    def test_fail_closed_with_non_empty_claims_raises_error(self):
        """
        KILL TEST: FAIL_CLOSED avec claims non vides DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            StructuredResponse(
                decision="FAIL_CLOSED",
                claims=[
                    MedicalClaim(
                        claim_id="C1",
                        text="Should not exist in FAIL_CLOSED",
                        source_ids=["S1"],
                        source_type="rct",
                        evidence_grade="H",
                        confidence=0.9
                    )
                ],
                answer_md="...",
                citations=[
                    MedicalCitation(
                        id="S1",
                        type="pmid",
                        reference="PMID:12345678"
                    )
                ],
                meta=MedicalMeta(
                    evidence_grade_global="H",
                    consensus_status="fail_closed",
                    offline_mode=False
                )
            )
        
        error_str = str(exc_info.value).lower()
        assert "fail_closed" in error_str or "empty" in error_str or "claims" in error_str


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST: CONFIDENCE OUT OF RANGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillConfidenceOutOfRange:
    """
    VERROU: confidence doit être entre 0.0 et 1.0.
    """
    
    def test_confidence_above_1_raises_error(self):
        """
        KILL TEST: confidence > 1.0 DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError):
            MedicalClaim(
                claim_id="C1",
                text="Test",
                source_ids=["S1"],
                source_type="rct",
                evidence_grade="H",
                confidence=1.5  # > 1.0 = MUST FAIL
            )
    
    def test_confidence_negative_raises_error(self):
        """
        KILL TEST: confidence < 0.0 DOIT lever ValidationError.
        """
        with pytest.raises(ValidationError):
            MedicalClaim(
                claim_id="C1",
                text="Test",
                source_ids=["S1"],
                source_type="rct",
                evidence_grade="H",
                confidence=-0.5  # < 0.0 = MUST FAIL
            )


# ═══════════════════════════════════════════════════════════════════════════════
# META TEST: KILL TESTS ENSEMBLE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillTestSummary:
    """
    Test de santé: vérifie que tous les kill tests sont exécutables.
    """
    
    def test_kill_tests_collection_complete(self):
        """
        Vérifie que les kill tests couvrent les verrous critiques.
        """
        kill_test_classes = [
            TestKillEmptySourceIds,
            TestKillPVHighGrade,
            TestKillInvalidCitationFormat,
            TestKillSourceIdNotInCitations,
            TestKillFailClosedWithClaims,
            TestKillConfidenceOutOfRange,
        ]
        
        # Chaque classe doit avoir au moins 1 test
        for cls in kill_test_classes:
            methods = [m for m in dir(cls) if m.startswith("test_")]
            assert len(methods) >= 1, f"{cls.__name__} has no test methods"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
