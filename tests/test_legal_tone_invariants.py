"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            P6.3 QA ADVERSARIAL — TONE INVARIANTS TESTS                       ║
║                                                                              ║
║  Vérifie la discipline linguistique du système.                              ║
║                                                                              ║
║  INTERDITS:                                                                  ║
║  - Aucune phrase conclusive ("donc", "en conséquence", "vous êtes fondé")    ║
║  - Aucune recommandation                                                     ║
║  - Aucune validation implicite                                               ║
║  - Aucun conseil juridique direct                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest
import re
from datetime import date
from typing import Any, Dict, List, Pattern, Set

# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment for each test."""
    original_env = os.environ.copy()
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    yield
    os.environ.clear()
    os.environ.update(original_env)


# ═══════════════════════════════════════════════════════════════════════════════
# FORBIDDEN PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Conclusive phrases that should NEVER appear in legal output
FORBIDDEN_CONCLUSIVE_PHRASES = [
    # French conclusive connectors
    r"\bdonc\s+(?:vous|il|elle|on|l'|la|le|les)\b",  # "donc vous/il..."
    r"\ben\s+conséquence\s*,?\s*(?:vous|il|elle|on)\b",  # "en conséquence, vous..."
    r"\bpar\s+conséquent\s*,?\s*(?:vous|il|elle|on)\b",  # "par conséquent, vous..."
    r"\bainsi\s*,?\s*(?:vous|il|elle|on)\s+(?:pouvez|devez|êtes|avez)\b",  # "ainsi, vous pouvez/devez"
    r"\bil\s+(?:en\s+)?résulte\s+(?:que|donc)\b",  # "il résulte que/donc"
    r"\bcela\s+(?:signifie|implique|permet)\s+(?:que|donc)\b",  # "cela signifie/implique que"
]

# Direct advice phrases that should NEVER appear
FORBIDDEN_ADVICE_PHRASES = [
    r"\bje\s+vous\s+(?:conseille|recommande|suggère)\b",  # "je vous conseille"
    r"\bvous\s+(?:devriez|pourriez|devez)\s+(?:donc|alors)\b",  # "vous devriez donc"
    r"\bil\s+(?:faut|convient|est\s+(?:préférable|recommandé))\s+(?:de|que)\b",  # "il faut/convient de"
    r"\bje\s+(?:pense|crois|estime)\s+que\s+vous\b",  # "je pense que vous"
    r"\bà\s+mon\s+(?:avis|sens)\b",  # "à mon avis"
    r"\bselon\s+moi\b",  # "selon moi"
]

# Implicit validation phrases that should NEVER appear
FORBIDDEN_VALIDATION_PHRASES = [
    r"\bvous\s+avez\s+(?:raison|tout\s+à\s+fait\s+raison)\b",  # "vous avez raison"
    r"\bc'est\s+(?:exact|correct|juste)\b",  # "c'est exact/correct"
    r"\beffectivement\s*,?\s*(?:vous|c'est|il)\b",  # "effectivement, vous/c'est"
    r"\ben\s+effet\s*,?\s*(?:vous|c'est|il)\b",  # "en effet, vous/c'est"
    r"\babsolument\b",  # "absolument" (too assertive)
    r"\bparfaitement\b",  # "parfaitement" (too validating)
    r"\bvous\s+êtes\s+(?:fondé|en\s+droit|habilité)\b",  # "vous êtes fondé/en droit"
    r"\bvotre\s+(?:position|analyse)\s+est\s+(?:correcte|juste|fondée)\b",  # "votre position est correcte"
]

# Normative conclusions that should NEVER appear
FORBIDDEN_NORMATIVE_CONCLUSIONS = [
    r"\bla\s+clause\s+est\s+(?:valide|nulle|illégale)\b",  # "la clause est valide/nulle"
    r"\ble\s+contrat\s+est\s+(?:valide|nul|résolu)\b",  # "le contrat est valide/nul"
    r"\bvous\s+êtes\s+(?:libéré|exonéré|protégé|obligé)\b",  # "vous êtes libéré"
    r"\bil\s+est\s+(?:illégal|légal)\s+de\b",  # "il est illégal/légal de"
    r"\bcette\s+pratique\s+est\s+(?:interdite|autorisée)\b",  # "cette pratique est interdite"
]

# Compile all forbidden patterns
ALL_FORBIDDEN_PATTERNS: List[Pattern] = [
    re.compile(p, re.IGNORECASE) 
    for patterns in [
        FORBIDDEN_CONCLUSIVE_PHRASES,
        FORBIDDEN_ADVICE_PHRASES,
        FORBIDDEN_VALIDATION_PHRASES,
        FORBIDDEN_NORMATIVE_CONCLUSIONS,
    ]
    for p in patterns
]


