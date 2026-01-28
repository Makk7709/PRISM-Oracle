"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             P6.2: NEEDLE TESTS FOR LEGAL DIFF SIGNAL OVERRIDE               ║
║                                                                              ║
║  Tests "needle in haystack": micro-mutations (1-2 mots) dans des phrases    ║
║  longues pour valider que le seuil 0.85 ne masque pas l'essentiel.          ║
║                                                                              ║
║  P6.2 INVARIANTS:                                                            ║
║  - Signal change = segment présent (no-signal-change-ignored)               ║
║  - Typo-only (après normalisation) = 0 segments                             ║
║  - Déterminisme: mêmes inputs → mêmes hash/segments                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
from datetime import date
from typing import List, Tuple


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


# ═══════════════════════════════════════════════════════════════════════════════
# LONG PHRASE TEMPLATES (≥25 words)
# ═══════════════════════════════════════════════════════════════════════════════

# Base phrase with "peut" that can be changed to "doit"
PHRASE_PEUT = (
    "Dans le cadre de l'application des dispositions prévues par le présent "
    "règlement, l'entreprise concernée peut transmettre les documents requis "
    "à l'autorité compétente dans un délai de trente jours calendaires."
)

# Same phrase with "doit"
PHRASE_DOIT = (
    "Dans le cadre de l'application des dispositions prévues par le présent "
    "règlement, l'entreprise concernée doit transmettre les documents requis "
    "à l'autorité compétente dans un délai de trente jours calendaires."
)

# Base phrase without "minimum"
PHRASE_NO_MINIMUM = (
    "Conformément aux articles susvisés du code applicable en la matière, "
    "le délai de préavis accordé aux parties prenantes est fixé à trente jours "
    "à compter de la notification officielle de la décision administrative."
)

# Same phrase with "minimum"
PHRASE_WITH_MINIMUM = (
    "Conformément aux articles susvisés du code applicable en la matière, "
    "le délai minimum de préavis accordé aux parties prenantes est fixé à trente jours "
    "à compter de la notification officielle de la décision administrative."
)

# Base phrase with "exemption"
PHRASE_WITH_EXEMPTION = (
    "Les dispositions du présent chapitre s'appliquent à toutes les entreprises "
    "du secteur concerné, à l'exception des petites structures qui bénéficient "
    "d'une exemption temporaire en raison de leur taille réduite."
)

# Same phrase without "exemption"
PHRASE_NO_EXEMPTION = (
    "Les dispositions du présent chapitre s'appliquent à toutes les entreprises "
    "du secteur concerné, y compris les petites structures qui doivent respecter "
    "les obligations prévues en raison de leur activité."
)

# Base phrase without sanction
PHRASE_NO_SANCTION = (
    "En cas de non-respect des délais impartis par la réglementation en vigueur, "
    "l'administration compétente procède à l'envoi d'un rappel officiel aux "
    "personnes concernées dans les meilleurs délais."
)

# Same phrase with sanction
PHRASE_WITH_SANCTION = (
    "En cas de non-respect des délais impartis par la réglementation en vigueur, "
    "l'administration compétente procède à l'application d'une sanction aux "
    "personnes concernées dans les meilleurs délais."
)

# Base phrase with "interdit"
PHRASE_INTERDIT = (
    "Selon les dispositions légales applicables au secteur d'activité concerné, "
    "la sous-traitance des prestations essentielles est strictement interdite "
    "sauf autorisation expresse délivrée par l'autorité de régulation."
)

# Same phrase with "autorisé"
PHRASE_AUTORISE = (
    "Selon les dispositions légales applicables au secteur d'activité concerné, "
    "la sous-traitance des prestations essentielles est désormais autorisée "
    "sauf interdiction expresse délivrée par l'autorité de régulation."
)


# ═══════════════════════════════════════════════════════════════════════════════
# NEEDLE TESTS: SIGNAL OVERRIDE (1-2 word changes that MUST be detected)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNeedlePeutToDoit:
    """Test peut→doit mutation in long phrase."""
    
    def test_peut_to_doit_detected(self):
        """peut→doit must be detected despite high similarity."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_PEUT,
            new_text=PHRASE_DOIT,
            text_id="NEEDLE_PEUT_DOIT",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1, (
            f"NEEDLE FAILURE: peut→doit not detected in long phrase. "
            f"Segments: {report.total_segments}"
        )
        assert report.aggravation_detected, (
            f"NEEDLE FAILURE: peut→doit should be AGGRAVATING. "
            f"Segments: {[s.to_dict() for s in report.segments]}"
        )
    
    def test_doit_to_peut_detected(self):
        """doit→peut must be detected despite high similarity."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_DOIT,
            new_text=PHRASE_PEUT,
            text_id="NEEDLE_DOIT_PEUT",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.relaxation_detected, (
            f"doit→peut should be RELAXING"
        )


