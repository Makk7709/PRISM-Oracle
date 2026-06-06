"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                P6.1-VERIFY: PROPERTY-BASED TESTS FOR LEGAL DIFF             ║
║                                                                              ║
║  Tests de propriétés mathématiques du moteur de diff juridique:             ║
║  - Idempotence: diff(A,A) => 0 segments                                     ║
║  - Symétrie: diff(A,B) ↔ diff(B,A) inversé                                  ║
║  - Déterminisme: N runs => mêmes résultats                                  ║
║  - Stabilité append-only: ajout identique ne change pas le diff initial     ║
║                                                                              ║
║  Ces tests garantissent la fiabilité du diff sans dépendance externe.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date
from typing import Any, Dict, List, Tuple


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment for each test."""
    original_env = os.environ.copy()
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_DIFF_ENABLED"] = "1"
    os.environ["LEGAL_VERSION_ENFORCEMENT"] = "0"
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Sample texts for property tests
SAMPLE_TEXT_A = """Article 1. Le contrat de travail est conclu pour une durée indéterminée.
Article 2. Le délai de préavis est de 30 jours.
Article 3. Les parties peuvent convenir d'une période d'essai."""

SAMPLE_TEXT_B = """Article 1. Le contrat de travail doit obligatoirement être conclu par écrit.
Article 2. Le délai de préavis minimum est de 15 jours.
Article 3. Les parties sont exemptées de période d'essai."""

SAMPLE_TEXT_C = """Section additionnelle.
Cette section ne modifie pas le contenu précédent."""


# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_report(report) -> Dict[str, Any]:
    """
    Normalize a report for deterministic comparison.
    
    Removes non-deterministic fields (computed_at) and normalizes structure.
    """
    return {
        "text_id": report.text_id,
        "from_version_id": report.from_version_id,
        "to_version_id": report.to_version_id,
        "as_of_date": report.as_of_date.isoformat(),
        "diff_hash": report.diff_hash,
        "diff_status": report.diff_status.value,
        "total_segments": report.total_segments,
        "aggravation_detected": report.aggravation_detected,
        "relaxation_detected": report.relaxation_detected,
        "segments": [
            {
                "segment_id": s.segment_id,
                "change_type": s.change_type.value,
                "before_text": s.before_text,
                "after_text": s.after_text,
                "qualification": s.qualification.value,
                "detected_signals": sorted(s.detected_signals),
            }
            for s in sorted(report.segments, key=lambda x: x.segment_id)
        ],
    }