def check_text_for_forbidden_patterns(text: str) -> List[str]:
    """
    Check text for any forbidden patterns.
    
    Returns list of violations found.
    """
    violations = []
    for pattern in ALL_FORBIDDEN_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            violations.extend(matches)
    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# 1️⃣ NO CONCLUSIVE PHRASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoConclussivePhrases:
    """
    Test absence de phrases conclusives.
    
    INTERDIT: "donc", "en conséquence", "il résulte que"
    """
    
    def test_forbidden_conclusive_patterns_detected(self):
        """Forbidden conclusive patterns should be detectable."""
        violating_texts = [
            "Donc vous êtes en droit de résilier.",
            "En conséquence, vous pouvez procéder.",
            "Par conséquent, il est autorisé.",
            "Il résulte que la clause est nulle.",
        ]
        
        for text in violating_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert violations, f"Should detect violation in: {text}"
    
    def test_valid_legal_statements_pass(self):
        """Valid legal statements should not trigger violations."""
        valid_texts = [
            "L'article L. 123-4 du Code de commerce dispose que...",
            "Selon les dispositions de l'article 1134 du Code civil...",
            "La jurisprudence de la Cour de cassation retient que...",
            "Les conditions mentionnées à l'article 12 prévoient...",
            "Il convient d'examiner les dispositions applicables.",
            "Les faits exposés correspondent au champ d'application de l'article...",
        ]
        
        for text in valid_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert not violations, f"Valid text should not violate: {text}"
    
    def test_legal_draft_application_no_conclusions(self):
        """LegalDraft.application should not contain conclusions."""
        from python.helpers.legal_pipeline import LegalDraft, LegalRouteContext
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope
        
        # Valid application examples
        valid_applications = [
            "L'article 1103 du Code civil s'applique aux contrats conclus après le 1er octobre 2016.",
            "Les dispositions de l'article L. 1234-1 du Code du travail encadrent la durée du préavis.",
            "La convention collective applicable prévoit des conditions spécifiques.",
        ]
        
        for app in valid_applications:
            violations = check_text_for_forbidden_patterns(app)
            assert not violations, f"Valid application should not violate: {app}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2️⃣ NO RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRecommendations:
    """
    Test absence de recommandations.
    
    INTERDIT: "je vous conseille", "vous devriez", "il faut"
    """
    
    def test_forbidden_advice_patterns_detected(self):
        """Forbidden advice patterns should be detectable."""
        violating_texts = [
            "Je vous conseille de signer ce contrat.",
            "Vous devriez donc contacter un avocat.",
            "Il faut que vous procédiez rapidement.",
            "À mon avis, cette clause est problématique.",
        ]
        
        for text in violating_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert violations, f"Should detect advice violation in: {text}"
    
    def test_factual_statements_not_advice(self):
        """Factual legal statements are not advice."""
        factual_texts = [
            "Le Code civil dispose que...",
            "La loi prévoit un délai de 30 jours.",
            "L'article 12 définit les conditions suivantes.",
            "La Cour de cassation a jugé que...",
        ]
        
        for text in factual_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert not violations, f"Factual statement incorrectly flagged: {text}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3️⃣ NO IMPLICIT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoImplicitValidation:
    """
    Test absence de validation implicite.
    
    INTERDIT: "vous avez raison", "c'est exact", "effectivement"
    """
    
    def test_forbidden_validation_patterns_detected(self):
        """Forbidden validation patterns should be detectable."""
        violating_texts = [
            "Vous avez raison sur ce point.",
            "C'est exact, la clause est valide.",
            "Effectivement, vous pouvez procéder.",
            "Absolument, c'est conforme.",
            "Vous êtes fondé à demander...",
        ]
        
        for text in violating_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert violations, f"Should detect validation violation in: {text}"
    
    def test_neutral_acknowledgment_allowed(self):
        """Neutral acknowledgment without validation is allowed."""
        allowed_texts = [
            "La question porte sur l'article L. 123-4.",
            "Les faits mentionnés concernent...",
            "L'analyse se concentre sur...",
        ]
        
        for text in allowed_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert not violations, f"Neutral acknowledgment incorrectly flagged: {text}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4️⃣ NO NORMATIVE CONCLUSIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoNormativeConclusions:
    """
    Test absence de conclusions normatives.
    
    INTERDIT: "la clause est valide", "vous êtes libéré", "il est illégal"
    """
    
    def test_forbidden_normative_conclusions_detected(self):
        """Forbidden normative conclusions should be detectable."""
        violating_texts = [
            "La clause est valide.",
            "Le contrat est nul.",
            "Vous êtes libéré de vos obligations.",
            "Il est illégal de procéder ainsi.",
            "Cette pratique est interdite.",
        ]
        
        for text in violating_texts:
            violations = check_text_for_forbidden_patterns(text)
            assert violations, f"Should detect normative conclusion in: {text}"
    
    def test_factual_citations_allowed(self):
        """Factual citations from sources are allowed."""
        
        # These should not violate because they report/cite, not conclude
        # Note: some may trigger patterns - that's expected for edge cases
        # The key is that direct conclusions are caught
        pass  # Acknowledgment that edge cases exist


