"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                P6.1-VERIFY: GOLDEN FILE TESTS FOR LEGAL DIFF                ║
║                                                                              ║
║  Tests de non-régression basés sur des cas de référence (golden files).     ║
║  Chaque golden file définit un scénario avec entrées et sorties attendues.  ║
║                                                                              ║
║  Structure golden file:                                                      ║
║  {                                                                           ║
║    "case_id": "identifier",                                                  ║
║    "description": "...",                                                     ║
║    "before": "texte avant",                                                  ║
║    "after": "texte après",                                                   ║
║    "expected": {                                                             ║
║      "diff_status": "available",                                             ║
║      "aggravation_detected": true/false,                                     ║
║      "relaxation_detected": true/false,                                      ║
║      "min_segments": N,                                                      ║
║      "must_contain_signals": [...],                                          ║
║      "must_have_topic": [...],                                               ║
║      "must_have_change_type": [...]                                          ║
║    }                                                                         ║
║  }                                                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GOLDEN_DIR = Path(__file__).parent / "golden" / "legal_diff_cases"


# ═══════════════════════════════════════════════════════════════════════════════
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


def load_golden_cases() -> List[Dict[str, Any]]:
    """Load all golden case files."""
    cases = []
    if not GOLDEN_DIR.exists():
        return cases
    
    for json_file in sorted(GOLDEN_DIR.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            case = json.load(f)
            case["_file"] = json_file.name
            cases.append(case)
    
    return cases


GOLDEN_CASES = load_golden_cases()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def format_segment_summary(report) -> str:
    """Format segment summary for error messages."""
    lines = []
    for seg in report.segments:
        lines.append(
            f"  - {seg.segment_id}: {seg.change_type.value} "
            f"[{seg.qualification.value}] signals={seg.detected_signals}"
        )
        if seg.before_text:
            lines.append(f"    before: {seg.before_text[:60]}...")
        if seg.after_text:
            lines.append(f"    after: {seg.after_text[:60]}...")
    return "\n".join(lines) if lines else "  (no segments)"


def get_all_signals(report) -> List[str]:
    """Get all detected signals from all segments."""
    signals = []
    for seg in report.segments:
        signals.extend(seg.detected_signals)
    return signals


def get_all_topics(report) -> List[str]:
    """Get all topics from all segments."""
    topics = []
    for seg in report.segments:
        topics.extend(seg.impacted_topics)
    return list(set(topics))


def get_all_change_types(report) -> List[str]:
    """Get all change types from all segments."""
    return [seg.change_type.value for seg in report.segments]


def get_all_qualifications(report) -> List[str]:
    """Get all qualifications from all segments."""
    return [seg.qualification.value for seg in report.segments]


# ═══════════════════════════════════════════════════════════════════════════════
# PARAMETRIZED GOLDEN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "case",
    GOLDEN_CASES,
    ids=[c.get("case_id", c.get("_file", "unknown")) for c in GOLDEN_CASES],
)
class TestGoldenCases:
    """Parametrized tests for all golden cases."""
    
    def test_golden_case(self, case: Dict[str, Any]):
        """Run a single golden case test."""
        from python.helpers.legal_diff import compute_legal_diff, DiffStatus
        
        case_id = case.get("case_id", case.get("_file", "unknown"))
        description = case.get("description", "No description")
        before = case.get("before", "")
        after = case.get("after", "")
        expected = case.get("expected", {})
        
        # Compute diff
        report = compute_legal_diff(
            old_text=before,
            new_text=after,
            text_id=f"GOLDEN_{case_id}",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 15),
        )
        
        # Build error context
        error_context = (
            f"\n{'='*60}\n"
            f"GOLDEN CASE: {case_id}\n"
            f"Description: {description}\n"
            f"Before: {before[:100]}...\n"
            f"After: {after[:100]}...\n"
            f"{'='*60}\n"
            f"ACTUAL RESULT:\n"
            f"  diff_status: {report.diff_status.value}\n"
            f"  aggravation_detected: {report.aggravation_detected}\n"
            f"  relaxation_detected: {report.relaxation_detected}\n"
            f"  total_segments: {report.total_segments}\n"
            f"  segments:\n{format_segment_summary(report)}\n"
            f"{'='*60}"
        )
        
        # Check diff_status
        if "diff_status" in expected:
            assert report.diff_status == DiffStatus(expected["diff_status"]), (
                f"diff_status mismatch{error_context}"
            )
        
        # Check aggravation_detected
        if "aggravation_detected" in expected:
            assert report.aggravation_detected == expected["aggravation_detected"], (
                f"aggravation_detected mismatch: "
                f"expected={expected['aggravation_detected']}, "
                f"actual={report.aggravation_detected}"
                f"{error_context}"
            )
        
        # Check relaxation_detected
        if "relaxation_detected" in expected:
            assert report.relaxation_detected == expected["relaxation_detected"], (
                f"relaxation_detected mismatch: "
                f"expected={expected['relaxation_detected']}, "
                f"actual={report.relaxation_detected}"
                f"{error_context}"
            )
        
        # Check min_segments
        if "min_segments" in expected:
            assert report.total_segments >= expected["min_segments"], (
                f"min_segments not met: "
                f"expected>={expected['min_segments']}, "
                f"actual={report.total_segments}"
                f"{error_context}"
            )
        
        # Check max_segments
        if "max_segments" in expected:
            assert report.total_segments <= expected["max_segments"], (
                f"max_segments exceeded: "
                f"expected<={expected['max_segments']}, "
                f"actual={report.total_segments}"
                f"{error_context}"
            )
        
        # Check must_contain_signals
        if "must_contain_signals" in expected:
            all_signals = get_all_signals(report)
            for signal in expected["must_contain_signals"]:
                assert signal in all_signals, (
                    f"Missing expected signal '{signal}' in {all_signals}"
                    f"{error_context}"
                )
        
        # Check must_have_topic
        if "must_have_topic" in expected:
            all_topics = get_all_topics(report)
            for topic in expected["must_have_topic"]:
                assert topic in all_topics, (
                    f"Missing expected topic '{topic}' in {all_topics}"
                    f"{error_context}"
                )
        
        # Check must_have_change_type
        if "must_have_change_type" in expected:
            all_change_types = get_all_change_types(report)
            for ct in expected["must_have_change_type"]:
                assert ct in all_change_types, (
                    f"Missing expected change_type '{ct}' in {all_change_types}"
                    f"{error_context}"
                )
        
        # Check must_have_qualification
        if "must_have_qualification" in expected:
            all_qualifications = get_all_qualifications(report)
            qual = expected["must_have_qualification"]
            assert qual in all_qualifications, (
                f"Missing expected qualification '{qual}' in {all_qualifications}"
                f"{error_context}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE GOLDEN VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldenFileStructure:
    """Validate golden file structure and coverage."""
    
    def test_golden_dir_exists(self):
        """Golden directory should exist."""
        assert GOLDEN_DIR.exists(), f"Golden directory not found: {GOLDEN_DIR}"
    
    def test_minimum_golden_files(self):
        """Should have at least 10 golden files."""
        files = list(GOLDEN_DIR.glob("*.json"))
        assert len(files) >= 10, (
            f"Expected at least 10 golden files, found {len(files)}: "
            f"{[f.name for f in files]}"
        )
    
    def test_golden_files_valid_json(self):
        """All golden files should be valid JSON."""
        for json_file in GOLDEN_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    assert "before" in data, f"Missing 'before' in {json_file.name}"
                    assert "after" in data, f"Missing 'after' in {json_file.name}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {json_file.name}: {e}")
    
    def test_golden_case_ids_unique(self):
        """All case IDs should be unique."""
        case_ids = [c.get("case_id") for c in GOLDEN_CASES if c.get("case_id")]
        assert len(case_ids) == len(set(case_ids)), (
            f"Duplicate case IDs found: {case_ids}"
        )
    
    def test_coverage_no_change(self):
        """Should have a no_change case."""
        case_ids = [c.get("case_id", "") for c in GOLDEN_CASES]
        assert any("no_change" in cid for cid in case_ids), (
            "Missing no_change golden case"
        )
    
    def test_coverage_add(self):
        """Should have an add case."""
        case_ids = [c.get("case_id", "") for c in GOLDEN_CASES]
        assert any("add" in cid for cid in case_ids), (
            "Missing add golden case"
        )
    
    def test_coverage_remove(self):
        """Should have a remove case."""
        case_ids = [c.get("case_id", "") for c in GOLDEN_CASES]
        assert any("remove" in cid for cid in case_ids), (
            "Missing remove golden case"
        )
    
    def test_coverage_modify(self):
        """Should have a modify case."""
        case_ids = [c.get("case_id", "") for c in GOLDEN_CASES]
        assert any("modify" in cid for cid in case_ids), (
            "Missing modify golden case"
        )
    
    def test_coverage_aggravation(self):
        """Should have cases testing aggravation."""
        has_aggravation = any(
            c.get("expected", {}).get("aggravation_detected") is True
            for c in GOLDEN_CASES
        )
        assert has_aggravation, "No golden case tests aggravation_detected=True"
    
    def test_coverage_relaxation(self):
        """Should have cases testing relaxation."""
        has_relaxation = any(
            c.get("expected", {}).get("relaxation_detected") is True
            for c in GOLDEN_CASES
        )
        assert has_relaxation, "No golden case tests relaxation_detected=True"


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT GENERATION (DEBUG HELPER)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_snapshot(case: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a normalized snapshot for a golden case (for debugging)."""
    from python.helpers.legal_diff import compute_legal_diff
    
    report = compute_legal_diff(
        old_text=case.get("before", ""),
        new_text=case.get("after", ""),
        text_id=f"SNAPSHOT_{case.get('case_id', 'unknown')}",
        from_version_id="v1",
        to_version_id="v2",
        as_of_date=date(2024, 1, 15),
    )
    
    return {
        "case_id": case.get("case_id"),
        "diff_status": report.diff_status.value,
        "aggravation_detected": report.aggravation_detected,
        "relaxation_detected": report.relaxation_detected,
        "total_segments": report.total_segments,
        "change_types": get_all_change_types(report),
        "qualifications": get_all_qualifications(report),
        "signals": get_all_signals(report),
        "topics": get_all_topics(report),
    }


class TestSnapshotGeneration:
    """Utility tests for snapshot generation (not for CI, for debugging)."""
    
    def test_can_generate_snapshots(self):
        """Verify snapshot generation works."""
        if not GOLDEN_CASES:
            pytest.skip("No golden cases found")
        
        snapshot = generate_snapshot(GOLDEN_CASES[0])
        assert "diff_status" in snapshot
        assert "total_segments" in snapshot


# ═══════════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