class TestNeedleMinimum:
    """Test +minimum mutation in long phrase."""
    
    def test_add_minimum_detected(self):
        """Adding 'minimum' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_NO_MINIMUM,
            new_text=PHRASE_WITH_MINIMUM,
            text_id="NEEDLE_ADD_MINIMUM",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1, (
            f"NEEDLE FAILURE: +minimum not detected"
        )
        assert report.aggravation_detected
    
    def test_remove_minimum_detected(self):
        """Removing 'minimum' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_WITH_MINIMUM,
            new_text=PHRASE_NO_MINIMUM,
            text_id="NEEDLE_REMOVE_MINIMUM",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.relaxation_detected


class TestNeedleExemption:
    """Test exemption mutation in long phrase."""
    
    def test_remove_exemption_detected(self):
        """Removing 'exemption' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_WITH_EXEMPTION,
            new_text=PHRASE_NO_EXEMPTION,
            text_id="NEEDLE_REMOVE_EXEMPTION",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1, (
            f"NEEDLE FAILURE: -exemption not detected"
        )
        # Note: removing exemption + adding "doit" = aggravating
        assert report.aggravation_detected
    
    def test_add_exemption_detected(self):
        """Adding 'exemption' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_NO_EXEMPTION,
            new_text=PHRASE_WITH_EXEMPTION,
            text_id="NEEDLE_ADD_EXEMPTION",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.relaxation_detected


class TestNeedleSanction:
    """Test sanction mutation in long phrase."""
    
    def test_add_sanction_detected(self):
        """Adding 'sanction' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_NO_SANCTION,
            new_text=PHRASE_WITH_SANCTION,
            text_id="NEEDLE_ADD_SANCTION",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.aggravation_detected
    
    def test_remove_sanction_detected(self):
        """Removing 'sanction' must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_WITH_SANCTION,
            new_text=PHRASE_NO_SANCTION,
            text_id="NEEDLE_REMOVE_SANCTION",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.relaxation_detected


