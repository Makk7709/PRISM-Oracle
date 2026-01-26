"""
Tests for Router Determinism — Verify strict deterministic behavior.

Same input MUST produce same output:
- Same route_id (sha256-based)
- Same input_hash (sha256-based)
- Same intents (sorted deterministically)
- Same verdict
- Same confidence
"""

import pytest

from python.helpers.router import (
    decide_route,
    _canonicalize_text,
    _stable_route_id,
    _stable_input_hash,
    RouteDecision,
)


class TestCanonicalizeText:
    """Test text canonicalization for deterministic hashing."""
    
    def test_lowercase(self):
        """Text should be lowercased."""
        assert _canonicalize_text("HELLO World") == "hello world"
    
    def test_strip_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        assert _canonicalize_text("  hello world  ") == "hello world"
    
    def test_collapse_whitespace(self):
        """Multiple whitespace should collapse to single space."""
        assert _canonicalize_text("hello   world") == "hello world"
        assert _canonicalize_text("hello\t\nworld") == "hello world"
        assert _canonicalize_text("hello  \n  world") == "hello world"
    
    def test_combined_normalization(self):
        """All normalizations should apply together."""
        text = "  HELLO   \n  WORLD  "
        assert _canonicalize_text(text) == "hello world"


class TestStableHashes:
    """Test that hashes are stable and deterministic."""
    
    def test_route_id_deterministic(self):
        """Same canonical text should produce same route_id."""
        text = "analyse financière"
        id1 = _stable_route_id(text)
        id2 = _stable_route_id(text)
        id3 = _stable_route_id(text)
        
        assert id1 == id2 == id3
        assert len(id1) == 8  # SHA256[:8]
    
    def test_input_hash_deterministic(self):
        """Same canonical text should produce same input_hash."""
        text = "analyse financière"
        h1 = _stable_input_hash(text)
        h2 = _stable_input_hash(text)
        h3 = _stable_input_hash(text)
        
        assert h1 == h2 == h3
        assert len(h1) == 12  # SHA256[:12]
    
    def test_different_text_different_hashes(self):
        """Different text should produce different hashes."""
        text1 = "analyse financière"
        text2 = "analyse juridique"
        
        assert _stable_route_id(text1) != _stable_route_id(text2)
        assert _stable_input_hash(text1) != _stable_input_hash(text2)


class TestDecideRouteDeterminism:
    """Test that decide_route is fully deterministic."""
    
    def test_same_input_same_output(self):
        """Same input text should produce identical decisions."""
        text = "Analyse DCF de l'entreprise avec risques juridiques"
        
        decisions = [decide_route(text) for _ in range(10)]
        
        # All route_ids should be identical
        route_ids = [d.route_id for d in decisions]
        assert len(set(route_ids)) == 1, f"Non-deterministic route_id: {set(route_ids)}"
        
        # All input_hashes should be identical
        input_hashes = [d.input_hash for d in decisions]
        assert len(set(input_hashes)) == 1, f"Non-deterministic input_hash: {set(input_hashes)}"
        
        # All verdicts should be identical
        verdicts = [d.verdict for d in decisions]
        assert len(set(verdicts)) == 1
        
        # All intent lists should be identical (same names, same order)
        intent_tuples = [
            tuple((i.name.value, round(i.score, 3)) for i in d.intents)
            for d in decisions
        ]
        assert len(set(intent_tuples)) == 1, f"Non-deterministic intents: {set(intent_tuples)}"
    
    def test_whitespace_variations_same_result(self):
        """Whitespace variations should produce same result."""
        text1 = "Analyse financière"
        text2 = "  Analyse   financière  "
        text3 = "Analyse\n\tfinancière"
        
        d1 = decide_route(text1)
        d2 = decide_route(text2)
        d3 = decide_route(text3)
        
        # All should have same route_id due to canonicalization
        assert d1.route_id == d2.route_id == d3.route_id
        assert d1.input_hash == d2.input_hash == d3.input_hash
    
    def test_case_variations_same_result(self):
        """Case variations should produce same result."""
        text1 = "analyse financière"
        text2 = "ANALYSE FINANCIÈRE"
        text3 = "AnAlYsE fInAnCiÈrE"
        
        d1 = decide_route(text1)
        d2 = decide_route(text2)
        d3 = decide_route(text3)
        
        assert d1.route_id == d2.route_id == d3.route_id
    
    def test_intent_order_deterministic(self):
        """Intents should always be in same order."""
        text = "Analyse financière juridique commerciale"
        
        decisions = [decide_route(text) for _ in range(20)]
        
        intent_orders = [
            tuple(i.name.value for i in d.intents)
            for d in decisions
        ]
        
        assert len(set(intent_orders)) == 1, \
            f"Non-deterministic intent order: {set(intent_orders)}"
    
    def test_compute_hash_stable(self):
        """RouteDecision.compute_hash() should be stable."""
        text = "Analyse DCF"
        
        decisions = [decide_route(text) for _ in range(10)]
        hashes = [d.compute_hash() for d in decisions]
        
        assert len(set(hashes)) == 1, f"Non-deterministic compute_hash: {set(hashes)}"
    
    def test_no_uuid_in_route_id(self):
        """route_id should not use uuid (which is random)."""
        text = "Test prompt"
        
        d1 = decide_route(text)
        d2 = decide_route(text)
        
        # If uuid was used, these would be different
        assert d1.route_id == d2.route_id
        
        # route_id should be hex (from sha256)
        assert all(c in '0123456789abcdef' for c in d1.route_id)


class TestDeterminismEdgeCases:
    """Test determinism in edge cases."""
    
    def test_empty_string_deterministic(self):
        """Empty string should produce deterministic result."""
        decisions = [decide_route("") for _ in range(5)]
        
        route_ids = [d.route_id for d in decisions]
        assert len(set(route_ids)) == 1
    
    def test_unicode_deterministic(self):
        """Unicode characters should not break determinism."""
        text = "Analyse financière avec émojis 📊💰 et accents éèàù"
        
        decisions = [decide_route(text) for _ in range(5)]
        
        route_ids = [d.route_id for d in decisions]
        assert len(set(route_ids)) == 1
    
    def test_long_text_deterministic(self):
        """Long text should remain deterministic."""
        text = "Analyse financière " * 100
        
        decisions = [decide_route(text) for _ in range(5)]
        
        route_ids = [d.route_id for d in decisions]
        assert len(set(route_ids)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
