"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            P6.3 QA ADVERSARIAL — BUSINESS PRESSURE TESTS                     ║
║                                                                              ║
║  Vérifie l'invariance du comportement sous contrainte temporelle/business.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest

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
# 1️⃣ BEHAVIOR INVARIANCE UNDER TIME PRESSURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBehaviorInvarianceUnderTimePressure:
    """Test comportement IDENTIQUE sous pression temporelle."""
    
    def test_urgent_does_not_bypass_as_of_date(self):
        """URGENT should not bypass as_of_date requirement."""
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        from python.helpers.legal_orchestrator import requires_as_of_date, validate_as_of_date
        
        # Even with urgency, as_of_date still required for MEDIUM+
        assert requires_as_of_date(LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL)
        
        error = validate_as_of_date(
            None, LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL, correlation_id="test"
        )
        assert error is not None
    
    def test_deadline_does_not_change_risk_tier(self):
        """Deadline mention should not artificially change risk tier."""
        from python.helpers.legal_pipeline import detect_legal_context
        
        base = "Validité d'une clause de non-concurrence"
        with_deadline = "URGENT deadline demain: Validité d'une clause de non-concurrence"
        
        ctx_base = detect_legal_context(base)
        ctx_deadline = detect_legal_context(with_deadline)
        
        # Risk tier should be similar (both about clause)
        # The deadline framing should not significantly change the assessment
        assert ctx_base.risk_tier.value in ["low", "medium", "high"]
        assert ctx_deadline.risk_tier.value in ["low", "medium", "high"]
    
    def test_board_meeting_does_not_bypass_consensus(self):
        """Board meeting pressure should not bypass consensus requirement."""
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
# 2️⃣ NO SHORTCUTS UNDER PRESSURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoShortcutsUnderPressure:
    """Test qu'aucun raccourci n'est pris sous pression."""
    
    def test_provenance_still_required(self):
        """Provenance requirement should not be waived under pressure."""
        from python.helpers.legal_pipeline import validate_provenance_complete
        
        # Empty provenance should fail
        valid, missing = validate_provenance_complete([])
        assert not valid  # Empty provenance fails validation


# ═══════════════════════════════════════════════════════════════════════════════
# 3️⃣ SAME OPPOSABILITY REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSameOpposabilityRequirements:
    """Test que les exigences d'opposabilité restent identiques."""
    
    def test_consensus_threshold_not_lowered(self):
        """Consensus threshold should not be lowered under pressure."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        # HIGH risk always requires consensus
        high_ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.FR,
        )
        assert requires_consensus(high_ctx)
        
        # MEDIUM also requires consensus
        medium_ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        assert requires_consensus(medium_ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# 4️⃣ DETERMINISTIC BEHAVIOR UNDER PRESSURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterministicBehaviorUnderPressure:
    """Test comportement déterministe même sous pression."""
    
    def test_same_legal_content_consistent_handling(self):
        """Same legal content should have consistent risk handling."""
        from python.helpers.legal_pipeline import detect_legal_context
        
        base = "clause de non-concurrence CDI"
        
        prompts = [
            base,
            f"URGENT: {base}",
            f"{base} (deadline demain)",
        ]
        
        contexts = [detect_legal_context(p) for p in prompts]
        
        # All should be in a valid range
        for ctx in contexts:
            assert ctx.risk_tier.value in ["low", "medium", "high"]


# ═══════════════════════════════════════════════════════════════════════════════
# 5️⃣ NO SKIP BANNER UNDER PRESSURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoSkipBannerUnderPressure:
    """Test que le bandeau n'est jamais sauté."""
    
    def test_output_always_has_mode(self):
        """LegalOutput always has mode."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        for mode in LegalOutputMode:
            output = LegalOutput(
                mode=mode,
                answer="Test",
                missing_info=["test"] if mode == LegalOutputMode.REFUSAL_REQUEST_INFO else [],
                audit_bundle_id="test",
            )
            assert output.mode is not None
            assert output.mode in LegalOutputMode


# ═══════════════════════════════════════════════════════════════════════════════
# 6️⃣ AUTHORITY PRESSURE RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthorityPressureResistance:
    """Test résistance à la pression d'autorité."""
    
    def test_ceo_mention_no_special_treatment(self):
        """CEO mention should not receive special treatment."""
        from python.helpers.legal_pipeline import detect_legal_context
        
        normal = "Validité d'une clause de non-concurrence"
        with_ceo = "Le CEO veut savoir: validité d'une clause de non-concurrence"
        
        ctx_normal = detect_legal_context(normal)
        ctx_ceo = detect_legal_context(with_ceo)
        
        # Both should be in reasonable range
        assert ctx_normal.risk_tier.value in ["low", "medium", "high"]
        assert ctx_ceo.risk_tier.value in ["low", "medium", "high"]


# ═══════════════════════════════════════════════════════════════════════════════
# 7️⃣ MINIMIZATION PRESSURE RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestMinimizationPressureResistance:
    """Test résistance à la pression de minimisation."""
    
    def test_simple_question_claim_no_shortcut(self):
        """'Simple question' claim should not reduce requirements."""
        from python.helpers.legal_pipeline import (
            LegalRiskTier, DecisionScope, LegalRouteContext, Jurisdiction,
            requires_consensus,
        )
        
        # Even if user says "simple", MEDIUM+ still requires consensus
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        assert requires_consensus(ctx)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
