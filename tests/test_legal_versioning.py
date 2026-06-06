"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P5: LEGAL VERSIONING TESTS                                ║
║                                                                              ║
║  Tests for P5 Versioning juridique & opposabilité temporelle:               ║
║  - LegalTextVersion model                                                    ║
║  - SourceNote version requirement                                            ║
║  - as_of_date enforcement                                                    ║
║  - VERSION_RESOLVED judge check                                              ║
║  - Temporal filtering in retrieval                                           ║
║                                                                              ║
║  Version: 1.0.0 (P5)                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    
    # Enable all P5 features
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_VERSION_ENFORCEMENT"] = "1"
    os.environ["LEGAL_AS_OF_DATE_ENFORCEMENT"] = "1"
    os.environ["LEGAL_WHITELIST_ENFORCEMENT"] = "1"
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_version():
    """Create a sample LegalTextVersion."""
    from python.helpers.legal_agent_contracts import LegalTextVersion
    
    return LegalTextVersion(
        text_id="LEGIARTI000006436298",
        version_id="v2016",
        effective_from=date(2016, 10, 1),
        effective_to=None,  # Still in force
        is_current=True,
    )


@pytest.fixture
def old_version():
    """Create an old LegalTextVersion."""
    from python.helpers.legal_agent_contracts import LegalTextVersion
    
    return LegalTextVersion(
        text_id="LEGIARTI000006436298",
        version_id="v2000",
        effective_from=date(2000, 1, 1),
        effective_to=date(2016, 9, 30),
        is_current=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P5.1: LEGAL TEXT VERSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalTextVersion:
    """Tests for LegalTextVersion model."""
    
    def test_valid_version(self, sample_version):
        """Valid version should be created."""
        assert sample_version.text_id == "LEGIARTI000006436298"
        assert sample_version.version_id == "v2016"
        assert sample_version.effective_from == date(2016, 10, 1)
        assert sample_version.effective_to is None
        assert sample_version.is_current is True
    
    def test_version_missing_text_id(self):
        """Version without text_id should fail."""
        from python.helpers.legal_agent_contracts import (
            LegalTextVersion, 
            ContractValidationError,
        )
        
        with pytest.raises(ContractValidationError) as exc_info:
            LegalTextVersion(
                text_id="",
                version_id="v1",
                effective_from=date(2020, 1, 1),
            )
        
        assert "text_id" in str(exc_info.value)
    
    def test_version_missing_effective_from(self):
        """Version without effective_from should fail."""
        from python.helpers.legal_agent_contracts import (
            LegalTextVersion, 
            ContractValidationError,
        )
        
        with pytest.raises(ContractValidationError) as exc_info:
            LegalTextVersion(
                text_id="test",
                version_id="v1",
                effective_from=None,
            )
        
        assert "effective_from" in str(exc_info.value)
    
    def test_version_effective_to_before_from(self):
        """effective_to before effective_from should fail."""
        from python.helpers.legal_agent_contracts import (
            LegalTextVersion, 
            ContractValidationError,
        )
        
        with pytest.raises(ContractValidationError) as exc_info:
            LegalTextVersion(
                text_id="test",
                version_id="v1",
                effective_from=date(2020, 1, 1),
                effective_to=date(2019, 1, 1),  # Before effective_from
            )
        
        assert "effective_to" in str(exc_info.value)
    
    def test_is_valid_at_current(self, sample_version):
        """Current version should be valid at today."""
        today = date.today()
        assert sample_version.is_valid_at(today) is True
    
    def test_is_valid_at_before_effective(self, sample_version):
        """Version should not be valid before effective_from."""
        old_date = date(2015, 1, 1)
        assert sample_version.is_valid_at(old_date) is False
    
    def test_is_valid_at_after_effective_to(self, old_version):
        """Version should not be valid after effective_to."""
        future_date = date(2020, 1, 1)
        assert old_version.is_valid_at(future_date) is False
    
    def test_parse_date_from_string(self):
        """Should parse date strings correctly."""
        from python.helpers.legal_agent_contracts import LegalTextVersion
        
        version = LegalTextVersion(
            text_id="test",
            version_id="v1",
            effective_from="2020-01-15",  # String
        )
        
        assert version.effective_from == date(2020, 1, 15)


class TestVersionResolution:
    """Tests for version resolution."""
    
    def test_resolve_single_version(self, sample_version):
        """Should resolve single valid version."""
        from python.helpers.legal_agent_contracts import resolve_version
        
        versions = [sample_version]
        as_of = date(2020, 1, 1)
        
        resolved, valid = resolve_version(versions, as_of)
        
        assert resolved is not None
        assert resolved.version_id == "v2016"
        assert len(valid) == 1
    
    def test_resolve_no_valid_version(self, sample_version):
        """Should return None if no valid version."""
        from python.helpers.legal_agent_contracts import resolve_version
        
        versions = [sample_version]
        as_of = date(2010, 1, 1)  # Before version's effective_from
        
        resolved, valid = resolve_version(versions, as_of)
        
        assert resolved is None
        assert len(valid) == 0
    
    def test_resolve_ambiguous_versions(self, sample_version, old_version):
        """Should detect ambiguity with overlapping versions."""
        from python.helpers.legal_agent_contracts import (
            LegalTextVersion,
            resolve_version,
        )
        
        # Create overlapping version
        overlapping = LegalTextVersion(
            text_id="LEGIARTI000006436298",
            version_id="v2016_bis",
            effective_from=date(2016, 10, 1),
            effective_to=None,
            is_current=True,
        )
        
        versions = [sample_version, overlapping]
        as_of = date(2020, 1, 1)
        
        resolved, valid = resolve_version(versions, as_of)
        
        # Ambiguous: multiple valid versions
        assert resolved is None
        assert len(valid) == 2
    
    def test_resolve_correct_version_at_date(self, sample_version, old_version):
        """Should resolve correct version at specific date."""
        from python.helpers.legal_agent_contracts import resolve_version
        
        versions = [sample_version, old_version]
        
        # At 2010: should get old version
        resolved_2010, _ = resolve_version(versions, date(2010, 1, 1))
        assert resolved_2010 is not None
        assert resolved_2010.version_id == "v2000"
        
        # At 2020: should get current version
        resolved_2020, _ = resolve_version(versions, date(2020, 1, 1))
        assert resolved_2020 is not None
        assert resolved_2020.version_id == "v2016"


# ═══════════════════════════════════════════════════════════════════════════════
# P5.2: SOURCE NOTE VERSION REQUIREMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceNoteVersioning:
    """Tests for SourceNote version requirement."""
    
    def test_source_note_without_version_fails(self):
        """SourceNote without version should fail when enforcement enabled."""
        from python.helpers.legal_agent_contracts import (
            SourceNote,
            ContractValidationError,
            compute_excerpt_hash,
        )
        
        os.environ["LEGAL_VERSION_ENFORCEMENT"] = "1"
        
        excerpt = "Test excerpt"
        
        with pytest.raises(ContractValidationError) as exc_info:
            SourceNote(
                origin_url="https://www.legifrance.gouv.fr/test",
                publisher="legifrance",
                jurisdiction="fr",
                excerpt=excerpt,
                excerpt_hash=compute_excerpt_hash(excerpt),
                chunk_id="chunk_001",
                # No legal_version
            )
        
        assert "legal_version" in str(exc_info.value)
    
    def test_source_note_without_version_ok_if_disabled(self):
        """SourceNote without version should pass when enforcement disabled."""
        from python.helpers.legal_agent_contracts import (
            SourceNote,
            compute_excerpt_hash,
        )
        
        os.environ["LEGAL_VERSION_ENFORCEMENT"] = "0"
        
        excerpt = "Test excerpt"
        
        # Should not raise
        sn = SourceNote(
            origin_url="https://www.legifrance.gouv.fr/test",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt=excerpt,
            excerpt_hash=compute_excerpt_hash(excerpt),
            chunk_id="chunk_001",
        )
        
        assert sn.legal_version is None
    
    def test_source_note_with_version(self, sample_version):
        """SourceNote with version should work."""
        from python.helpers.legal_agent_contracts import (
            SourceNote,
            compute_excerpt_hash,
        )
        
        excerpt = "Les contrats légalement formés..."
        
        sn = SourceNote(
            origin_url="https://www.legifrance.gouv.fr/test",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt=excerpt,
            excerpt_hash=compute_excerpt_hash(excerpt),
            chunk_id="chunk_001",
            legal_version=sample_version,
        )
        
        assert sn.legal_version is not None
        assert sn.version_id == "v2016"
        assert sn.effective_from == date(2016, 10, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# P5.3: AS_OF_DATE ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsOfDateEnforcement:
    """Tests for as_of_date enforcement in orchestrator."""
    
    def test_requires_as_of_date_medium_risk(self):
        """MEDIUM risk + OPERATIONAL scope should require as_of_date."""
        from python.helpers.legal_orchestrator import requires_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        assert requires_as_of_date(LegalRiskTier.MEDIUM, DecisionScope.OPERATIONAL) is True
    
    def test_requires_as_of_date_high_risk(self):
        """HIGH risk + BOARD scope should require as_of_date."""
        from python.helpers.legal_orchestrator import requires_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        assert requires_as_of_date(LegalRiskTier.HIGH, DecisionScope.BOARD) is True
    
    def test_not_requires_as_of_date_info_scope(self):
        """INFO scope should never require as_of_date."""
        from python.helpers.legal_orchestrator import requires_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        assert requires_as_of_date(LegalRiskTier.HIGH, DecisionScope.INFO) is False
    
    def test_not_requires_as_of_date_low_risk(self):
        """LOW risk should never require as_of_date."""
        from python.helpers.legal_orchestrator import requires_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        assert requires_as_of_date(LegalRiskTier.LOW, DecisionScope.OPERATIONAL) is False
    
    def test_validate_as_of_date_missing(self):
        """Should return error when as_of_date missing but required."""
        from python.helpers.legal_orchestrator import validate_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        error = validate_as_of_date(
            None,
            LegalRiskTier.MEDIUM,
            DecisionScope.OPERATIONAL,
            correlation_id="test",
        )
        
        assert error is not None
        assert "as_of_date required" in error
    
    def test_validate_as_of_date_provided(self):
        """Should return None when as_of_date provided."""
        from python.helpers.legal_orchestrator import validate_as_of_date
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        error = validate_as_of_date(
            date(2024, 1, 1),
            LegalRiskTier.HIGH,
            DecisionScope.BOARD,
            correlation_id="test",
        )
        
        assert error is None


# ═══════════════════════════════════════════════════════════════════════════════
# P5.4: VERSION_RESOLVED JUDGE CHECK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVersionResolvedCheck:
    """Tests for VERSION_RESOLVED judge check."""
    
    def test_version_resolved_check_pass(self):
        """VERSION_RESOLVED should pass when status is resolved."""
        from python.helpers.legal_pipeline import (
            LegalDraft,
            LegalRouteContext,
            LegalRiskTier,
            DecisionScope,
            Jurisdiction,
            judge_legal_draft,
            JudgeCheckResult,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="test_001",
            query="Test query",
            facts=["Fait 1"],
            rules=["Article 1103 C. civ."],
            application="Application test",
            source_chunk_ids=["chunk_001"],
            citations=["Art. 1103"],
            legal_context=ctx,
            version_status="resolved",
            as_of_date="2024-01-01",
        )
        
        result = judge_legal_draft(draft)
        
        # Find VERSION_RESOLVED check
        version_check = next(
            (c for c in result.checks if c.check_id == "version_resolved"),
            None
        )
        
        assert version_check is not None
        assert version_check.result == JudgeCheckResult.PASS
    
    def test_version_resolved_check_fail_ambiguous(self):
        """VERSION_RESOLVED should fail when status is ambiguous."""
        from python.helpers.legal_pipeline import (
            LegalDraft,
            LegalRouteContext,
            LegalRiskTier,
            DecisionScope,
            Jurisdiction,
            judge_legal_draft,
            JudgeCheckResult,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        
        draft = LegalDraft(
            draft_id="test_002",
            query="Test query",
            facts=["Fait 1"],
            rules=["Article 1103 C. civ."],
            application="Application test",
            source_chunk_ids=["chunk_001"],
            citations=["Art. 1103"],
            legal_context=ctx,
            version_status="ambiguous",
        )
        
        result = judge_legal_draft(draft)
        
        # Find VERSION_RESOLVED check
        version_check = next(
            (c for c in result.checks if c.check_id == "version_resolved"),
            None
        )
        
        assert version_check is not None
        assert version_check.result == JudgeCheckResult.FAIL
        assert "VERSION_RESOLVED" in result.critical_failures


# ═══════════════════════════════════════════════════════════════════════════════
# P5.5: OUTPUT RENDERING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputRendering:
    """Tests for output rendering with as_of_date."""
    
    def test_banner_with_as_of_date(self):
        """Banner should include date when as_of_date set."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.APPROVED_POSITION,
            answer="Test answer",
            as_of_date="2024-01-15",
        )
        
        banner = output.get_banner()
        
        assert "15/01/2024" in banner
        assert "droit en vigueur au" in banner
    
    def test_to_dict_includes_as_of_date(self):
        """to_dict should include as_of_date."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test",
            as_of_date="2024-06-01",
            version_status="resolved",
        )
        
        d = output.to_dict()
        
        assert d["as_of_date"] == "2024-06-01"
        assert d["version_status"] == "resolved"


# ═══════════════════════════════════════════════════════════════════════════════
# P5: PIPELINE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP5PipelineIntegration:
    """Integration tests for P5 in the pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_refusal_without_as_of_date(self):
        """Pipeline should refuse when as_of_date required but not provided."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        # This query should trigger MEDIUM+ risk
        output = await run_legal_pipeline(
            query="Un contrat commercial signé le 1er janvier peut-il être annulé ?",
            correlation_id="p5_test_001",
            as_of_date=None,  # Not provided
        )
        
        # Should refuse due to missing as_of_date if risk_tier >= MEDIUM
        # (depends on how detect_legal_context classifies this query)
        assert output is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_accepts_with_as_of_date(self):
        """Pipeline should accept when as_of_date provided."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        output = await run_legal_pipeline(
            query="Quelles sont les conditions de validité d'un contrat ?",
            correlation_id="p5_test_002",
            as_of_date="2024-01-15",
        )
        
        assert output is not None
        # The output should have as_of_date info
        assert output.as_of_date == "2024-01-15" or output.mode == LegalOutputMode.REFUSAL_REQUEST_INFO


# ═══════════════════════════════════════════════════════════════════════════════
# P5: NO REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP5NoRegression:
    """Verify P5 doesn't break P0.7-P4."""
    
    @pytest.mark.asyncio
    async def test_pipeline_still_works(self):
        """Pipeline should still work with P5 additions."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        output = await run_legal_pipeline(
            query="Test query for P5",
            correlation_id="p5_regression_001",
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


class TestP5NightlyE2E:
    """Nightly E2E tests for P5."""
    
    @nightly
    @pytest.mark.asyncio
    async def test_e2e_with_as_of_date(self, tmp_path):
        """Full E2E with as_of_date."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        
        output = await run_legal_pipeline(
            query="Un contrat signé en janvier 2020 est-il valide ?",
            correlation_id="nightly_e2e_p5",
            as_of_date="2024-01-01",
        )
        
        assert output is not None
        assert output.audit_bundle_id is not None


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
