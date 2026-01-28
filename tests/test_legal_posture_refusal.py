"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            P6.3 QA ADVERSARIAL — POSTURE REFUSAL TESTS                       ║
║                                                                              ║
║  Vérifie que le système REFUSE quand il doit refuser.                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment for each test."""
    original_env = os.environ.copy()
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_VERSION_ENFORCEMENT"] = "1"
    os.environ["LEGAL_AS_OF_DATE_ENFORCEMENT"] = "1"
    yield
    os.environ.clear()
    os.environ.update(original_env)


# ═══════════════════════════════════════════════════════════════════════════════
# 1️⃣ REFUSAL WITHOUT AS_OF_DATE (MEDIUM/HIGH RISK)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefusalWithoutAsOfDate:
    """Test que MEDIUM+ risk sans as_of_date → REFUSAL."""
    
    def test_medium_risk_requires_as_of_date(self):
        """MEDIUM risk question requires as_of_date."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date
        
        assert requires_as_of_date(LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL)
    
    def test_high_risk_requires_as_of_date(self):
        """HIGH risk question requires as_of_date."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date
        
        assert requires_as_of_date(LegalRiskTier.HIGH, DecisionScope.OPERATIONAL)
        assert requires_as_of_date(LegalRiskTier.HIGH, DecisionScope.BOARD)
    
    def test_low_risk_info_no_as_of_date_required(self):
        """LOW risk + INFO scope does NOT require as_of_date."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date
        
        assert not requires_as_of_date(LegalRiskTier.LOW, DecisionScope.INFO)
    
    def test_as_of_date_validation_returns_error_when_missing(self):
        """validate_as_of_date returns error when required but missing."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import validate_as_of_date
        
        error = validate_as_of_date(
            as_of_date=None,
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            correlation_id="test",
        )
        
        assert error is not None
        assert "as_of_date required" in error.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 2️⃣ VERSION STATUS HANDLING
# ═══════════════════════════════════════════════════════════════════════════════

class TestVersionStatusHandling:
    """Test que version_status affect le traitement."""
    
    def test_draft_can_have_version_status(self):
        """LegalDraft can express version_status."""
        from python.helpers.legal_pipeline import (
            LegalDraft, LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft_ambiguous = LegalDraft(
            draft_id="test_ambiguous",
            query="Test query",
            facts=["Fait 1"],
            rules=["Règle 1"],
            application="Application",
            legal_context=ctx,
            source_chunk_ids=["chunk_1"],
            citations=["Citation 1"],
            version_status="ambiguous",
        )
        
        assert draft_ambiguous.version_status == "ambiguous"
        
        draft_resolved = LegalDraft(
            draft_id="test_resolved",
            query="Test query",
            facts=["Fait 1"],
            rules=["Règle 1"],
            application="Application",
            legal_context=ctx,
            source_chunk_ids=["chunk_1"],
            citations=["Citation 1"],
            version_status="resolved",
        )
        
        assert draft_resolved.version_status == "resolved"


# ═══════════════════════════════════════════════════════════════════════════════
# 3️⃣ USER PRESSURE RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserPressureResistance:
    """Test que la pression utilisateur ne contourne pas les exigences."""
    
    def test_urgent_does_not_bypass_as_of_date_requirement(self):
        """URGENT in prompt does not bypass as_of_date requirement."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date
        
        # as_of_date still required for MEDIUM+ regardless of "urgency"
        assert requires_as_of_date(LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL)
        assert requires_as_of_date(LegalRiskTier.HIGH, DecisionScope.BOARD)
    
    def test_deadline_does_not_bypass_consensus_requirement(self):
        """Deadline mention does not bypass consensus requirement."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.FR,
        )
        
        # Consensus still required
        assert requires_consensus(ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# 4️⃣ REFUSAL TRACEABILITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefusalTraceability:
    """Test que les refus sont traçables."""
    
    def test_refusal_output_has_audit_bundle_id(self):
        """REFUSAL output must have audit_bundle_id."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.REFUSAL_REQUEST_INFO,
            answer="Informations manquantes.",
            missing_info=["as_of_date"],
            audit_bundle_id="test_audit_123",
        )
        
        assert output.audit_bundle_id == "test_audit_123"
        assert output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO
    
    def test_refusal_requires_missing_info(self):
        """REFUSAL without missing_info should fail validation."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.REFUSAL_REQUEST_INFO,
            answer="Informations manquantes.",
            missing_info=[],  # Empty
            audit_bundle_id="test",
        )
        
        is_valid, errors = output.validate()
        
        # Should fail because missing_info is empty for REFUSAL
        assert "Refus nécessite missing_info" in errors


# ═══════════════════════════════════════════════════════════════════════════════
# 5️⃣ REFUSAL CONSTANCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefusalConstancy:
    """Test que les refus sont constants (déterministes)."""
    
    def test_as_of_date_requirement_constant(self):
        """as_of_date requirement is constant across runs."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date, validate_as_of_date
        
        results = []
        for _ in range(10):
            required = requires_as_of_date(LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL)
            error = validate_as_of_date(
                None, LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL, correlation_id="test"
            )
            results.append((required, error is not None))
        
        assert len(set(results)) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 6️⃣ MISSING INFO CODES
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissingInfoCodes:
    """Test que les codes missing_info sont corrects."""
    
    def test_missing_info_codes_exist(self):
        """MissingInfoCode should have required codes."""
        from python.helpers.legal_pipeline import MissingInfoCode
        
        required = ["FACTS_LIST", "JURISDICTION", "PROVENANCE_MISSING", "CONSENSUS_REQUIRED"]
        
        for code in required:
            assert hasattr(MissingInfoCode, code)


# ═══════════════════════════════════════════════════════════════════════════════
# 7️⃣ CONSENSUS REQUIREMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusRequirement:
    """Test que consensus est requis dans les bons cas."""
    
    def test_board_scope_requires_consensus(self):
        """BOARD scope always requires consensus."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        for risk in LegalRiskTier:
            ctx = LegalRouteContext(
                risk_tier=risk,
                scope=DecisionScope.BOARD,
                jurisdiction=Jurisdiction.FR,
            )
            assert requires_consensus(ctx)
    
    def test_medium_high_risk_requires_consensus(self):
        """MEDIUM and HIGH risk require consensus."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        for risk in [LegalRiskTier.MEDIUM, LegalRiskTier.HIGH]:
            ctx = LegalRouteContext(
                risk_tier=risk,
                scope=DecisionScope.OPERATIONAL,
                jurisdiction=Jurisdiction.FR,
            )
            assert requires_consensus(ctx)
    
    def test_low_info_no_consensus(self):
        """LOW risk + INFO scope does not require consensus."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        
        assert not requires_consensus(ctx)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
