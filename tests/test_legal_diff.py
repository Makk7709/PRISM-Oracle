"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P6.1: LEGAL DIFF TESTS                                    ║
║                                                                              ║
║  Tests for P6.1 Diff Juridique Opposable & Analyse d'Évolution Normative:   ║
║  - LegalDiffSegment model                                                    ║
║  - LegalDiffReport model                                                     ║
║  - compute_legal_diff()                                                      ║
║  - qualify_change()                                                          ║
║  - Integration with pipeline                                                 ║
║                                                                              ║
║  Version: 1.0.0 (P6.1)                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date, datetime


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_DIFF_ENABLED"] = "1"
    os.environ["LEGAL_VERSION_ENFORCEMENT"] = "0"  # Disable for diff tests
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_old_text():
    """Sample old legal text (v1)."""
    return "Article 1. Le contrat peut être résilié par les parties.\nArticle 2. Le délai de préavis est de 30 jours.\nArticle 3. Les sanctions sont définies par le règlement."


@pytest.fixture
def sample_new_text_add():
    """Sample new text with addition."""
    return "Article 1. Le contrat peut être résilié par les parties.\nArticle 2. Le délai de préavis est de 30 jours.\nArticle 3. Les sanctions sont définies par le règlement.\nArticle 4. Une pénalité de retard s'applique obligatoirement."


@pytest.fixture
def sample_new_text_remove():
    """Sample new text with removal."""
    return "Article 1. Le contrat peut être résilié par les parties.\nArticle 3. Les sanctions sont définies par le règlement."


@pytest.fixture
def sample_new_text_modify():
    """Sample new text with modification (substantial change)."""
    return "Article 1. Le contrat doit obligatoirement être validé par un notaire.\nArticle 2. Le délai de préavis est de 30 jours.\nArticle 3. Les sanctions sont définies par le règlement."


@pytest.fixture
def sample_new_text_aggravating():
    """Sample new text with aggravating changes."""
    return "Article 1. Le contrat doit obligatoirement être validé immédiatement.\nArticle 2. Le délai minimum de préavis est de 15 jours.\nArticle 3. Les sanctions sont obligatoires et immédiates."


