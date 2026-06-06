"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            P6.1-VERIFY: FUZZ TYPOGRAPHY TESTS FOR LEGAL DIFF                ║
║                                                                              ║
║  Tests de robustesse aux variations typographiques.                         ║
║  Les changements purement cosmétiques ne doivent PAS déclencher:            ║
║  - aggravation_detected                                                      ║
║  - relaxation_detected                                                       ║
║                                                                              ║
║  Variations testées:                                                         ║
║  - Apostrophes: ' vs '                                                       ║
║  - Tirets: - vs – vs —                                                       ║
║  - Espaces multiples, insécables                                            ║
║  - Numérotation: 1°, 1., I.                                                 ║
║  - Casse mineure                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date
from typing import Callable, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# NIGHTLY MARKER
# ═══════════════════════════════════════════════════════════════════════════════

nightly = pytest.mark.skipif(
    os.environ.get("CI_NIGHTLY", "0") != "1",
    reason="Nightly-only fuzz test (set CI_NIGHTLY=1 to run)"
)


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


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY VARIANT GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def variant_apostrophe_straight(text: str) -> str:
    """Replace curly apostrophe with straight."""
    return text.replace("'", "'")


def variant_apostrophe_curly(text: str) -> str:
    """Replace straight apostrophe with curly."""
    return text.replace("'", "'")


def variant_dash_hyphen(text: str) -> str:
    """Replace en-dash/em-dash with hyphen."""
    return text.replace("–", "-").replace("—", "-")


def variant_dash_en(text: str) -> str:
    """Replace hyphen with en-dash."""
    return text.replace("-", "–")


def variant_dash_em(text: str) -> str:
    """Replace hyphen with em-dash."""
    return text.replace("-", "—")


def variant_multiple_spaces(text: str) -> str:
    """Add multiple spaces."""
    return text.replace(" ", "  ")


def variant_trim_spaces(text: str) -> str:
    """Normalize multiple spaces to single."""
    import re
    return re.sub(r" +", " ", text)


def variant_nbsp(text: str) -> str:
    """Replace some spaces with non-breaking spaces."""
    # Replace every 3rd space with nbsp
    chars = list(text)
    count = 0
    for i, c in enumerate(chars):
        if c == " ":
            count += 1
            if count % 3 == 0:
                chars[i] = "\u00a0"  # NBSP
    return "".join(chars)


def variant_numbering_dot(text: str) -> str:
    """Convert Article 1° to Article 1."""
    import re
    return re.sub(r"(\d)°", r"\1.", text)


def variant_numbering_degree(text: str) -> str:
    """Convert Article 1. to Article 1°"""
    import re
    # Only at word boundaries after Article/Section etc
    return re.sub(r"(Article|Section)\s+(\d+)\.", r"\1 \2°", text)


def variant_lowercase_article(text: str) -> str:
    """Convert Article to article."""
    return text.replace("Article", "article")


def variant_uppercase_article(text: str) -> str:
    """Convert article to ARTICLE."""
    return text.replace("Article", "ARTICLE").replace("article", "ARTICLE")


# All typography variants
TYPOGRAPHY_VARIANTS: List[Tuple[str, Callable[[str], str]]] = [
    ("apostrophe_straight", variant_apostrophe_straight),
    ("apostrophe_curly", variant_apostrophe_curly),
    ("dash_hyphen", variant_dash_hyphen),
    ("dash_en", variant_dash_en),
    ("dash_em", variant_dash_em),
    ("multiple_spaces", variant_multiple_spaces),
    ("trim_spaces", variant_trim_spaces),
    ("nbsp", variant_nbsp),
    ("numbering_dot", variant_numbering_dot),
    ("numbering_degree", variant_numbering_degree),
    ("lowercase_article", variant_lowercase_article),
    ("uppercase_article", variant_uppercase_article),
]


# ═══════════════════════════════════════════════════════════════════════════════
# BASE TEXTS FOR FUZZ TESTING
# ═══════════════════════════════════════════════════════════════════════════════

# Neutral text without normative keywords
BASE_TEXT_NEUTRAL = """Article 1° L'entreprise transmet les documents requis.
Article 2° Le délai de transmission est de trente jours.
Article 3° Les modalités sont précisées par décret."""

# Text with apostrophes and dashes
BASE_TEXT_PUNCTUATION = """Article 1. L'utilisateur — ou son représentant — fournit les pièces.
Article 2. Le délai d'examen est fixé par l'administration.
Article 3. La demande n'est recevable qu'après validation."""


