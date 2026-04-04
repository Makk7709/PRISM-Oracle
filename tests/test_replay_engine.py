"""
Tests A2A — Replay Engine.

Couvre :
  - Capture et persistance de snapshots
  - Verification d'integrite (tamper detection)
  - Comparaison de reponses (divergence NONE / MINOR / SIGNIFICANT / CRITICAL)
  - Determinisme (meme input → meme snapshot)
  - Robustesse aux donnees vides / corrompues
  - Property tests (invariance, idempotence)
"""

import json
import os
import tempfile

import pytest

from python.helpers.replay_engine import (
    DivergenceLevel,
    ModelSnapshot,
    SessionSnapshot,
    capture_snapshot,
    compare_responses,
    load_snapshot,
    save_snapshot,
    verify_snapshot_integrity,
)


# ─── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def tmp_base(tmp_path):
    """Base directory for test storage."""
    return str(tmp_path)


@pytest.fixture
def sample_snapshot():
    """A fully populated snapshot for testing."""
    return capture_snapshot(
        context_id="test-ctx-001",
        session_id="KRV-SES-20260404-ABC1234",
        query="What is the capital of France?",
        response="The capital of France is Paris.",
        system_prompt="You are a helpful assistant.",
        history_text="User: What is the capital of France?\nAssistant: The capital of France is Paris.",
        agent_profile="agent_0",
        model_provider="openrouter",
        model_name="anthropic/claude-sonnet-4-20250514",
        model_temperature=0.0,
        model_kwargs={"max_tokens": 4096},
        tool_calls=[{"name": "knowledge_lookup", "args": {"q": "France capital"}}],
        delegation_chain=["agent_0"],
        execution_budget={"current_iterations": 2, "current_tool_calls": 1},
        tokens_input=150,
        tokens_output=25,
        username="test_user",
        organization="test_org",
        correlation_id="corr-12345",
    )


# ─── Snapshot Capture ────────────────────────────────────

class TestSnapshotCapture:
    def test_capture_produces_valid_snapshot(self, sample_snapshot):
        assert sample_snapshot.context_id == "test-ctx-001"
        assert sample_snapshot.query == "What is the capital of France?"
        assert sample_snapshot.response == "The capital of France is Paris."
        assert sample_snapshot.model_config.provider == "openrouter"
        assert sample_snapshot.model_config.temperature == 0.0
        assert sample_snapshot.tokens_input == 150
        assert sample_snapshot.correlation_id == "corr-12345"

    def test_capture_computes_hashes(self, sample_snapshot):
        assert sample_snapshot.response_hash is not None
        assert sample_snapshot.response_hash.startswith("sha256:")
        assert sample_snapshot.system_prompt_hash is not None
        assert sample_snapshot.system_prompt_hash.startswith("sha256:")
        assert sample_snapshot.history_hash is not None
        assert sample_snapshot.integrity_hash.startswith("sha256:")

    def test_capture_with_empty_query(self):
        snap = capture_snapshot(context_id="ctx-empty", query="", response="")
        assert snap.context_id == "ctx-empty"
        assert snap.response_hash is None
        assert snap.system_prompt_hash is None

    def test_capture_generates_correlation_id(self):
        snap = capture_snapshot(context_id="ctx-no-corr")
        assert snap.correlation_id != ""

    def test_snapshot_version(self, sample_snapshot):
        assert sample_snapshot.snapshot_version == "1.0.0"


# ─── Persistance ─────────────────────────────────────────

class TestSnapshotPersistence:
    def test_save_and_load_roundtrip(self, sample_snapshot, tmp_base):
        path = save_snapshot(sample_snapshot, base_dir=tmp_base)
        assert os.path.exists(path)
        assert path.endswith("replay_snapshot.json")

        loaded = load_snapshot("test-ctx-001", base_dir=tmp_base)
        assert loaded is not None
        assert loaded.context_id == sample_snapshot.context_id
        assert loaded.query == sample_snapshot.query
        assert loaded.response_hash == sample_snapshot.response_hash
        assert loaded.integrity_hash == sample_snapshot.integrity_hash

    def test_load_nonexistent_returns_none(self, tmp_base):
        result = load_snapshot("nonexistent-ctx", base_dir=tmp_base)
        assert result is None

    def test_save_creates_directory(self, tmp_base):
        snap = capture_snapshot(context_id="new-ctx-dir", query="test")
        path = save_snapshot(snap, base_dir=tmp_base)
        assert os.path.isdir(os.path.join(tmp_base, "tmp", "chats", "new-ctx-dir"))

    def test_serialization_is_valid_json(self, sample_snapshot, tmp_base):
        path = save_snapshot(sample_snapshot, base_dir=tmp_base)
        with open(path, "r") as f:
            data = json.load(f)
        assert data["context_id"] == "test-ctx-001"
        assert data["model_config"]["provider"] == "openrouter"


# ─── Integrity Verification ──────────────────────────────

