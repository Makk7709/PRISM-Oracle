"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TOOL POLICY — Runtime Validation                         ║
║                                                                              ║
║  Middleware for validating tool calls against profile-based policies.       ║
║  Ensures tools are authorized before execution.                             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agent import Agent


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class PolicyDecision(str, Enum):
    """Decision result from policy check."""
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    REQUIRES_FALLBACK = "requires_fallback"


@dataclass
class PolicyResult:
    """Result of a policy check."""
    decision: PolicyDecision
    tool_name: str
    reason: str = ""
    allowed_alternatives: list[str] = None
    
    def __post_init__(self):
        if self.allowed_alternatives is None:
            self.allowed_alternatives = []


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Default policies for all profiles
DEFAULT_POLICY = {
    "image_tools": {
        "allowed": ["generate_image"],
        "forbidden_patterns": [],
        "enabled": True,
    }
}

# Profile-specific overrides
PROFILE_POLICIES = {
    "marketing": {
        "image_tools": {
            "allowed": ["generate_image"],
            "forbidden_patterns": [
                r"huggingface",
                r"stable_diffusion",
                r"sd_",
                r"midjourney",
                r"replicate",
            ],
            "enabled": True,
            "require_tool_for_image_request": True,
        }
    },
    "legal_safe": {
        "image_tools": {
            "allowed": ["generate_image"],
            "forbidden_patterns": [],
            "enabled": True,  # Legal can use images for diagrams, etc.
        }
    },
    "finance": {
        "image_tools": {
            "allowed": ["generate_image"],
            "forbidden_patterns": [],
            "enabled": True,  # Finance can use images for charts, etc.
        }
    },
    "developer": {
        "image_tools": {
            "allowed": ["generate_image"],
            "forbidden_patterns": [],
            "enabled": True,
        }
    },
    "multitask": {
        "image_tools": {
            "allowed": ["generate_image"],
            "forbidden_patterns": [],
            "enabled": True,
        }
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_tool_policy(
    tool_name: str,
    profile: str,
    agent: Optional["Agent"] = None
) -> PolicyResult:
    """
    Check if a tool is allowed for the given profile.
    
    Args:
        tool_name: Name of the tool being called
        profile: Active agent profile
        agent: Optional agent instance for context
        
    Returns:
        PolicyResult with decision and reasoning
    """
    tool_name_lower = tool_name.lower()
    
    # Get policy for profile
    policy = get_policy_for_profile(profile)
    
    # Check image tools policy
    image_policy = policy.get("image_tools", {})
    
    # Check if tool is in forbidden patterns
    for pattern in image_policy.get("forbidden_patterns", []):
        if re.search(pattern, tool_name_lower, re.IGNORECASE):
            allowed = image_policy.get("allowed", [])
            return PolicyResult(
                decision=PolicyDecision.FORBIDDEN,
                tool_name=tool_name,
                reason=f"Tool '{tool_name}' matches forbidden pattern '{pattern}' for profile '{profile}'",
                allowed_alternatives=allowed
            )
    
    # Check if image generation is enabled
    if _is_image_tool(tool_name_lower):
        from python.helpers import settings as settings_module
        settings = settings_module.get_settings()
        if not settings.get("image_gen_enabled", True):
            return PolicyResult(
                decision=PolicyDecision.FORBIDDEN,
                tool_name=tool_name,
                reason="Image generation is disabled in settings"
            )
        
        if not image_policy.get("enabled", True):
            return PolicyResult(
                decision=PolicyDecision.FORBIDDEN,
                tool_name=tool_name,
                reason=f"Image generation is disabled for profile '{profile}'"
            )
    
    # Tool is allowed
    return PolicyResult(
        decision=PolicyDecision.ALLOWED,
        tool_name=tool_name,
        reason="Tool allowed by policy"
    )


def get_policy_for_profile(profile: str) -> dict:
    """Get the effective policy for a profile."""
    # Start with default policy
    policy = DEFAULT_POLICY.copy()
    
    # Merge profile-specific policy
    if profile in PROFILE_POLICIES:
        profile_policy = PROFILE_POLICIES[profile]
        for key, value in profile_policy.items():
            if key in policy and isinstance(policy[key], dict):
                policy[key] = {**policy[key], **value}
            else:
                policy[key] = value
    
    return policy


def get_allowed_tools_for_profile(profile: str, category: str = "image_tools") -> list[str]:
    """Get list of allowed tools for a profile in a category."""
    policy = get_policy_for_profile(profile)
    return policy.get(category, {}).get("allowed", [])


def is_tool_forbidden(tool_name: str, profile: str) -> tuple[bool, str]:
    """
    Quick check if a tool is forbidden.
    
    Returns:
        (is_forbidden, reason)
    """
    result = check_tool_policy(tool_name, profile)
    if result.decision == PolicyDecision.FORBIDDEN:
        return True, result.reason
    return False, ""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _is_image_tool(tool_name: str) -> bool:
    """Check if a tool is an image generation tool."""
    image_patterns = [
        r"generate_image",
        r"create_image",
        r"image_gen",
        r"dall-?e",
        r"imagen",
        r"stable_diffusion",
        r"midjourney",
    ]
    for pattern in image_patterns:
        if re.search(pattern, tool_name, re.IGNORECASE):
            return True
    return False


def format_forbidden_response(result: PolicyResult) -> str:
    """Format a user-friendly response for forbidden tool."""
    response = f"## ⚠️ Tool Not Authorized\n\n"
    response += f"**Tool:** `{result.tool_name}`\n\n"
    response += f"**Reason:** {result.reason}\n\n"
    
    if result.allowed_alternatives:
        response += "**Allowed alternatives:**\n"
        for alt in result.allowed_alternatives:
            response += f"- `{alt}`\n"
    
    return response


def log_policy_check(result: PolicyResult, profile: str):
    """Log policy check result."""
    from python.helpers.print_style import PrintStyle
    if result.decision == PolicyDecision.FORBIDDEN:
        PrintStyle(font_color="red", padding=True).print(
            f"[POLICY] BLOCKED: {result.tool_name} for profile={profile}"
        )
        PrintStyle(font_color="red").print(f"  Reason: {result.reason}")
    elif result.decision == PolicyDecision.ALLOWED:
        PrintStyle(font_color="green").print(
            f"[POLICY] ALLOWED: {result.tool_name} for profile={profile}"
        )


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "PolicyDecision",
    "PolicyResult",
    "check_tool_policy",
    "get_policy_for_profile",
    "get_allowed_tools_for_profile",
    "is_tool_forbidden",
    "format_forbidden_response",
    "log_policy_check",
]