def get_segment_summary(report) -> List[Tuple[str, str, str]]:
    """Get a summary of segments for comparison: (change_type, qualification, has_texts)."""
    return sorted([
        (s.change_type.value, s.qualification.value, bool(s.before_text), bool(s.after_text))
        for s in report.segments
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 1: IDEMPOTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotence:
    """diff(A,A) must produce 0 segments."""
    
    def test_idempotence_simple(self):
        """Same text compared to itself produces no segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=SAMPLE_TEXT_A,
            new_text=SAMPLE_TEXT_A,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0, (
            f"Idempotence violated: diff(A,A) produced {report.total_segments} segments "
            f"instead of 0. Segments: {[s.to_dict() for s in report.segments]}"
        )
        assert not report.aggravation_detected
        assert not report.relaxation_detected
    
    def test_idempotence_with_whitespace_variations(self):
        """Whitespace-normalized identical texts produce no segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text_a = "Article 1. Test.\nArticle 2. Test."
        text_b = "  Article 1. Test.  \n  Article 2. Test.  "
        
        report = compute_legal_diff(
            old_text=text_a,
            new_text=text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        # After stripping, texts should be identical
        assert report.total_segments == 0, (
            f"Whitespace-only changes produced {report.total_segments} segments"
        )
    
    def test_idempotence_empty_text(self):
        """Empty texts produce no segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text="",
            new_text="",
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
    
    def test_idempotence_multiline(self):
        """Multiline identical text produces no segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text = """Paragraphe 1 avec plusieurs mots.
        
        Paragraphe 2 après une ligne vide.
        
        Paragraphe 3 final."""
        
        report = compute_legal_diff(
            old_text=text,
            new_text=text,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 2: SYMMETRY
# ═══════════════════════════════════════════════════════════════════════════════

class TestSymmetry:
    """diff(A,B) and diff(B,A) must be symmetric: ADD↔REMOVE, same count."""
    
    def test_symmetry_add_becomes_remove(self):
        """ADD in diff(A,B) becomes REMOVE in diff(B,A)."""
        from python.helpers.legal_diff import compute_legal_diff, ChangeType
        
        text_a = "Article 1. Contenu initial."
        text_b = "Article 1. Contenu initial.\nArticle 2. Nouveau contenu ajouté."
        
        report_ab = compute_legal_diff(
            old_text=text_a,
            new_text=text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report_ba = compute_legal_diff(
            old_text=text_b,
            new_text=text_a,
            text_id="TEST",
            from_version_id="v2",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        # Count changes
        adds_ab = len(report_ab.additions)
        removes_ab = len(report_ab.removals)
        adds_ba = len(report_ba.additions)
        removes_ba = len(report_ba.removals)
        
        assert adds_ab == removes_ba, (
            f"Symmetry violated: A→B has {adds_ab} ADD, B→A has {removes_ba} REMOVE"
        )
        assert removes_ab == adds_ba, (
            f"Symmetry violated: A→B has {removes_ab} REMOVE, B→A has {adds_ba} ADD"
        )
    
    def test_symmetry_total_segment_count(self):
        """Total segment count is preserved in symmetric diffs."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report_ab = compute_legal_diff(
            old_text=SAMPLE_TEXT_A,
            new_text=SAMPLE_TEXT_B,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report_ba = compute_legal_diff(
            old_text=SAMPLE_TEXT_B,
            new_text=SAMPLE_TEXT_A,
            text_id="TEST",
            from_version_id="v2",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        # MODIFY count stays same, ADD/REMOVE swap
        mods_ab = len(report_ab.modifications)
        mods_ba = len(report_ba.modifications)
        
        assert mods_ab == mods_ba, (
            f"MODIFY count differs: A→B={mods_ab}, B→A={mods_ba}"
        )
        
        total_ab = report_ab.total_segments
        total_ba = report_ba.total_segments
        
        assert total_ab == total_ba, (
            f"Total segment count differs: A→B={total_ab}, B→A={total_ba}"
        )
    
    def test_symmetry_modify_texts_swapped(self):
        """MODIFY segments have before/after swapped in reverse diff."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text_a = "Le délai est de 30 jours."
        text_b = "Le délai minimum est de 15 jours obligatoirement."
        
        report_ab = compute_legal_diff(
            old_text=text_a,
            new_text=text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report_ba = compute_legal_diff(
            old_text=text_b,
            new_text=text_a,
            text_id="TEST",
            from_version_id="v2",
            to_version_id="v1",
            as_of_date=date(2024, 1, 1),
        )
        
        if report_ab.modifications and report_ba.modifications:
            mod_ab = report_ab.modifications[0]
            mod_ba = report_ba.modifications[0]
            
            assert mod_ab.before_text == mod_ba.after_text, (
                f"MODIFY before/after not swapped correctly"
            )
            assert mod_ab.after_text == mod_ba.before_text, (
                f"MODIFY before/after not swapped correctly"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 3: DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    """Multiple runs of the same diff must produce identical results."""
    
    def test_determinism_5_runs(self):
        """5 runs of the same diff produce identical segment_id, diff_hash, and qualifications."""
        from python.helpers.legal_diff import compute_legal_diff
        
        results = []
        for _ in range(5):
            report = compute_legal_diff(
                old_text=SAMPLE_TEXT_A,
                new_text=SAMPLE_TEXT_B,
                text_id="TEST",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            results.append(normalize_report(report))
        
        # All results must be identical
        first = results[0]
        for i, result in enumerate(results[1:], 2):
            assert result == first, (
                f"Determinism violated: run {i} differs from run 1\n"
                f"Run 1: {first}\n"
                f"Run {i}: {result}"
            )
    
    def test_determinism_diff_hash(self):
        """diff_hash is deterministic across runs."""
        from python.helpers.legal_diff import compute_legal_diff
        
        hashes = set()
        for _ in range(5):
            report = compute_legal_diff(
                old_text=SAMPLE_TEXT_A,
                new_text=SAMPLE_TEXT_B,
                text_id="TEST",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            hashes.add(report.diff_hash)
        
        assert len(hashes) == 1, (
            f"diff_hash not deterministic: got {len(hashes)} different values: {hashes}"
        )
    
    def test_determinism_segment_ids(self):
        """segment_ids are deterministic across runs."""
        from python.helpers.legal_diff import compute_legal_diff
        
        segment_ids_sets = []
        for _ in range(5):
            report = compute_legal_diff(
                old_text=SAMPLE_TEXT_A,
                new_text=SAMPLE_TEXT_B,
                text_id="TEST",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            segment_ids_sets.append(tuple(s.segment_id for s in report.segments))
        
        assert len(set(segment_ids_sets)) == 1, (
            f"segment_ids not deterministic: {segment_ids_sets}"
        )
    
    def test_determinism_qualifications(self):
        """Qualifications are deterministic across runs."""
        from python.helpers.legal_diff import compute_legal_diff
        
        qualifications_sets = []
        for _ in range(5):
            report = compute_legal_diff(
                old_text=SAMPLE_TEXT_A,
                new_text=SAMPLE_TEXT_B,
                text_id="TEST",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            qualifications_sets.append(tuple(
                (s.segment_id, s.qualification.value) for s in report.segments
            ))
        
        assert len(set(qualifications_sets)) == 1, (
            f"Qualifications not deterministic: {qualifications_sets}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 4: APPEND-ONLY STABILITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppendOnlyStability:
    """Adding identical content to both texts preserves the original diff."""
    
    def test_append_same_suffix(self):
        """A+C vs B+C has same diff as A vs B for the original parts."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text_a = "Article 1. Version originale."
        text_b = "Article 1. Version modifiée obligatoirement."
        suffix = "\n\nSection commune ajoutée identiquement."
        
        # Original diff
        report_original = compute_legal_diff(
            old_text=text_a,
            new_text=text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        # Diff with same suffix
        report_appended = compute_legal_diff(
            old_text=text_a + suffix,
            new_text=text_b + suffix,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        # Same number of segments (suffix is identical, no change)
        assert report_original.total_segments == report_appended.total_segments, (
            f"Append-only stability violated: "
            f"original={report_original.total_segments}, "
            f"appended={report_appended.total_segments}"
        )
        
        # Same flags
        assert report_original.aggravation_detected == report_appended.aggravation_detected
        assert report_original.relaxation_detected == report_appended.relaxation_detected
    
    def test_prepend_same_prefix(self):
        """C+A vs C+B has same diff as A vs B for the differing parts."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text_a = "Article 1. Version originale."
        text_b = "Article 1. Version avec sanction obligatoire."
        prefix = "Préambule identique.\n\n"
        
        report_original = compute_legal_diff(
            old_text=text_a,
            new_text=text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report_prepended = compute_legal_diff(
            old_text=prefix + text_a,
            new_text=prefix + text_b,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report_original.total_segments == report_prepended.total_segments, (
            f"Prepend stability violated"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 5: CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsistency:
    """Ensure internal consistency of reports."""
    
    def test_flags_match_segments(self):
        """aggravation_detected/relaxation_detected match segment qualifications."""
        from python.helpers.legal_diff import compute_legal_diff, ImpactQualification
        
        report = compute_legal_diff(
            old_text=SAMPLE_TEXT_A,
            new_text=SAMPLE_TEXT_B,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        has_aggravating = any(
            s.qualification == ImpactQualification.AGGRAVATING
            for s in report.segments
        )
        has_relaxing = any(
            s.qualification == ImpactQualification.RELAXING
            for s in report.segments
        )
        
        assert report.aggravation_detected == has_aggravating, (
            f"aggravation_detected={report.aggravation_detected} "
            f"but segments have aggravating={has_aggravating}"
        )
        assert report.relaxation_detected == has_relaxing, (
            f"relaxation_detected={report.relaxation_detected} "
            f"but segments have relaxing={has_relaxing}"
        )
    
    def test_segment_count_properties(self):
        """total_segments == len(additions) + len(removals) + len(modifications)."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=SAMPLE_TEXT_A,
            new_text=SAMPLE_TEXT_B,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        computed_total = (
            len(report.additions) + 
            len(report.removals) + 
            len(report.modifications)
        )
        
        assert report.total_segments == computed_total, (
            f"Segment count inconsistent: "
            f"total_segments={report.total_segments}, "
            f"computed={computed_total}"
        )
    
    def test_all_segments_have_required_fields(self):
        """All segments have required fields based on change_type."""
        from python.helpers.legal_diff import compute_legal_diff, ChangeType
        
        report = compute_legal_diff(
            old_text=SAMPLE_TEXT_A,
            new_text=SAMPLE_TEXT_B,
            text_id="TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        for seg in report.segments:
            assert seg.segment_id, f"Missing segment_id"
            
            if seg.change_type == ChangeType.ADD:
                assert seg.after_text, f"ADD segment {seg.segment_id} missing after_text"
            elif seg.change_type == ChangeType.REMOVE:
                assert seg.before_text, f"REMOVE segment {seg.segment_id} missing before_text"
            elif seg.change_type == ChangeType.MODIFY:
                assert seg.before_text, f"MODIFY segment {seg.segment_id} missing before_text"
                assert seg.after_text, f"MODIFY segment {seg.segment_id} missing after_text"


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
