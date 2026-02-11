"""
Extension system_prompt — Chat style personalization (symbiose homme-IA).

Injects the style block at the START of the system prompt (R3).
Runs before _10_system_prompt (filename sort: _05 < _10).

Spec: docs/SPEC_CHAT_PERSONALIZATION.md
"""

from typing import Any

from python.helpers.extension import Extension
from python.helpers.settings import get_settings
from python.helpers.chat_style import build_style_instruction
from agent import LoopData


class ChatStyleExtension(Extension):
    """Injects chat personalization (tutoiement, ton, humanisation) at start of system prompt."""

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any
    ) -> None:
        settings = get_settings()
        style_block = build_style_instruction(settings)
        system_prompt.insert(0, style_block)