class TestNeedleInterditAutorise:
    """Test interdit→autorisé mutation in long phrase."""
    
    def test_interdit_to_autorise_detected(self):
        """interdit→autorisé must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_INTERDIT,
            new_text=PHRASE_AUTORISE,
            text_id="NEEDLE_INTERDIT_AUTORISE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.relaxation_detected
    
    def test_autorise_to_interdit_detected(self):
        """autorisé→interdit must be detected."""
        from python.helpers.legal_diff import compute_legal_diff
        
        report = compute_legal_diff(
            old_text=PHRASE_AUTORISE,
            new_text=PHRASE_INTERDIT,
            text_id="NEEDLE_AUTORISE_INTERDIT",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments >= 1
        assert report.aggravation_detected


# ═══════════════════════════════════════════════════════════════════════════════
# TYPO-ONLY TESTS (P6.2.1 normalization → 0 segments)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypoOnlyNormalization:
    """Test that typography-only changes result in 0 segments after normalization."""
    
    def test_apostrophe_curly_to_straight(self):
        """Curly apostrophe → straight should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "L'entreprise fournit les documents à l'administration."
        variant = "L'entreprise fournit les documents à l'administration."  # curly '
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_APOSTROPHE",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0, (
            f"TYPO-ONLY FAILURE: apostrophe variation produced {report.total_segments} segments"
        )
    
    def test_en_dash_to_hyphen(self):
        """En-dash → hyphen should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Le contrat - signé par les parties - est valide."
        variant = "Le contrat – signé par les parties – est valide."  # en-dash
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_DASH",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
    
    def test_nbsp_to_space(self):
        """NBSP → space should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1. Le délai est de 30 jours."
        variant = "Article\u00a01.\u00a0Le délai est de 30\u00a0jours."  # NBSP
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_NBSP",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
    
    def test_multiple_spaces(self):
        """Multiple spaces should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1. Le délai est de 30 jours."
        variant = "Article  1.  Le  délai  est  de  30  jours."  # double spaces
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_SPACES",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
    
    def test_crlf_to_lf(self):
        """CRLF → LF should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "Article 1.\nArticle 2."
        variant = "Article 1.\r\nArticle 2."  # CRLF
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_CRLF",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0
    
    def test_combined_typo_variations(self):
        """Multiple typo variations combined should be 0 segments."""
        from python.helpers.legal_diff import compute_legal_diff
        
        original = "L'entreprise - ou son mandataire - fournit les documents."
        # curly apostrophe + en-dash + NBSP
        variant = "L'entreprise\u00a0–\u00a0ou son mandataire\u00a0–\u00a0fournit les documents."
        
        report = compute_legal_diff(
            old_text=original,
            new_text=variant,
            text_id="TYPO_COMBINED",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report.total_segments == 0


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISM TESTS (P6.2: normalized hash stability)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterminismWithNormalization:
    """Test hash determinism with typography variations."""
    
    def test_same_hash_after_normalization(self):
        """Texts that normalize to same content should have same diff_hash."""
        from python.helpers.legal_diff import compute_legal_diff
        
        text_v1 = "L'entreprise fournit les documents."
        text_v2 = "L'entreprise transmet les pièces."
        
        # Different typography for same semantic content
        text_v1_typo = "L'entreprise fournit les documents."  # curly '
        text_v2_typo = "L'entreprise transmet les pièces."  # curly '
        
        report_original = compute_legal_diff(
            old_text=text_v1,
            new_text=text_v2,
            text_id="HASH_TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        report_typo = compute_legal_diff(
            old_text=text_v1_typo,
            new_text=text_v2_typo,
            text_id="HASH_TEST",
            from_version_id="v1",
            to_version_id="v2",
            as_of_date=date(2024, 1, 1),
        )
        
        assert report_original.diff_hash == report_typo.diff_hash, (
            f"Hash mismatch after normalization: "
            f"{report_original.diff_hash} != {report_typo.diff_hash}"
        )
    
    def test_10_runs_determinism(self):
        """10 runs should produce identical results."""
        from python.helpers.legal_diff import compute_legal_diff
        
        results = []
        for _ in range(10):
            report = compute_legal_diff(
                old_text=PHRASE_PEUT,
                new_text=PHRASE_DOIT,
                text_id="DETERMINISM",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            results.append((
                report.diff_hash,
                tuple(s.segment_id for s in report.segments),
                tuple(s.qualification.value for s in report.segments),
            ))
        
        first = results[0]
        for i, result in enumerate(results[1:], 2):
            assert result == first, (
                f"Determinism failed at run {i}: {result} != {first}"
            )
    
    def test_segment_ids_deterministic(self):
        """Segment IDs should be deterministic."""
        from python.helpers.legal_diff import compute_legal_diff
        
        ids_sets = []
        for _ in range(5):
            report = compute_legal_diff(
                old_text=PHRASE_PEUT,
                new_text=PHRASE_DOIT,
                text_id="DETERMINISM",
                from_version_id="v1",
                to_version_id="v2",
                as_of_date=date(2024, 1, 1),
            )
            ids_sets.append(tuple(s.segment_id for s in report.segments))
        
        assert len(set(ids_sets)) == 1, f"Segment IDs not deterministic: {ids_sets}"


# ═══════════════════════════════════════════════════════════════════════════════
# P6.2.2 SIGNAL OVERRIDE INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignalOverrideInvariant:
    """Test the no-signal-change-ignored invariant."""
    
    def test_should_force_diff_on_signal_add(self):
        """should_force_diff returns True when signal added."""
        from python.helpers.legal_diff import should_force_diff
        
        before = "L'entreprise transmet les documents."
        after = "L'entreprise doit transmettre les documents."
        
        assert should_force_diff(before, after), (
            "should_force_diff should return True when 'doit' added"
        )
    
    def test_should_force_diff_on_signal_remove(self):
        """should_force_diff returns True when signal removed."""
        from python.helpers.legal_diff import should_force_diff
        
        before = "L'entreprise peut transmettre."
        after = "L'entreprise transmet."
        
        assert should_force_diff(before, after), (
            "should_force_diff should return True when 'peut' removed"
        )
    
    def test_should_force_diff_false_on_no_signal_change(self):
        """should_force_diff returns False when no signal changed."""
        from python.helpers.legal_diff import should_force_diff
        
        before = "L'entreprise transmet les documents."
        after = "L'entreprise envoie les pièces."
        
        assert not should_force_diff(before, after), (
            "should_force_diff should return False when no signals changed"
        )
    
    def test_extract_signals_case_insensitive(self):
        """extract_normative_signals is case-insensitive."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals_lower = extract_normative_signals("l'entreprise doit fournir")
        signals_upper = extract_normative_signals("L'ENTREPRISE DOIT FOURNIR")
        
        assert "doit" in signals_lower
        assert "doit" in signals_upper
    
    def test_signal_change_implies_segment(self):
        """If signals change, there must be a segment."""
        from python.helpers.legal_diff import (
            compute_legal_diff, 
            should_force_diff,
        )
        
        # Test pairs where signals change
        pairs = [
            ("L'entreprise transmet.", "L'entreprise doit transmettre."),
            ("Obligatoire pour tous.", "Facultatif pour tous."),
            ("Interdit de procéder.", "Autorisé à procéder."),
        ]
        
        for before, after in pairs:
            if should_force_diff(before, after):
                report = compute_legal_diff(
                    old_text=before,
                    new_text=after,
                    text_id="INVARIANT_TEST",
                    from_version_id="v1",
                    to_version_id="v2",
                    as_of_date=date(2024, 1, 1),
                )
                
                assert report.total_segments >= 1, (
                    f"INVARIANT VIOLATION: signal changed but no segment. "
                    f"Before: {before}, After: {after}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# P6.2.3 INFLECTED FORMS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInflectedForms:
    """Test detection of inflected forms (P6.2.3)."""
    
    def test_autorisee_detected(self):
        """'autorisée' (feminine) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("La pratique est autorisée.")
        assert "autorisée" in signals or "autorisé" in signals
    
    def test_exemptees_detected(self):
        """'exemptées' (feminine plural) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("Les entreprises sont exemptées.")
        assert any("exempt" in s for s in signals)
    
    def test_obligatoires_detected(self):
        """'obligatoires' (plural) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("Les déclarations obligatoires.")
        assert "obligatoires" in signals or "obligatoire" in signals
    
    def test_interdites_detected(self):
        """'interdites' (feminine plural) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("Les pratiques interdites.")
        assert any("interdit" in s for s in signals)
    
    def test_peuvent_detected(self):
        """'peuvent' (plural) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("Les parties peuvent résilier.")
        assert "peuvent" in signals
    
    def test_doivent_detected(self):
        """'doivent' (plural) should be detected."""
        from python.helpers.legal_diff import extract_normative_signals
        
        signals = extract_normative_signals("Les parties doivent respecter.")
        assert "doivent" in signals


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeLegalText:
    """Unit tests for normalize_legal_text function."""
    
    def test_empty_string(self):
        """Empty string returns empty string."""
        from python.helpers.legal_diff import normalize_legal_text
        
        assert normalize_legal_text("") == ""
    
    def test_apostrophe_normalization(self):
        """Curly apostrophes are normalized."""
        from python.helpers.legal_diff import normalize_legal_text
        
        # U+2019 RIGHT SINGLE QUOTATION MARK (curly apostrophe)
        input_text = "L\u2019entreprise"
        result = normalize_legal_text(input_text)
        assert "'" in result  # straight apostrophe U+0027
        assert "\u2019" not in result  # no curly U+2019
    
    def test_dash_normalization(self):
        """En/em dashes are normalized to hyphen."""
        from python.helpers.legal_diff import normalize_legal_text
        
        result = normalize_legal_text("test–dash—em")
        assert "–" not in result
        assert "—" not in result
        assert "-" in result
    
    def test_nbsp_normalization(self):
        """NBSP is normalized to space."""
        from python.helpers.legal_diff import normalize_legal_text
        
        result = normalize_legal_text("test\u00a0value")
        assert "\u00a0" not in result
        assert " " in result
    
    def test_space_collapse(self):
        """Multiple spaces are collapsed."""
        from python.helpers.legal_diff import normalize_legal_text
        
        result = normalize_legal_text("test   multiple   spaces")
        assert "   " not in result
        assert result == "test multiple spaces"
    
    def test_crlf_normalization(self):
        """CRLF is normalized to LF."""
        from python.helpers.legal_diff import normalize_legal_text
        
        result = normalize_legal_text("line1\r\nline2")
        assert "\r" not in result
        assert result == "line1\nline2"
    
    def test_preserves_case(self):
        """Case is preserved."""
        from python.helpers.legal_diff import normalize_legal_text
        
        result = normalize_legal_text("Article IMPORTANT Test")
        assert "IMPORTANT" in result


# ═══════════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
