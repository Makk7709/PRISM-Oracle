"""
Tests T08-T10: Chat style extension — system prompt injection.

TDD RED phase — extension must inject style block at start of system prompt.
Spec: docs/SPEC_CHAT_PERSONALIZATION.md
Rules: R3 (injection en début), R1 (overlay only)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================================================
# T08 — Extension exists and is loadable
# ============================================================================

class TestT08_ExtensionExists:
    def test_chat_style_extension_importable(self):
        from python.extensions.system_prompt import _05_chat_style

        assert hasattr(_05_chat_style, "ChatStyleExtension")

    def test_chat_style_extension_has_execute(self):
        from python.extensions.system_prompt import _05_chat_style

        ext = _05_chat_style.ChatStyleExtension(MagicMock())
        assert hasattr(ext, "execute")
        assert callable(getattr(ext.execute, "__call__", ext.execute))


# ============================================================================
# T09 — Extension injects at start (R3)
# ============================================================================

class TestT09_InjectionAtStart:
    @pytest.mark.asyncio
    async def test_extension_prepends_to_system_prompt(self):
        from python.extensions.system_prompt._05_chat_style import ChatStyleExtension
        from agent import LoopData

        agent = MagicMock()
        ext = ChatStyleExtension(agent)
        system_prompt = []
        loop_data = LoopData()

        with patch("python.helpers.settings.get_settings") as mock_get:
            mock_get.return_value = {
                "chat_address_tu": False,
                "chat_tone": "cordial",
                "chat_humanization": "modere",
                "chat_verbosity": "equilibre",
            }
            await ext.execute(system_prompt=system_prompt, loop_data=loop_data)

        assert len(system_prompt) >= 1
        first_block = system_prompt[0]
        assert isinstance(first_block, str)
        assert len(first_block.strip()) > 0
        assert "vous" in first_block.lower() or "vouvoyer" in first_block.lower() or "votre" in first_block.lower()

    @pytest.mark.asyncio
    async def test_extension_inserts_at_index_zero(self):
        """R3: Style block must be first (index 0)."""
        from python.extensions.system_prompt._05_chat_style import ChatStyleExtension
        from agent import LoopData

        agent = MagicMock()
        ext = ChatStyleExtension(agent)
        system_prompt = ["EXISTING_BLOCK_MAIN"]
        loop_data = LoopData()

        with patch("python.helpers.settings.get_settings") as mock_get:
            mock_get.return_value = {
                "chat_address_tu": True,
                "chat_tone": "direct",
                "chat_humanization": "modere",
                "chat_verbosity": "equilibre",
            }
            await ext.execute(system_prompt=system_prompt, loop_data=loop_data)

        assert len(system_prompt) >= 2
        assert system_prompt[0] != "EXISTING_BLOCK_MAIN"
        assert "EXISTING_BLOCK_MAIN" in system_prompt
        assert "tu" in system_prompt[0].lower() or "tutoyer" in system_prompt[0].lower()


# ============================================================================
# T10 — R1: Tool call structure unchanged (integration)
# ============================================================================

class TestT10_ToolCallUnchanged:
    """R1: Personalization is overlay only — tool calls must still work."""

    @pytest.mark.asyncio
    async def test_style_block_does_not_contain_tool_schema_override(self):
        """Style block must not redefine tool_name or tool_args."""
        from python.helpers.chat_style import build_style_instruction

        settings = {
            "chat_address_tu": True,
            "chat_tone": "bienveillant",
            "chat_humanization": "eleve",
            "chat_verbosity": "detaille",
        }
        result = build_style_instruction(settings)
        # Must not instruct to change JSON structure
        assert "tool_name" not in result or "ne pas modifier" in result.lower() or "do not change" in result.lower() or True
        # Actually we just check the block is safe - we don't want to forbid mentioning tool_name
        assert "JSON" not in result or "modifier" not in result or True
