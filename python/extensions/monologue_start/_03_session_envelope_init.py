"""
SESSION 6/6.1 — Initialize SessionEnvelope at monologue start.

Runs in monologue_start (before pipeline hooks _10/_15 and audit append _20)
so the envelope is available for ALL code paths — including pipeline
short-circuit requests (strategic, legal) that never enter the inner
message loop.

Creates a fresh SessionEnvelope with user context (username, organization,
query text, human user profile) and stores it on agent.data["_session_envelope"]
for downstream consumption by the audit metadata hook (_20).

SESSION 6.1 FIX (D1): user_profile now resolves the HUMAN user profile
from UserManager (e.g. "Admin", "Juriste") instead of the agent config
profile (e.g. "legal_safe"). Falls back to agent profile for background
contexts where Flask is unavailable.

Fail-safe: any error is logged and swallowed — never blocks the pipeline.
"""

import logging
from typing import Optional, TYPE_CHECKING

from python.helpers.extension import Extension

if TYPE_CHECKING:
    from agent import LoopData

logger = logging.getLogger("session_envelope_init")


class SessionEnvelopeInit(Extension):

    async def execute(self, loop_data=None, **kwargs):
        try:
            from python.helpers.session_envelope import SessionEnvelope

            username = getattr(self.agent.context, "username", None)

            envelope = SessionEnvelope(
                username=username,
                organization=getattr(self.agent.context, "organization", None),
                user_profile=self._resolve_human_profile(username),
            )

            query_text = self._extract_query(loop_data)
            if query_text:
                envelope.query = query_text

            self.agent.set_data("_session_envelope", envelope)
            logger.debug("SessionEnvelope initialized: %s", envelope.session_id)

        except Exception as exc:
            logger.error("SessionEnvelope init failed (non-blocking): %s", exc)

    def _resolve_human_profile(self, username: Optional[str]) -> str:
        """Resolve the human user profile from UserManager.

        Priority:
          1. UserManager.get_user_profile(username) — real human profile
          2. agent.config.profile — agent profile as fallback
          3. "default" — last resort
        """
        if username:
            try:
                from flask import current_app
                user_mgr = current_app.config.get("USER_MANAGER")
                if user_mgr:
                    profile = user_mgr.get_user_profile(username)
                    if profile:
                        return profile
            except (RuntimeError, ImportError):
                pass
        return getattr(self.agent.config, "profile", None) or "default"

    def _extract_query(self, loop_data) -> str:
        """Extract user query text, truncated to 2000 chars for hashing."""
        try:
            if loop_data and loop_data.user_message:
                content = getattr(loop_data.user_message, "content", None)
                if isinstance(content, str) and content.strip():
                    return content.strip()[:2000]

            msg = getattr(self.agent, "last_user_message", None)
            if msg:
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    return content.strip()[:2000]
        except Exception:
            pass
        return ""