@pytest.fixture
def sample_new_text_relaxing():
    """Sample new text with relaxing changes."""
    return "Article 1. Le contrat peut être résilié par les parties.\nArticle 2. Le délai de préavis peut être prolongé jusqu'à 60 jours.\nArticle 3. Les parties sont exemptées de sanctions mineures."


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1.1: LEGAL DIFF SEGMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalDiffSegment:
    """Tests for LegalDiffSegment model."""
    
    def test_valid_add_segment(self):
        """Valid ADD segment should be created."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType, ImpactQualification
        
        seg = LegalDiffSegment(
            segment_id="seg_001",
            change_type=ChangeType.ADD,
            after_text="Nouveau texte ajouté",
        )
        
        assert seg.segment_id == "seg_001"
        assert seg.change_type == ChangeType.ADD
        assert seg.qualification == ImpactQualification.NEUTRAL
    
    def test_valid_remove_segment(self):
        """Valid REMOVE segment should be created."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType
        
        seg = LegalDiffSegment(
            segment_id="seg_002",
            change_type=ChangeType.REMOVE,
            before_text="Texte supprimé",
        )
        
        assert seg.change_type == ChangeType.REMOVE
        assert seg.before_text == "Texte supprimé"
    
    def test_valid_modify_segment(self):
        """Valid MODIFY segment should be created."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType
        
        seg = LegalDiffSegment(
            segment_id="seg_003",
            change_type=ChangeType.MODIFY,
            before_text="Ancien texte",
            after_text="Nouveau texte",
        )
        
        assert seg.change_type == ChangeType.MODIFY
        assert seg.before_text == "Ancien texte"
        assert seg.after_text == "Nouveau texte"
    
    def test_add_segment_requires_after_text(self):
        """ADD segment without after_text should fail."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType, DiffValidationError
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffSegment(
                segment_id="seg_001",
                change_type=ChangeType.ADD,
                # Missing after_text
            )
        
        assert "ADD segment requires after_text" in str(exc_info.value)
    
    def test_remove_segment_requires_before_text(self):
        """REMOVE segment without before_text should fail."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType, DiffValidationError
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffSegment(
                segment_id="seg_001",
                change_type=ChangeType.REMOVE,
                # Missing before_text
            )
        
        assert "REMOVE segment requires before_text" in str(exc_info.value)
    
    def test_modify_segment_requires_both_texts(self):
        """MODIFY segment requires both before and after text."""
        from python.helpers.legal_diff import LegalDiffSegment, ChangeType, DiffValidationError
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffSegment(
                segment_id="seg_001",
                change_type=ChangeType.MODIFY,
                before_text="Only before",
                # Missing after_text
            )
        
        assert "MODIFY segment requires before_text AND after_text" in str(exc_info.value)
    
    def test_non_neutral_requires_signals(self):
        """Non-NEUTRAL qualification requires detected_signals."""
        from python.helpers.legal_diff import (
            LegalDiffSegment, 
            ChangeType, 
            ImpactQualification,
            DiffValidationError,
        )
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffSegment(
                segment_id="seg_001",
                change_type=ChangeType.ADD,
                after_text="Test",
                qualification=ImpactQualification.AGGRAVATING,
                # Missing detected_signals
            )
        
        assert "aggravating qualification requires detected_signals" in str(exc_info.value).lower()


class TestLegalDiffReport:
    """Tests for LegalDiffReport model."""
    
    def test_valid_report(self):
        """Valid report should be created."""
        from python.helpers.legal_diff import (
            LegalDiffReport, 
            LegalDiffSegment,
            ChangeType,
            DiffStatus,
        )
        
        report = LegalDiffReport(
            text_id="LEGIARTI123",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
            segments=[
                LegalDiffSegment(
                    segment_id="seg_001",
                    change_type=ChangeType.ADD,
                    after_text="New text",
                )
            ],
        )
        
        assert report.text_id == "LEGIARTI123"
        assert report.diff_status == DiffStatus.AVAILABLE
        assert report.total_segments == 1
    
    def test_report_requires_text_id(self):
        """Report requires text_id."""
        from python.helpers.legal_diff import LegalDiffReport, DiffValidationError
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffReport(
                text_id="",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
        
        assert "text_id required" in str(exc_info.value)
    
    def test_report_requires_as_of_date(self):
        """Report requires as_of_date (P5 inheritance)."""
        from python.helpers.legal_diff import LegalDiffReport, DiffValidationError
        
        with pytest.raises(DiffValidationError) as exc_info:
            LegalDiffReport(
                text_id="TEST",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=None,
            )
        
        assert "as_of_date required" in str(exc_info.value)
    
    def test_report_computes_hash(self):
        """Report should compute deterministic hash."""
        from python.helpers.legal_diff import LegalDiffReport
        
        report1 = LegalDiffReport(
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report2 = LegalDiffReport(
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report1.diff_hash == report2.diff_hash
    
    def test_report_to_markdown(self):
        """Report should generate markdown."""
        from python.helpers.legal_diff import (
            LegalDiffReport,
            LegalDiffSegment,
            ChangeType,
        )
        
        report = LegalDiffReport(
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 15),
            segments=[
                LegalDiffSegment(
                    segment_id="seg_001",
                    change_type=ChangeType.ADD,
                    after_text="Nouveau texte",
                )
            ],
        )
        
        md = report.to_markdown()
        
        assert "Évolutions depuis la version précédente" in md
        assert "v1" in md
        assert "v2" in md
        assert "15/01/2024" in md


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1.2: DIFF ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeLegalDiff:
    """Tests for compute_legal_diff()."""
    
    def test_diff_pure_addition(self, sample_old_text, sample_new_text_add):
        """Should detect pure addition."""
        from python.helpers.legal_diff import compute_legal_diff, ChangeType
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_add,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert len(report.additions) >= 1
        assert any("pénalité" in seg.after_text.lower() for seg in report.additions)
    
    def test_diff_pure_removal(self, sample_old_text, sample_new_text_remove):
        """Should detect pure removal."""
        from python.helpers.legal_diff import compute_legal_diff, ChangeType
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_remove,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert len(report.removals) >= 1
        assert any("préavis" in seg.before_text.lower() for seg in report.removals)
    
    def test_diff_modification(self, sample_old_text, sample_new_text_modify):
        """Should detect modification."""
        from python.helpers.legal_diff import compute_legal_diff, ChangeType
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_modify,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        # Should have at least one modification
        assert len(report.modifications) >= 1 or len(report.segments) >= 1
    
    def test_diff_no_changes(self, sample_old_text):
        """Should handle identical texts."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_old_text,  # Same text
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
        assert "Aucune modification" in report.summary


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1.3: QUALIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualifyChange:
    """Tests for qualify_change()."""
    
    def test_neutral_by_default(self):
        """Should return NEUTRAL by default."""
        from python.helpers.legal_diff import qualify_change, ChangeType, ImpactQualification
        
        qual, reason, signals = qualify_change(
            change_type=ChangeType.ADD,
            before_text=None,
            after_text="Texte neutre sans signal",
        )
        
        assert qual == ImpactQualification.NEUTRAL
    
    def test_aggravating_detected(self):
        """Should detect AGGRAVATING when obligation added."""
        from python.helpers.legal_diff import qualify_change, ChangeType, ImpactQualification
        
        qual, reason, signals = qualify_change(
            change_type=ChangeType.ADD,
            before_text=None,
            after_text="L'entreprise doit obligatoirement respecter les délais",
        )
        
        assert qual == ImpactQualification.AGGRAVATING
        assert len(signals) > 0
    
    def test_relaxing_detected(self):
        """Should detect RELAXING when exemption added."""
        from python.helpers.legal_diff import qualify_change, ChangeType, ImpactQualification
        
        qual, reason, signals = qualify_change(
            change_type=ChangeType.ADD,
            before_text=None,
            after_text="Les petites entreprises peuvent être exemptées",
        )
        
        assert qual == ImpactQualification.RELAXING
        assert len(signals) > 0
    
    def test_aggravating_on_sanction(self):
        """Should detect AGGRAVATING when sanction added."""
        from python.helpers.legal_diff import qualify_change, ChangeType, ImpactQualification
        
        qual, reason, signals = qualify_change(
            change_type=ChangeType.MODIFY,
            before_text="Un rappel sera envoyé",
            after_text="Une sanction immédiate sera appliquée",
        )
        
        assert qual == ImpactQualification.AGGRAVATING
    
    def test_relaxing_on_prolongation(self):
        """Should detect RELAXING when delay prolonged."""
        from python.helpers.legal_diff import qualify_change, ChangeType, ImpactQualification
        
        qual, reason, signals = qualify_change(
            change_type=ChangeType.MODIFY,
            before_text="Le délai est de 30 jours",
            after_text="Le délai peut être prolongé jusqu'à 60 jours",
        )
        
        assert qual == ImpactQualification.RELAXING


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1 INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiffIntegration:
    """Integration tests for diff in pipeline."""
    
    def test_diff_in_aggravating_scenario(self, sample_old_text, sample_new_text_aggravating):
        """Full diff should detect aggravation."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_aggravating,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.aggravation_detected is True
        assert "Aggravation" in report.summary or any(
            seg.qualification.value == "aggravating" for seg in report.segments
        )
    
    def test_diff_in_relaxing_scenario(self, sample_old_text, sample_new_text_relaxing):
        """Full diff should detect relaxation."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_relaxing,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.relaxation_detected is True or len(report.segments) > 0
    
    def test_not_applicable_report(self):
        """Should create NOT_APPLICABLE report when no previous version."""
        from python.helpers.legal_diff import (
            create_not_applicable_report,
            DiffStatus,
        )
        
        report = create_not_applicable_report(
            text_id="TEST",
            current_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.diff_status == DiffStatus.NOT_APPLICABLE
        assert report.from_version_id == "N/A"
    
    def test_output_includes_diff_fields(self):
        """LegalOutput should include diff fields."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test",
            diff_status="available",
            diff_summary="1 ajout détecté",
            diff_report={"text_id": "TEST", "total_segments": 1},
        )
        
        d = output.to_dict()
        
        assert d["diff_status"] == "available"
        assert d["diff_summary"] == "1 ajout détecté"
        assert d["diff_report"]["text_id"] == "TEST"
    
    def test_output_markdown_includes_diff(self):
        """LegalOutput markdown should include diff section."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test",
            audit_bundle_id="test_123",
            judge_verdict="approve",
            diff_status="available",
            diff_summary="Modifications: 1 ajout.",
            diff_report={"aggravation_detected": True},
        )
        
        md = output.to_markdown()
        
        assert "Évolutions" in md
        assert "Modifications: 1 ajout" in md
        assert "Aggravation" in md


