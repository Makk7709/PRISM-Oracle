"""
SESSION 12 — Tests: query hash backfill + dynamic human_review / consensus flags.

Validates:
  - envelope.query backfill from various message formats (string, dict, list)
  - has_human_review resolved from legal output, metacognition, explicit flag
  - has_consensus resolved from consensus_result, prism flag, assessment
  - Flags stay False when no signal is present
  - Non-blocking on errors
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from python.helpers.session_envelope import SessionEnvelope


def _make_hook():
    """Build a minimal AuditMetadataAppend with a mock agent."""
    from python.extensions.monologue_start._20_audit_metadata_append import (
        AuditMetadataAppend,
    )
    agent = MagicMock()
    stored = {}
    agent.set_data = lambda k, v: stored.__setitem__(k, v)
    agent.get_data = lambda k: stored.get(k)
    hook = AuditMetadataAppend.__new__(AuditMetadataAppend)
    hook.agent = agent
    hook._stored = stored
    return hook


def _make_loop_data(content):
    """Build a mock loop_data with user_message.content = content."""
    ld = MagicMock()
    ld.user_message.content = content
    return ld


# ═══════════════════════════════════════════════════════════════════════════════
# BACKFILL ENVELOPE.QUERY
# ═══════════════════════════════════════════════════════════════════════════════


class TestBackfillEnvelopeQuery:

    def test_noop_when_query_already_set(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query="already set")
        ld = _make_loop_data("new content")
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "already set"

    def test_noop_when_envelope_is_none(self):
        hook = _make_hook()
        hook._backfill_envelope_query(None, _make_loop_data("anything"))

    def test_backfill_from_string_content(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data("Analyse stratégique de mon entreprise")
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Analyse stratégique de mon entreprise"

    def test_backfill_from_dict_raw_content(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data({"raw_content": "Étude de marché IA France"})
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Étude de marché IA France"

    def test_backfill_from_dict_user_message_key(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data({"user_message": "Pricing strategy B2B"})
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Pricing strategy B2B"

    def test_backfill_from_dict_text_key(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data({"text": "Due diligence complète"})
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Due diligence complète"

    def test_backfill_from_nested_dict(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data({
            "raw_content": {"user_message": "Analyse financière DCF"}
        })
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Analyse financière DCF"

    def test_backfill_from_list_content(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = _make_loop_data(["Partie 1", "Partie 2"])
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Partie 1 Partie 2"

    def test_backfill_truncates_to_2000(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        long_text = "x" * 5000
        ld = _make_loop_data(long_text)
        hook._backfill_envelope_query(envelope, ld)
        assert len(envelope.query) == 2000

    def test_backfill_from_last_user_message_fallback(self):
        hook = _make_hook()
        envelope = SessionEnvelope(query=None)
        ld = MagicMock()
        ld.user_message = None
        hook.agent.last_user_message = MagicMock()
        hook.agent.last_user_message.content = "Fallback query text"
        hook._backfill_envelope_query(envelope, ld)
        assert envelope.query == "Fallback query text"

    def test_backfill_query_produces_hash(self):
        """When query is backfilled, IntegrityBlock.from_session should produce a hash."""
        from python.helpers.integrity_block import IntegrityBlock
        query = "Test strategic query for hash"
        block = IntegrityBlock.from_session(
            query=query, response="test response", session_id="KRV-TEST"
        )
        assert block.hash_request is not None
        assert block.hash_request.startswith("sha256:")


# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN REVIEW FLAG
# ═══════════════════════════════════════════════════════════════════════════════


class TestHumanReviewFlag:

    def test_false_when_no_signals(self):
        hook = _make_hook()
        assert hook._resolve_human_review_flag() is False

    def test_true_from_legal_output(self):
        hook = _make_hook()
        legal_output = MagicMock()
        legal_output.safety.requires_human_review = True
        hook._stored["_legal_pipeline_output"] = legal_output
        assert hook._resolve_human_review_flag() is True

    def test_false_from_legal_output_no_review(self):
        hook = _make_hook()
        legal_output = MagicMock()
        legal_output.safety.requires_human_review = False
        hook._stored["_legal_pipeline_output"] = legal_output
        assert hook._resolve_human_review_flag() is False

    def test_true_from_metacognition_escalation(self):
        hook = _make_hook()
        hook._stored["_metacognition_escalation"] = True
        assert hook._resolve_human_review_flag() is True

    def test_true_from_explicit_flag(self):
        hook = _make_hook()
        hook._stored["_requires_human_review"] = True
        assert hook._resolve_human_review_flag() is True

    def test_non_blocking_on_error(self):
        hook = _make_hook()
        hook.agent.get_data = MagicMock(side_effect=RuntimeError("boom"))
        assert hook._resolve_human_review_flag() is False


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS FLAG
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsensusFlag:

    def test_false_when_no_signals(self):
        hook = _make_hook()
        assert hook._resolve_consensus_flag() is False

    def test_true_from_consensus_result(self):
        hook = _make_hook()
        hook._stored["_consensus_result"] = {
            "approved": True, "source": "adversarial_pipeline"
        }
        assert hook._resolve_consensus_flag() is True

    def test_true_from_prism_flag(self):
        hook = _make_hook()
        hook._stored["_prism_consensus_used"] = True
        assert hook._resolve_consensus_flag() is True

    def test_true_from_assessment_requires_consensus(self):
        hook = _make_hook()
        hook._stored["_consensus_assessment"] = {
            "requires_consensus": True, "domain": "legal"
        }
        assert hook._resolve_consensus_flag() is True

    def test_false_from_assessment_no_consensus(self):
        hook = _make_hook()
        hook._stored["_consensus_assessment"] = {
            "requires_consensus": False, "domain": "default"
        }
        assert hook._resolve_consensus_flag() is False

    def test_non_blocking_on_error(self):
        hook = _make_hook()
        hook.agent.get_data = MagicMock(side_effect=RuntimeError("boom"))
        assert hook._resolve_consensus_flag() is False
