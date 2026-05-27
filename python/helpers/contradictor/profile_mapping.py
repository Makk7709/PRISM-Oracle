# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         CONTRADICTOR — Canonical application-side intent→profile map         ║
║                                                                              ║
║  Single source of truth for the orchestrator side of the profile mapping.   ║
║                                                                              ║
║  CRITICAL                                                                    ║
║  - `contradictor` MUST map to `contradictor`, never to `default`.            ║
║  - The audit-only mapping in `python/helpers/router/metrics.py` is           ║
║    intentionally distinct (used for divergence analysis only).               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


INTENT_TO_PROFILE: Mapping[str, str] = MappingProxyType(
    {
        "finance": "finance",
        "sales": "sales",
        "legal_safe": "legal_safe",
        "medical": "medical",
        "developer": "developer",
        "researcher": "researcher",
        "marketing": "marketing",
        "multitask": "default",
        "contradictor": "contradictor",
    }
)


def resolve_profile_for_intent(intent_name: str) -> str:
    """
    Resolve an IntentName value to the application-side profile name.

    Raises:
        KeyError: if the intent has no canonical mapping. We refuse to
                  silently fallback for unknown intents — defensive design.
    """
    if intent_name not in INTENT_TO_PROFILE:
        raise KeyError(
            f"No canonical profile mapping for intent {intent_name!r}. "
            "Update python/helpers/contradictor/profile_mapping.py."
        )
    return INTENT_TO_PROFILE[intent_name]


__all__ = ["INTENT_TO_PROFILE", "resolve_profile_for_intent"]
