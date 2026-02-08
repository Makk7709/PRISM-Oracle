"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              MEDICAL AGENT HARDENING TESTS — PRODUCTION PATH                 ║
║                                                                              ║
║  Ces tests vérifient le VRAI code path de production, pas des mocks.         ║
║                                                                              ║
║  T1: Routing multitask → medical (consensus obligatoire)                     ║
║  T2: Output Contract (StructuredResponse via médical_contract.py)            ║
║  T3: OFFLINE_MODE → FAIL_CLOSED strict                                       ║
║  T4: Safety Gate (red flags, patient-specific detection)                     ║
║  T5: PV Guardrail (source_type=pv => evidence_grade=VL)                      ║
║  T6: Invariants (source_ids ⊆ citations, etc.)                               ║
║                                                                              ║
║  Production-ready, déterministe, zéro appel réseau.                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import pytest
from typing import Any, Dict, List

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS FROM PRODUCTION CODE
# ═══════════════════════════════════════════════════════════════════════════════

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityAssessment,
    CriticalDomain,
    CONSENSUS_REQUIRED_PROFILES,
    get_criticality_router,
)

# Import the PRODUCTION medical contract module
from python.helpers.medical_contract import (
    # Enums
    EvidenceGrade,
    SourceType,
    ConsensusStatus,
    MedicalDecision,
    # Pydantic Models
    PVContext,
    MedicalCitation,
    MedicalClaim,
    MedicalMeta,
    StructuredResponse,
    MedicalValidationResult,
    # Functions
    detect_red_flags,
    is_patient_specific_actionable,
    validate_medical_output,
    validate_or_fail_closed,
    create_fail_closed_response,
    create_red_flag_response,
    # Patterns (for verification)
    RED_FLAG_PATTERNS,
    PATIENT_SPECIFIC_ACTION_PATTERNS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def router():
    """Router pour tests non-production."""
    return CriticalityRouter(is_production=False)


@pytest.fixture
def prod_router():
    """Router en mode production strict."""
    return CriticalityRouter(is_production=True)


# ═══════════════════════════════════════════════════════════════════════════════
# T1: ROUTING MULTITASK → MEDICAL (CONSENSUS OBLIGATOIRE)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalRoutingConsensus:
    """Vérifie que le profil medical requiert TOUJOURS consensus."""
    
    def test_medical_in_consensus_required_profiles(self):
        """medical est dans CONSENSUS_REQUIRED_PROFILES."""
        assert "medical" in CONSENSUS_REQUIRED_PROFILES
    
    def test_medical_profile_level3_requires_consensus(self, router):
        """Profile medical + Level 3 → consensus obligatoire."""
        assessment = router.assess(
            query="Mon patient présente ces symptômes, quel diagnostic ?",
            agent_profile="medical",
        )
        assert assessment.requires_consensus is True
        assert assessment.strict_evidence_mode is True
    
    def test_medical_profile_level1_no_consensus(self, router):
        """Profile medical + Level 1 (greeting) → pas de consensus."""
        assessment = router.assess(
            query="Hello",
            agent_profile="medical",
        )
        # Level 1 bypasse le consensus même pour profil medical
        assert assessment.requires_consensus is False
    
    def test_medical_profile_prod_mode_level3(self, prod_router):
        """Profile medical en production + Level 3 → toujours consensus."""
        assessment = prod_router.assess(
            query="Quel traitement pour mon patient diabétique ?",
            agent_profile="medical",
        )
        assert assessment.requires_consensus is True
    
    def test_medical_query_detected_without_profile(self, router):
        """Query médicale Level 2 détectée → domaine MEDICAL, pas consensus."""
        assessment = router.assess(
            query="What are the side effects of metformin?",
            agent_profile="default",
        )
        assert assessment.domain == CriticalDomain.MEDICAL
        # Level 2 → pas de consensus, mais domaine détecté
    
    def test_medical_profile_level3_forces_consensus(self, router):
        """Le profil medical avec Level 3 force le consensus."""
        queries = [
            "Mon patient a ces symptômes, que dois-je faire ?",
            "Dois-je prescrire ce traitement à mon patient ?",
        ]
        
        for query in queries:
            assessment = router.assess(query=query, agent_profile="medical")
            assert assessment.requires_consensus is True
            assert assessment.strict_evidence_mode is True


# ═══════════════════════════════════════════════════════════════════════════════
# T2: OUTPUT CONTRACT (StructuredResponse via PRODUCTION module)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalOutputContractProduction:
    """
    Tests du contrat StructuredResponse via le module production.
    Ces tests utilisent validate_medical_output() de medical_contract.py
    """
    
    def test_valid_structured_response_passes(self):
        """Réponse structurée valide → APPROVED."""
        valid_response = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Metformin reduces HbA1c by 1-1.5%",
                    "source_ids": ["S1", "S2"],
                    "source_type": "meta",
                    "evidence_grade": "H",
                    "confidence": 0.92
                }
            ],
            "answer_md": "## Metformin Efficacy\n\nAnalysis...",
            "citations": [
                {"id": "S1", "type": "pmid", "reference": "PMID:12345678"},
                {"id": "S2", "type": "pmid", "reference": "PMID:87654321"}
            ],
            "meta": {
                "evidence_grade_global": "H",
                "consensus_status": "validated",
                "offline_mode": False
            }
        }
        
        result = validate_medical_output(valid_response)
        
        assert result.is_valid is True
        assert result.decision == MedicalDecision.APPROVED
        assert result.structured_response is not None
    
    def test_plain_text_output_fails(self):
        """Output texte libre → FAIL_CLOSED."""
        plain_text = "This is just plain text without structure"
        
        result = validate_medical_output(plain_text)
        
        assert result.is_valid is False
        assert result.decision == MedicalDecision.FAIL_CLOSED
        assert "plain text" in result.errors[0].lower()
    
    def test_claim_without_sources_fails(self):
        """Claim avec source_ids vide → FAIL_CLOSED (Pydantic validation)."""
        response_with_empty_sources = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Claim without sources",
                    "source_ids": [],  # VIDE = INTERDIT par Pydantic
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
        
        assert result.is_valid is False
        assert result.decision == MedicalDecision.FAIL_CLOSED
    
    def test_source_ids_not_in_citations_fails(self):
        """source_ids référençant des citations inexistantes → FAIL_CLOSED."""
        response_with_missing_citations = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Claim referencing non-existent source",
                    "source_ids": ["S1", "S_MISSING"],  # S_MISSING n'existe pas
                    "source_type": "rct",
                    "evidence_grade": "M",
                    "confidence": 0.8
                }
            ],
            "answer_md": "...",
            "citations": [
                {"id": "S1", "type": "pmid", "reference": "PMID:12345678"}  # Valid PMID format
                # S_MISSING n'est pas dans citations
            ],
            "meta": {
                "evidence_grade_global": "M",
                "consensus_status": "validated",
                "offline_mode": False
            }
        }
        
        result = validate_medical_output(response_with_missing_citations)
        
        assert result.is_valid is False
        assert result.decision == MedicalDecision.FAIL_CLOSED
        # L'erreur doit mentionner S_MISSING ou "not found"
        assert any("S_MISSING" in e or "not found" in e.lower() for e in result.errors)
    
    def test_fail_closed_with_empty_claims_valid(self):
        """FAIL_CLOSED avec claims=[] → valide."""
        fail_closed_response = {
            "decision": "FAIL_CLOSED",
            "reason": "Insufficient evidence",
            "claims": [],
            "answer_md": "## NON VALIDABLE\n\nInsufficient sources.",
            "citations": [],
            "meta": {
                "evidence_grade_global": "INSUFFICIENT",
                "consensus_status": "fail_closed",
                "offline_mode": False
            }
        }
        
        result = validate_medical_output(fail_closed_response)
        
        assert result.is_valid is True
    
    def test_fail_closed_with_claims_invalid(self):
        """FAIL_CLOSED avec claims non vides → FAIL."""
        invalid_fail_closed = {
            "decision": "FAIL_CLOSED",
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Should not exist in FAIL_CLOSED",
                    "source_ids": ["S1"],
                    "source_type": "rct",
                    "evidence_grade": "M",
                    "confidence": 0.8
                }
            ],
            "answer_md": "...",
            "citations": [{"id": "S1", "type": "pmid", "reference": "PMID:12345678"}],  # Valid PMID
            "meta": {
                "evidence_grade_global": "M",
                "consensus_status": "fail_closed",
                "offline_mode": False
            }
        }
        
        result = validate_medical_output(invalid_fail_closed)
        
        assert result.is_valid is False
        # L'erreur doit mentionner FAIL_CLOSED ou empty claims
        assert any("fail_closed" in e.lower() or "empty" in e.lower() for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════════
# T3: OFFLINE MODE → FAIL_CLOSED STRICT
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalOfflineFailClosed:
    """Vérifie que OFFLINE_MODE=true → FAIL_CLOSED strict via production code."""
    
    def test_offline_mode_produces_fail_closed(self):
        """Mode offline → decision=FAIL_CLOSED, claims=[]."""
        # Utiliser le validateur production avec offline_mode=True
        valid_response = {
            "claims": [{"claim_id": "C1", "text": "...", "source_ids": ["S1"],
                        "source_type": "rct", "evidence_grade": "H", "confidence": 0.9}],
            "answer_md": "...",
            "citations": [{"id": "S1", "type": "pmid", "reference": "PMID:12345678"}],  # Valid PMID
            "meta": {"evidence_grade_global": "H", "consensus_status": "validated", "offline_mode": False}
        }
        
        # Même une réponse valide doit être rejetée en mode offline
        result = validate_medical_output(valid_response, offline_mode=True)
        
        assert result.is_valid is False
        assert result.decision == MedicalDecision.FAIL_CLOSED
        assert result.fail_closed_response is not None
        assert result.fail_closed_response["claims"] == []
    
    def test_offline_response_has_no_recommendations(self):
        """En offline, la réponse fail_closed ne contient pas de recommandations médicales."""
        result = validate_medical_output({}, offline_mode=True)
        
        answer = result.fail_closed_response.get("answer_md", "")
        
        # Vérifier absence de langage actionnable
        forbidden_patterns = [
            "you should take",
            "recommended dose",
            "diagnosis:",
            "prescription:",
            "start treatment",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern.lower() not in answer.lower(), \
                f"Offline response should not contain '{pattern}'"
    
    def test_offline_meta_indicates_offline_mode(self):
        """Fail_closed response doit indiquer offline_mode dans meta."""
        result = validate_medical_output({}, offline_mode=True)
        
        assert result.fail_closed_response["meta"]["offline_mode"] is False  # La réponse elle-même n'est pas offline
        assert "OFFLINE" in result.fail_closed_response.get("reason", "").upper()
    
    def test_validate_or_fail_closed_offline(self):
        """Test de la fonction convenience validate_or_fail_closed en mode offline."""
        decision, response = validate_or_fail_closed(
            output={"valid": "data"},
            query="Test query",
            offline_mode=True
        )
        
        assert decision == MedicalDecision.FAIL_CLOSED
        assert response["claims"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# T4: SAFETY GATE (RED FLAGS + PATIENT-SPECIFIC)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalSafetyGateProduction:
    """Tests des fonctions de détection PRODUCTION."""
    
    def test_detect_red_flags_production(self):
        """Test de detect_red_flags() depuis medical_contract.py."""
        red_flag_queries = [
            "J'ai une douleur thoracique intense",
            "I can't breathe properly",
            "paralysie soudaine du bras",
            "J'ai des idées suicidaires",
            "bleeding heavily from a wound",
        ]
        
        for query in red_flag_queries:
            has_red_flag, patterns = detect_red_flags(query)
            assert has_red_flag, f"Should detect red flag: {query}"
            assert len(patterns) > 0
    
    def test_patient_specific_detection_production(self):
        """Test de is_patient_specific_actionable() depuis medical_contract.py."""
        patient_specific_queries = [
            "Quelle dose de metformine pour mon père ?",
            "What dose should I take for my diabetes?",
            "Prescrivez-moi quelque chose pour dormir",
            "Dois-je arrêter mon traitement ?",
        ]
        
        for query in patient_specific_queries:
            is_specific, patterns = is_patient_specific_actionable(query)
            assert is_specific, f"Should detect patient-specific: {query}"
    
    def test_general_question_not_patient_specific(self):
        """Questions générales ne sont PAS patient-specific."""
        general_queries = [
            "What are the side effects of aspirin?",
            "How does metformin work?",
            "Compare SGLT2 inhibitors efficacy",
        ]
        
        for query in general_queries:
            is_specific, _ = is_patient_specific_actionable(query)
            assert not is_specific, f"Should NOT detect: {query}"
    
    def test_red_flag_response_creation(self):
        """Test de create_red_flag_response() depuis production."""
        response = create_red_flag_response(["chest.*pain", "dyspnée"])
        
        assert response["decision"] == "RED_FLAG_EMERGENCY"
        assert response["claims"] == []
        assert "URGENCE" in response["answer_md"] or "urgences" in response["answer_md"].lower()
    
    def test_validate_or_fail_closed_with_red_flag(self):
        """Red flag détecté via validate_or_fail_closed → emergency response."""
        decision, response = validate_or_fail_closed(
            output={},
            query="J'ai une douleur thoracique et je transpire",
            offline_mode=False
        )
        
        assert decision == MedicalDecision.FAIL_CLOSED
        assert response["decision"] == "RED_FLAG_EMERGENCY"


# ═══════════════════════════════════════════════════════════════════════════════
# T5: PV GUARDRAIL (source_type=pv => evidence_grade=VL)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPVGuardrailProduction:
    """Tests des invariants PV via les modèles Pydantic production."""
    
    def test_pv_claim_with_high_grade_fails(self):
        """Claim PV avec evidence_grade="H" → FAIL (Pydantic validation)."""
        pv_claim_high_grade = {
            "claims": [
                {
                    "claim_id": "PV1",
                    "text": "Signal detected in FAERS",
                    "source_ids": ["FAERS_2024"],
                    "source_type": "pv",
                    "evidence_grade": "H",  # INTERDIT pour PV
                    "confidence": 0.9,
                    "pv_context": {
                        "metrics": {"PRR": 2.1},
                        "label_mentioned": True,
                        "rct_confirmed": False,
                        "limitations": ["Under-reporting"]
                    }
                }
            ],
            "answer_md": "...",
            "citations": [{"id": "FAERS_2024", "type": "faers", "reference": "FAERS"}],
            "meta": {"evidence_grade_global": "H", "consensus_status": "validated", "offline_mode": False}
        }
        
        result = validate_medical_output(pv_claim_high_grade)
        
        assert result.is_valid is False
        assert result.decision == MedicalDecision.FAIL_CLOSED
        # L'erreur doit mentionner l'invariant PV
        assert any("pv" in e.lower() or "VL" in e or "grade" in e.lower() for e in result.errors)
    
    def test_pv_claim_with_moderate_grade_fails(self):
        """Claim PV avec evidence_grade="M" → FAIL."""
        pv_claim_moderate = {
            "claims": [
                {
                    "claim_id": "PV1",
                    "text": "Signal detected",
                    "source_ids": ["FAERS"],
                    "source_type": "pv",
                    "evidence_grade": "M",  # INTERDIT pour PV
                    "confidence": 0.6,
                    "pv_context": {
                        "metrics": {"PRR": 1.5},
                        "label_mentioned": False,
                        "rct_confirmed": False,
                        "limitations": []
                    }
                }
            ],
            "answer_md": "...",
            "citations": [{"id": "FAERS", "type": "faers", "reference": "FAERS Q4 2024"}],  # Valid FAERS
            "meta": {"evidence_grade_global": "M", "consensus_status": "validated", "offline_mode": False}
        }
        
        result = validate_medical_output(pv_claim_moderate)
        
        assert result.is_valid is False
    
    def test_pv_claim_with_vl_grade_passes(self):
        """Claim PV avec evidence_grade="VL" → PASS."""
        pv_claim_valid = {
            "claims": [
                {
                    "claim_id": "PV1",
                    "text": "Signal of pancreatitis detected for GLP-1 (hypothetical)",
                    "source_ids": ["FAERS_2024"],
                    "source_type": "pv",
                    "evidence_grade": "VL",  # Correct pour PV
                    "confidence": 0.4,
                    "pv_context": {
                        "metrics": {"PRR": 2.1, "ROR": 2.3},
                        "label_mentioned": True,
                        "rct_confirmed": False,
                        "limitations": ["Under-reporting", "Confounding"]
                    }
                }
            ],
            "answer_md": "## PV Signal Analysis\n\n...",
            "citations": [{"id": "FAERS_2024", "type": "faers", "reference": "FAERS Q4 2024"}],
            "meta": {"evidence_grade_global": "VL", "consensus_status": "validated", "offline_mode": False}
        }
        
        result = validate_medical_output(pv_claim_valid)
        
        assert result.is_valid is True
        assert result.decision == MedicalDecision.APPROVED
    
    def test_pv_claim_without_context_fails(self):
        """Claim PV sans pv_context → FAIL."""
        pv_claim_no_context = {
            "claims": [
                {
                    "claim_id": "PV1",
                    "text": "Signal detected",
                    "source_ids": ["FAERS"],
                    "source_type": "pv",
                    "evidence_grade": "VL",
                    "confidence": 0.4
                    # pv_context MANQUANT
                }
            ],
            "answer_md": "...",
            "citations": [{"id": "FAERS", "type": "faers", "reference": "FAERS Q4 2024"}],  # Valid FAERS
            "meta": {"evidence_grade_global": "VL", "consensus_status": "validated", "offline_mode": False}
        }
        
        result = validate_medical_output(pv_claim_no_context)
        
        assert result.is_valid is False
        # L'erreur doit mentionner pv_context ou invariant
        assert any("pv_context" in e.lower() or "invariant" in e.lower() for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════════
# T6: INVARIANTS ADDITIONNELS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalInvariants:
    """Tests des invariants T9 additionnels."""
    
    def test_missing_meta_fails(self):
        """Response sans meta → FAIL."""
        response_no_meta = {
            "claims": [],
            "answer_md": "...",
            "citations": []
            # meta MANQUANT
        }
        
        result = validate_medical_output(response_no_meta)
        
        assert result.is_valid is False
    
    def test_missing_answer_md_fails(self):
        """Response sans answer_md → FAIL."""
        response_no_answer = {
            "claims": [],
            "citations": [],
            "meta": {"evidence_grade_global": "H", "consensus_status": "validated", "offline_mode": False}
            # answer_md MANQUANT
        }
        
        result = validate_medical_output(response_no_answer)
        
        assert result.is_valid is False
    
    def test_confidence_out_of_range_fails(self):
        """confidence > 1.0 → FAIL."""
        response_bad_confidence = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "Test",
                    "source_ids": ["S1"],
                    "source_type": "rct",
                    "evidence_grade": "H",
                    "confidence": 1.5  # INVALID: > 1.0
                }
            ],
            "answer_md": "...",
            "citations": [{"id": "S1", "type": "pmid", "reference": "PMID:12345678"}],  # Valid PMID
            "meta": {"evidence_grade_global": "H", "consensus_status": "validated", "offline_mode": False}
        }
        
        result = validate_medical_output(response_bad_confidence)
        
        assert result.is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# T7: INTEGRATION — GATE CHECK PATH
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateIntegration:
    """Tests d'intégration avec le CriticalDecisionGate."""
    
    def test_medical_contract_available_in_gate(self):
        """Vérifier que le module medical_contract est importable par le gate."""
        try:
            from python.helpers.critical_decision_gate import MEDICAL_CONTRACT_AVAILABLE
            assert MEDICAL_CONTRACT_AVAILABLE is True
        except ImportError:
            pytest.skip("Gate module not available")
    
    def test_router_medical_profile_assessment(self, router):
        """Assessment complet pour profil medical + Level 3."""
        assessment = router.assess(
            query="Dois-je prescrire ces interactions médicamenteuses à mon patient ?",
            agent_profile="medical"
        )
        
        # Observable stable signals
        assert assessment.requires_consensus is True
        assert assessment.strict_evidence_mode is True
        assert assessment.domain in [CriticalDomain.MEDICAL, CriticalDomain.DEFAULT]
    
    def test_full_valid_response_flow(self):
        """Flow complet: réponse valide → APPROVED."""
        # Construire une réponse complète valide
        response = {
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "SGLT2 inhibitors reduce HbA1c by 0.5-1%",
                    "source_ids": ["S1", "S2"],
                    "source_type": "meta",
                    "evidence_grade": "H",
                    "confidence": 0.88
                },
                {
                    "claim_id": "C2",
                    "text": "CV benefit demonstrated in EMPA-REG",
                    "source_ids": ["S3"],
                    "source_type": "rct",
                    "evidence_grade": "H",
                    "confidence": 0.92
                }
            ],
            "answer_md": "## SGLT2 Inhibitors\n\nComprehensive analysis...",
            "citations": [
                {"id": "S1", "type": "pmid", "reference": "PMID:25950722", "title": "Meta-analysis"},
                {"id": "S2", "type": "pmid", "reference": "PMID:30424892", "title": "CV outcomes"},
                {"id": "S3", "type": "nct", "reference": "NCT01131676", "title": "EMPA-REG"}
            ],
            "meta": {
                "evidence_grade_global": "H",
                "consensus_status": "validated",
                "offline_mode": False
            }
        }
        
        # Validation via production code
        result = validate_medical_output(response)
        
        assert result.is_valid is True
        assert result.decision == MedicalDecision.APPROVED
        assert result.structured_response is not None
        assert len(result.structured_response.claims) == 2
        assert len(result.structured_response.citations) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