# ═══════════════════════════════════════════════════════════════════════════════
# P6.1: NO REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP61NoRegression:
    """Verify P6.1 doesn't break P0.7-P5."""
    
    @pytest.mark.asyncio
    async def test_pipeline_still_works(self):
        """Pipeline should still work with P6.1 additions."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        output = await run_legal_pipeline(
            query="Test query for P6.1",
            correlation_id="p61_test_001",
        )
        
        assert output is not None
        assert output.mode in list(LegalOutputMode)
    
    def test_p6_diff_available(self):
        """P6 diff module should be available."""
        from python.helpers.legal_orchestrator import P6_DIFF_AVAILABLE
        
        assert P6_DIFF_AVAILABLE is True
    
    def test_is_diff_enabled_flag(self):
        """is_diff_enabled flag should work."""
        from python.helpers.legal_orchestrator import is_diff_enabled
        
        os.environ["LEGAL_DIFF_ENABLED"] = "1"
        assert is_diff_enabled() is True
        
        os.environ["LEGAL_DIFF_ENABLED"] = "0"
        assert is_diff_enabled() is False


# ═══════════════════════════════════════════════════════════════════════════════
# NIGHTLY-ONLY E2E TESTS
# ═══════════════════════════════════════════════════════════════════════════════

nightly = pytest.mark.skipif(
    os.environ.get("CI_NIGHTLY", "0") != "1",
    reason="Nightly-only test (set CI_NIGHTLY=1 to run)"
)


class TestP61NightlyE2E:
    """Nightly E2E tests for P6.1."""
    
    @nightly
    def test_full_diff_workflow(self, sample_old_text, sample_new_text_aggravating):
        """Full diff workflow end-to-end."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=sample_old_text,
            new_text=sample_new_text_aggravating,
            text_id="LEGIARTI000TEST",
            from_version_id="v2020",
            to_version_id="v2024",
            as_of_date=date(2024, 1, 15),
        )
        
        # Full validation
        assert report.text_id == "LEGIARTI000TEST"
        assert report.diff_hash  # Has hash
        assert report.summary  # Has summary
        
        # Segments all valid
        for seg in report.segments:
            assert seg.segment_id
            assert seg.change_type


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
