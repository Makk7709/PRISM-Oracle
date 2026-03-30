"""
Canonical Organization Model for KOREV Evidence multi-tenant architecture.

All tenant identity logic MUST flow through this module.
No comparison, storage, or filtering of organization values is permitted
using raw strings elsewhere in the codebase.

Architecture:
- organization_id  : stable slug used for ALL logic, comparisons, storage
                     e.g. "dica-france", "korev-ai", "scriptoura"
- organization_display : human-readable label, UI only
                     e.g. "DICA France", "Korev AI", "Scriptoura"

Rules:
- normalize_org_id() is the SINGLE entry point for any org string → slug
- Organization registry is the source of truth for display names
- All comparisons use organization_id (never display)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("organization")

_SLUG_RE = re.compile(r"[^a-z0-9-]")
_MULTI_DASH = re.compile(r"-{2,}")


def normalize_org_id(raw: str | None) -> str:
    """Convert any organization string to its canonical slug form.

    Deterministic, idempotent, case-insensitive.
    Already-normalized slugs pass through unchanged.

    Examples:
        "DICA France"  → "dica-france"
        "Korev AI"     → "korev-ai"
        "Scriptoura"   → "scriptoura"
        "dica-france"  → "dica-france"  (idempotent)
        None           → ""
        ""             → ""
    """
    if not raw:
        return ""
    slug = raw.strip().lower()
    slug = slug.replace("_", "-").replace(" ", "-")
    slug = _SLUG_RE.sub("", slug)
    slug = _MULTI_DASH.sub("-", slug)
    slug = slug.strip("-")
    return slug


@dataclass(frozen=True)
class Organization:
    """Immutable organization entity."""
    organization_id: str      # canonical slug (e.g. "dica-france")
    display_name: str         # UI label (e.g. "DICA France")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class OrganizationRegistry:
    """In-memory registry of known organizations.

    Populated at startup from users.json.  Provides fast lookup
    from any form (display, slug, mixed-case) to the canonical Organization.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Organization] = {}

    def register(self, display_name: str, **metadata: object) -> Organization:
        """Register or retrieve an organization from its display name."""
        org_id = normalize_org_id(display_name)
        if not org_id:
            raise ValueError(f"Cannot register organization with empty slug from '{display_name}'")
        if org_id in self._by_id:
            return self._by_id[org_id]
        org = Organization(
            organization_id=org_id,
            display_name=display_name,
            metadata=dict(metadata),
        )
        self._by_id[org_id] = org
        logger.info("organization_registered org_id=%s display=%s", org_id, display_name)
        return org

    def get(self, raw: str | None) -> Optional[Organization]:
        """Lookup by any form (display name, slug, mixed-case)."""
        org_id = normalize_org_id(raw)
        return self._by_id.get(org_id)

    def get_display(self, raw: str | None) -> str:
        """Return the display name for any org input, or the input itself as fallback."""
        org = self.get(raw)
        if org:
            return org.display_name
        return raw or ""

    def get_id(self, raw: str | None) -> str:
        """Return the canonical org_id for any org input."""
        return normalize_org_id(raw)

    def all_ids(self) -> list[str]:
        return list(self._by_id.keys())

    def all_orgs(self) -> list[Organization]:
        return list(self._by_id.values())

    def __contains__(self, raw: str | None) -> bool:
        return normalize_org_id(raw) in self._by_id


# Module-level singleton
_registry: OrganizationRegistry | None = None


def get_registry() -> OrganizationRegistry:
    global _registry
    if _registry is None:
        _registry = OrganizationRegistry()
    return _registry


def initialize_registry_from_users(users: dict) -> OrganizationRegistry:
    """Populate the registry from a users.json-style dict.

    Called once at startup from UserManager._load_users_json.
    """
    registry = get_registry()
    seen_orgs: set[str] = set()
    for _username, info in users.items():
        display = info.get("organization")
        if display and display not in seen_orgs:
            seen_orgs.add(display)
            registry.register(display)
    return registry


def org_match(a: str | None, b: str | None) -> bool:
    """Compare two organization values using canonical normalization.

    This is the ONLY sanctioned way to compare orgs in the entire codebase.
    """
    return normalize_org_id(a) == normalize_org_id(b)
