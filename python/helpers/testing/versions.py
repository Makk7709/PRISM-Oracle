# -*- coding: utf-8 -*-
"""
Version constants for fixture key computation.

These versions are included in fixture keys to ensure fixtures are
invalidated when prompts or schemas change.

RULES:
- Bump PROMPT_VERSION when any system prompt or message format changes
- Bump TOOL_SCHEMA_VERSION when tool schemas change
- Bump EVIDENCE_LOGIC_VERSION when reasoning logic changes significantly

Version format: "YYYY-MM-DD-x" where x is a/b/c for same-day bumps.
"""

# Bump when prompts change (system messages, user message templates, etc.)
PROMPT_VERSION = "2026-01-24-a"

# Bump when tool schemas change (function definitions, parameter formats)
TOOL_SCHEMA_VERSION = "v1"

# Bump when core reasoning logic changes (escalation rules, thresholds)
EVIDENCE_LOGIC_VERSION = "v1"


def get_version_suffix() -> str:
    """
    Get version suffix for fixture keys.
    
    Returns: "pv-{PROMPT_VERSION}__sv-{TOOL_SCHEMA_VERSION}"
    """
    return f"pv-{PROMPT_VERSION}__sv-{TOOL_SCHEMA_VERSION}"


def get_all_versions() -> dict:
    """
    Get all version constants as a dict.
    
    Useful for logging and debugging.
    """
    return {
        "prompt_version": PROMPT_VERSION,
        "tool_schema_version": TOOL_SCHEMA_VERSION,
        "evidence_logic_version": EVIDENCE_LOGIC_VERSION,
    }
