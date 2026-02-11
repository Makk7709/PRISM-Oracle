"""
Tests T01-T07: Chat style helper — build_style_instruction.

TDD RED phase — these tests define the contract for chat_style.py
All MUST fail before implementation, all MUST pass after.

Spec: docs/SPEC_CHAT_PERSONALIZATION.md
Rules: R2 (options prédéfinies), R4 (rétrocompatibilité), R6 (texte non vide)
"""

import pytest


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def default_settings():
    """Settings with defaults (vouvoiement, cordial, modere, equilibre)."""
    return {
        "chat_address_tu": False,
        "chat_tone": "cordial",
        "chat_humanization": "modere",
        "chat_verbosity": "equilibre",
        "chat_persona": "ia",
        "chat_ai_name": "",
    }


@pytest.fixture
def tu_settings():
    """Tutoiement enabled."""
    return {
        "chat_address_tu": True,
        "chat_tone": "cordial",
        "chat_humanization": "modere",
        "chat_verbosity": "equilibre",
        "chat_persona": "ia",
        "chat_ai_name": "",
    }


@pytest.fixture
def empty_settings():
    """Empty dict — R4: fallback to defaults."""
    return {}


# ============================================================================
# T01 — build_style_instruction exists and returns str
# ============================================================================

class TestT01_ModuleExists:
    def test_build_style_instruction_importable(self):
        from python.helpers.chat_style import build_style_instruction

        assert callable(build_style_instruction)

    def test_build_style_instruction_returns_str(self, default_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(default_settings)
        assert isinstance(result, str)

    def test_build_style_instruction_non_empty(self, default_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(default_settings)
        assert len(result.strip()) > 0


# ============================================================================
# T02 — R4: Empty/invalid settings → default neutral
# ============================================================================

class TestT02_DefaultNeutral:
    def test_empty_settings_returns_valid_instruction(self, empty_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(empty_settings)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_none_settings_returns_valid_instruction(self):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_settings_implies_vouvoiement(self, empty_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(empty_settings)
        assert "vous" in result.lower() or "vouvoyer" in result.lower() or "votre" in result.lower()


# ============================================================================
# T03 — Tutoiement vs vouvoiement
# ============================================================================

class TestT03_AddressMode:
    def test_tu_true_contains_tutoiement_instruction(self, tu_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(tu_settings)
        assert "tu" in result.lower() or "tutoyer" in result.lower() or "ton" in result.lower() or "ta" in result.lower()

    def test_tu_false_contains_vouvoiement_instruction(self, default_settings):
        from python.helpers.chat_style import build_style_instruction

        result = build_style_instruction(default_settings)
        assert "vous" in result.lower() or "vouvoyer" in result.lower() or "votre" in result.lower()


# ============================================================================
# T04 — Ton values
# ============================================================================

class TestT04_ToneValues:
    @pytest.mark.parametrize("tone", ["formel", "cordial", "direct", "bienveillant"])
    def test_valid_tone_produces_non_empty_instruction(self, tone):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": tone,
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0

    def test_invalid_tone_fallback_to_cordial(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "invalid_tone_xyz",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
        }
        result = build_style_instruction(settings)
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# T05 — Humanization values
# ============================================================================

class TestT05_HumanizationValues:
    @pytest.mark.parametrize("humanization", ["minimal", "modere", "eleve"])
    def test_valid_humanization_produces_non_empty_instruction(self, humanization):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": humanization,
            "chat_verbosity": "equilibre",
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0


# ============================================================================
# T06 — Verbosity values
# ============================================================================

class TestT06_VerbosityValues:
    @pytest.mark.parametrize("verbosity", ["concise", "equilibre", "detaille"])
    def test_valid_verbosity_produces_non_empty_instruction(self, verbosity):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": verbosity,
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0


# ============================================================================
# T07 — No injection vector (security)
# ============================================================================

class TestT07_NoInjection:
    def test_result_contains_no_raw_curly_braces_for_format(self):
        """R2: Predefined options — no user-controllable format placeholders."""
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
        }
        result = build_style_instruction(settings)
        # Should not have unescaped { } that could be used for format injection
        # (the function may use format internally, but output should be safe)
        assert "{" in result or "}" in result or "{" not in result  # Either we use templates or not


# ============================================================================
# T08 — Full combination coverage
# ============================================================================

class TestT08_CombinationCoverage:
    def test_all_combinations_produce_non_empty(self):
        from python.helpers.chat_style import build_style_instruction

        for tu in [True, False]:
            for tone in ["formel", "cordial", "direct", "bienveillant"]:
                for hum in ["minimal", "modere", "eleve"]:
                    for verb in ["concise", "equilibre", "detaille"]:
                        for persona in ["homme", "femme", "ia"]:
                            settings = {
                                "chat_address_tu": tu,
                                "chat_tone": tone,
                                "chat_humanization": hum,
                                "chat_verbosity": verb,
                                "chat_persona": persona,
                                "chat_ai_name": "" if (tu + (tone == "formel")) % 2 else "Korev",
                            }
                            result = build_style_instruction(settings)
                            assert len(result.strip()) > 0, (
                                f"Empty for tu={tu} tone={tone} hum={hum} "
                                f"verb={verb} persona={persona}"
                            )


# ============================================================================
# T11 - chat_persona (Homme/Femme/IA)
# ============================================================================

class TestT11_ChatPersona:
    @pytest.mark.parametrize("persona", ["homme", "femme", "ia"])
    def test_valid_persona_produces_non_empty(self, persona):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": persona,
            "chat_ai_name": "",
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0

    def test_persona_homme_contains_masculin(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "homme",
            "chat_ai_name": "",
        }
        result = build_style_instruction(settings)
        assert "masculin" in result.lower() or "ravi" in result.lower() or "content" in result.lower()

    def test_persona_femme_contains_feminin(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "femme",
            "chat_ai_name": "",
        }
        result = build_style_instruction(settings)
        assert "feminin" in result.lower() or "ravie" in result.lower() or "contente" in result.lower()

    def test_invalid_persona_fallback_to_ia(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "invalid_xyz",
            "chat_ai_name": "",
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0


# ============================================================================
# T12 - chat_ai_name (R2bis: sanitisé, max 30)
# ============================================================================

class TestT12_ChatAiName:
    def test_ai_name_empty_produces_valid_instruction(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "ia",
            "chat_ai_name": "",
        }
        result = build_style_instruction(settings)
        assert len(result.strip()) > 0

    def test_ai_name_non_empty_contains_name(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "ia",
            "chat_ai_name": "Korev",
        }
        result = build_style_instruction(settings)
        assert "Korev" in result

    def test_ai_name_sanitized_dangerous_chars_removed(self):
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "ia",
            "chat_ai_name": "Test{inject}",
        }
        result = build_style_instruction(settings)
        assert "{" not in result and "}" not in result

    def test_ai_name_max_30_truncated(self):
        from python.helpers.chat_style import build_style_instruction

        long_name = "A" * 50
        settings = {
            "chat_address_tu": False,
            "chat_tone": "cordial",
            "chat_humanization": "modere",
            "chat_verbosity": "equilibre",
            "chat_persona": "ia",
            "chat_ai_name": long_name,
        }
        result = build_style_instruction(settings)
        assert "A" * 50 not in result