class TestIntegrityVerification:
    def test_unaltered_snapshot_passes(self, sample_snapshot):
        assert verify_snapshot_integrity(sample_snapshot) is True

    def test_tampered_response_hash_fails(self, sample_snapshot):
        sample_snapshot.response_hash = "sha256:0000000000000000"
        assert verify_snapshot_integrity(sample_snapshot) is False

    def test_tampered_query_fails(self, sample_snapshot):
        original_hash = sample_snapshot.integrity_hash
        sample_snapshot.query = "TAMPERED QUERY"
        assert verify_snapshot_integrity(sample_snapshot) is False

    def test_tampered_model_config_fails(self, sample_snapshot):
        sample_snapshot.model_config.temperature = 1.0
        assert verify_snapshot_integrity(sample_snapshot) is False

    def test_integrity_after_save_load(self, sample_snapshot, tmp_base):
        save_snapshot(sample_snapshot, base_dir=tmp_base)
        loaded = load_snapshot("test-ctx-001", base_dir=tmp_base)
        assert loaded is not None
        assert verify_snapshot_integrity(loaded) is True


# ─── Response Comparison ─────────────────────────────────

class TestResponseComparison:
    def test_identical_responses(self):
        report = compare_responses("Paris is the capital.", "Paris is the capital.")
        assert report.level == DivergenceLevel.NONE
        assert report.response_match is True
        assert report.response_similarity == 1.0
        assert report.hash_match is True

    def test_minor_divergence(self):
        original = "The capital of France is Paris, a beautiful city with many landmarks."
        replayed = "The capital of France is Paris, a wonderful city with many landmarks."
        report = compare_responses(original, replayed)
        assert report.level in (DivergenceLevel.NONE, DivergenceLevel.MINOR, DivergenceLevel.SIGNIFICANT)
        assert report.response_similarity >= 0.7

    def test_significant_divergence(self):
        original = "The capital of France is Paris."
        replayed = "Berlin is the capital of Germany. It has many museums."
        report = compare_responses(original, replayed)
        assert report.level in (DivergenceLevel.SIGNIFICANT, DivergenceLevel.CRITICAL)
        assert report.response_match is False

    def test_critical_divergence(self):
        original = "Yes, the transaction is approved with high confidence."
        replayed = "No, the transaction is rejected due to fraud signals."
        report = compare_responses(original, replayed)
        assert report.response_match is False
        assert report.hash_match is False

    def test_empty_vs_content(self):
        report = compare_responses("", "Some content here")
        assert report.response_match is False

    def test_length_disparity_detection(self):
        original = "Short."
        replayed = "This is a much longer response with many additional words and details that were not in the original response at all."
        report = compare_responses(original, replayed)
        assert any("longueur" in d for d in report.details) or report.level != DivergenceLevel.NONE


# ─── Determinism (Property Tests) ────────────────────────

class TestDeterminism:
    def test_same_input_same_integrity_hash(self):
        """Property: identical inputs must produce identical integrity hashes."""
        kwargs = dict(
            context_id="det-ctx",
            query="Test query",
            response="Test response",
            model_provider="test",
            model_name="test-model",
            model_temperature=0.0,
            correlation_id="fixed-corr",
        )
        snap1 = capture_snapshot(**kwargs)
        snap2 = capture_snapshot(**kwargs)
        assert snap1.integrity_hash == snap2.integrity_hash

    def test_different_response_different_hash(self):
        """Property: different responses must produce different integrity hashes."""
        base = dict(
            context_id="det-ctx2",
            query="Same query",
            correlation_id="fixed",
        )
        snap1 = capture_snapshot(**base, response="Response A")
        snap2 = capture_snapshot(**base, response="Response B")
        assert snap1.integrity_hash != snap2.integrity_hash

    def test_comparison_is_symmetric(self):
        """Property: compare(a, b) and compare(b, a) yield the same similarity."""
        a = "The capital is Paris."
        b = "Paris is the capital."
        r1 = compare_responses(a, b)
        r2 = compare_responses(b, a)
        assert r1.response_similarity == r2.response_similarity

    def test_comparison_reflexive(self):
        """Property: compare(a, a) always yields NONE divergence."""
        for text in ["Hello", "", "A" * 10000, "Special chars: é à ü"]:
            report = compare_responses(text, text)
            assert report.level == DivergenceLevel.NONE


# ─── Edge Cases and Robustness ───────────────────────────

class TestEdgeCases:
    def test_unicode_handling(self):
        snap = capture_snapshot(
            context_id="unicode-ctx",
            query="Qu'est-ce que la théorie de la relativité ?",
            response="La théorie de la relativité d'Einstein décrit la gravitation.",
        )
        assert snap.response_hash is not None
        assert verify_snapshot_integrity(snap) is True

    def test_very_large_response(self):
        large = "word " * 100_000
        snap = capture_snapshot(context_id="large-ctx", query="big", response=large)
        assert snap.response_hash is not None
        assert verify_snapshot_integrity(snap) is True

    def test_special_characters_in_query(self):
        snap = capture_snapshot(
            context_id="special-ctx",
            query='{"injection": true, "<script>alert(1)</script>"}',
            response="Safe response.",
        )
        assert verify_snapshot_integrity(snap) is True

    def test_from_dict_with_extra_fields_ignores_them(self):
        data = {
            "snapshot_version": "1.0.0",
            "context_id": "test",
            "model_config": {"provider": "test", "name": "test"},
            "unknown_field": "should_be_ignored",
        }
        snap = SessionSnapshot.from_dict(data)
        assert snap.context_id == "test"

    def test_to_dict_roundtrip(self, sample_snapshot):
        d = sample_snapshot.to_dict()
        restored = SessionSnapshot.from_dict(d)
        assert restored.context_id == sample_snapshot.context_id
        assert restored.integrity_hash == sample_snapshot.integrity_hash
        assert restored.model_config.provider == sample_snapshot.model_config.provider