# ═══════════════════════════════════════════════════════════════════════════════
# FUZZ TESTS - FAST (subset for CI)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypographyFuzzFast:
    """Fast typography fuzz tests for CI gate."""
    
    def test_apostrophe_variation_no_impact(self):
        """Apostrophe variations should not trigger normative impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "L'entreprise fournit les documents."
        variant = "L'entreprise fournit les documents."  # curly apostrophe
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_APOSTROPHE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected, (
            f"Apostrophe variation triggered aggravation. "
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
        assert not report.relaxation_detected, (
            f"Apostrophe variation triggered relaxation. "
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
    
    def test_dash_variation_no_impact(self):
        """Dash variations should not trigger normative impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Le contrat - signé par les parties - est valide."
        variant = "Le contrat – signé par les parties – est valide."  # en-dash
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_DASH",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected
    
    def test_whitespace_variation_no_impact(self):
        """Whitespace variations should not trigger normative impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1. Le délai est de 30 jours."
        variant = "Article 1.  Le  délai  est  de  30  jours."  # double spaces
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_WHITESPACE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected
    
    def test_numbering_variation_no_impact(self):
        """Numbering format variations should not trigger normative impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1° Le contrat est valable."
        variant = "Article 1. Le contrat est valable."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_NUMBERING",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected
    
    def test_case_variation_no_impact(self):
        """Case variations on non-normative words should not trigger impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1. Le délai est fixé."
        variant = "ARTICLE 1. Le délai est fixé."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_CASE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected


# ═══════════════════════════════════════════════════════════════════════════════
# FUZZ TESTS - NIGHTLY (comprehensive)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypographyFuzzNightly:
    """Comprehensive typography fuzz tests for nightly CI."""
    
    @nightly
    @pytest.mark.parametrize("variant_name,variant_fn", TYPOGRAPHY_VARIANTS)
    def test_variant_on_neutral_text(self, variant_name: str, variant_fn: Callable):
        """Typography variant on neutral text should not trigger impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = BASE_TEXT_NEUTRAL
        variant = variant_fn(original)
        
        # Skip if variant is identical (transformation had no effect)
        if original == variant:
            pytest.skip(f"Variant {variant_name} produced identical text")
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id=f"FUZZ_{variant_name.upper()}",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected, (
            f"Variant '{variant_name}' on neutral text triggered aggravation.\n"
            f"Original: {original[:100]}...\n"
            f"Variant: {variant[:100]}...\n"
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
        assert not report.relaxation_detected, (
            f"Variant '{variant_name}' on neutral text triggered relaxation.\n"
            f"Original: {original[:100]}...\n"
            f"Variant: {variant[:100]}...\n"
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
    
    @nightly
    @pytest.mark.parametrize("variant_name,variant_fn", TYPOGRAPHY_VARIANTS)
    def test_variant_on_punctuation_text(self, variant_name: str, variant_fn: Callable):
        """Typography variant on punctuation-rich text should not trigger impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = BASE_TEXT_PUNCTUATION
        variant = variant_fn(original)
        
        if original == variant:
            pytest.skip(f"Variant {variant_name} produced identical text")
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id=f"FUZZ_PUNCT_{variant_name.upper()}",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected, (
            f"Variant '{variant_name}' triggered aggravation on punctuation text"
        )
        assert not report.relaxation_detected, (
            f"Variant '{variant_name}' triggered relaxation on punctuation text"
        )
    
    @nightly
    def test_combined_variants_no_impact(self):
        """Multiple typography variants combined should not trigger impact."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = BASE_TEXT_NEUTRAL
        
        # Apply multiple variants
        variant = original
        variant = variant_apostrophe_curly(variant)
        variant = variant_dash_en(variant)
        variant = variant_multiple_spaces(variant)
        variant = variant_lowercase_article(variant)
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="FUZZ_COMBINED",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY + NORMATIVE COMBINATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypographyWithNormative:
    """
    Tests that typography changes don't mask or create false normative signals.
    """
    
    def test_typography_doesnt_mask_aggravation(self):
        """Real aggravation should still be detected despite typography changes."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "L'entreprise peut fournir un rapport."
        # Add typography changes + real normative change
        variant = "L'entreprise doit obligatoirement fournir un rapport."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_MASK_TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.aggravation_detected, (
            "Real aggravation was masked by typography. "
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
    
    def test_typography_doesnt_mask_relaxation(self):
        """Real relaxation should still be detected despite typography changes."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Le délai est de 30 jours."
        variant = "Le délai peut être prolongé jusqu'à 60 jours."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_MASK_RELAX",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.relaxation_detected, (
            "Real relaxation was masked. "
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
    
    def test_typography_doesnt_create_false_aggravation(self):
        """Typography changes shouldn't create false aggravation signals."""
        from python.helpers.legal_diff import compute_legal_diff
        
        # Text with "doit" that stays unchanged
        original = "L'entreprise doit fournir un rapport."
        variant = "L'entreprise doit fournir un rapport."  # curly apostrophe only
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_FALSE_AGG",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        # "doit" is present in both, should not trigger aggravation
        assert not report.aggravation_detected, (
            "Typography-only change created false aggravation"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypographyEdgeCases:
    """Edge cases for typography handling."""
    
    def test_empty_after_normalization(self):
        """Texts that become identical after normalization."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "  Article 1.  Test.  "
        variant = "Article 1. Test."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="EDGE_EMPTY_NORM",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        # Should produce 0 segments since stripping makes them equal
        assert report.total_segments == 0
    
    def test_unicode_normalization(self):
        """Unicode normalization edge case (é vs é composed)."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Le délai est de 30 jours."  # precomposed é
        variant = "Le délai est de 30 jours."  # could be decomposed
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="EDGE_UNICODE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert not report.aggravation_detected
        assert not report.relaxation_detected


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