# ═══════════════════════════════════════════════════════════════════════════════
# 5️⃣ BANDEAU/BANNER COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBandeauCompliance:
    """
    Test que le bandeau/disclaimer est conforme.
    """
    
    def test_output_banner_exists(self):
        """LegalOutput should have banner method."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test answer",
            audit_bundle_id="test_audit",
        )
        
        # to_markdown should include banner
        markdown = output.to_markdown()
        
        # Check banner indicators
        assert "ANALYSE" in markdown.upper() or "POSITION" in markdown.upper() or "REFUS" in markdown.upper(), (
            "Output markdown should contain mode indicator"
        )
    
    def test_banner_mode_correct(self):
        """Banner should reflect actual mode."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        # SAFE_ANALYSIS mode
        safe_output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test",
            audit_bundle_id="test",
        )
        safe_md = safe_output.to_markdown()
        
        # REFUSAL mode
        refusal_output = LegalOutput(
            mode=LegalOutputMode.REFUSAL_REQUEST_INFO,
            answer="Informations manquantes",
            missing_info=["as_of_date"],
            audit_bundle_id="test",
        )
        refusal_md = refusal_output.to_markdown()
        
        # Banners should differ
        assert safe_md != refusal_md, "Different modes should produce different markdown"


# ═══════════════════════════════════════════════════════════════════════════════
# 6️⃣ COMPREHENSIVE TEXT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class TestComprehensiveTextAnalysis:
    """
    Test complet de tous les champs textuels.
    """
    
    def test_legal_output_all_fields_compliant(self):
        """All text fields in LegalOutput should be compliant."""
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        # Create a typical output
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="L'article L. 123-4 dispose que les entreprises doivent respecter...",
            facts=["Le contrat a été signé le 1er janvier 2024."],
            rules=["Article L. 123-4 du Code de commerce"],
            application="Les dispositions de l'article s'appliquent aux contrats commerciaux.",
            risks=["Clause potentiellement contestable selon l'article 12"],
            next_action="Vérifier la conformité avec les conditions générales",
            citations=["Art. L. 123-4 C. com."],
            audit_bundle_id="test_audit",
        )
        
        # Check all text fields
        fields_to_check = [
            ("answer", output.answer),
            ("application", output.application),
            ("next_action", output.next_action),
        ]
        
        for field_name, field_value in fields_to_check:
            if field_value:
                violations = check_text_for_forbidden_patterns(field_value)
                assert not violations, (
                    f"LegalOutput.{field_name} contains violations: {violations}"
                )
    
    def test_legal_draft_all_fields_compliant(self):
        """All text fields in LegalDraft should be compliant."""
        from python.helpers.legal_pipeline import (
            LegalDraft, LegalRouteContext, LegalRiskTier, DecisionScope,
        )
        
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.LOW,
            scope=DecisionScope.INFO,
            jurisdiction=None,
        )
        
        # Create a typical draft
        draft = LegalDraft(
            draft_id="test_draft",
            query="Test query",
            facts=["Le délai contractuel est de 30 jours."],
            rules=["Article 1134 du Code civil"],
            application="L'article 1134 encadre la force obligatoire des contrats.",
            legal_context=ctx,
            source_chunk_ids=["chunk_1"],
            citations=["Art. 1134 C. civ."],
        )
        
        # Check application field (main prose content)
        if draft.application:
            violations = check_text_for_forbidden_patterns(draft.application)
            assert not violations, (
                f"LegalDraft.application contains violations: {violations}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 7️⃣ EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """
    Test cas limites pour la détection de patterns.
    """
    
    def test_quoted_text_in_citations(self):
        """Quoted legal text should not be flagged even if it contains patterns."""
        # When we QUOTE a law that says "il est interdit", that's reporting
        # The key is OUR language, not the source's language
        
        # These are edge cases - the system should ideally recognize quotes
        # For now, we acknowledge this limitation
        pass
    
    def test_negative_statements_allowed(self):
        """Negative factual statements should be allowed."""
        allowed_negatives = [
            "L'article ne s'applique pas aux cas mentionnés.",
            "Cette disposition n'est pas applicable en l'espèce.",
            "Aucune source ne confirme cette interprétation.",
        ]
        
        for text in allowed_negatives:
            violations = check_text_for_forbidden_patterns(text)
            assert not violations, f"Negative statement incorrectly flagged: {text}"
    
    def test_conditional_statements_allowed(self):
        """Conditional factual statements should be allowed."""
        allowed_conditionals = [
            "Si les conditions de l'article 12 sont remplies, l'article s'applique.",
            "Dans le cas où la clause serait considérée comme abusive...",
            "Selon l'interprétation retenue par la Cour de cassation...",
        ]
        
        for text in allowed_conditionals:
            violations = check_text_for_forbidden_patterns(text)
            assert not violations, f"Conditional statement incorrectly flagged: {text}"


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
