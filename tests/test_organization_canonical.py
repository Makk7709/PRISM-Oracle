"""
Tests for the canonical Organization model, normalization, and multi-tenant isolation.

Covers:
- normalize_org_id() idempotency and edge cases
- OrganizationRegistry lookup
- Authorization with normalized org comparisons
- Cross-tenant isolation (regression for the "dica-france" vs "DICA France" bug)
- Notification visibility with mixed org formats
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.organization import (
    normalize_org_id,
    org_match,
    Organization,
    OrganizationRegistry,
    get_registry,
    initialize_registry_from_users,
)
from python.security.authorization import (
    AccessPrincipal,
    can_access_context,
    can_access_task,
    validate_task_scope,
)


# normalize_org_id
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeOrgId:
    def test_display_to_slug_dica(self):
        assert normalize_org_id("DICA France") == "dica-france"

    def test_display_to_slug_korev(self):
        assert normalize_org_id("Korev AI") == "korev-ai"

    def test_display_to_slug_scriptoura(self):
        assert normalize_org_id("Scriptoura") == "scriptoura"

    def test_idempotent_slug(self):
        assert normalize_org_id("dica-france") == "dica-france"

    def test_idempotent_korev(self):
        assert normalize_org_id("korev-ai") == "korev-ai"

    def test_none_returns_empty(self):
        assert normalize_org_id(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_org_id("") == ""

    def test_whitespace_stripped(self):
        assert normalize_org_id("  DICA France  ") == "dica-france"

    def test_underscores_to_dashes(self):
        assert normalize_org_id("my_org_name") == "my-org-name"

    def test_special_chars_removed(self):
        assert normalize_org_id("Org@#$%Test!") == "orgtest"

    def test_multiple_spaces(self):
        assert normalize_org_id("DICA   France") == "dica-france"

    def test_case_variations(self):
        assert normalize_org_id("KOREV AI") == "korev-ai"
        assert normalize_org_id("korev ai") == "korev-ai"
        assert normalize_org_id("Korev Ai") == "korev-ai"
        assert normalize_org_id("KOREV-AI") == "korev-ai"

    def test_no_leading_trailing_dash(self):
        assert normalize_org_id("-test-org-") == "test-org"

    def test_double_dashes_collapsed(self):
        assert normalize_org_id("test--org") == "test-org"


class TestOrgMatch:
    def test_display_vs_slug(self):
        assert org_match("DICA France", "dica-france") is True

    def test_korev_variants(self):
        assert org_match("Korev AI", "korev-ai") is True

    def test_scriptoura(self):
        assert org_match("Scriptoura", "scriptoura") is True

    def test_different_orgs(self):
        assert org_match("DICA France", "korev-ai") is False

    def test_none_vs_none(self):
        assert org_match(None, None) is True

    def test_none_vs_string(self):
        assert org_match(None, "dica-france") is False

    def test_string_vs_none(self):
        assert org_match("dica-france", None) is False


# OrganizationRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrganizationRegistry:
    def test_register_and_lookup(self):
        registry = OrganizationRegistry()
        org = registry.register("DICA France")
        assert org.organization_id == "dica-france"
        assert org.display_name == "DICA France"

    def test_lookup_by_slug(self):
        registry = OrganizationRegistry()
        registry.register("Korev AI")
        found = registry.get("korev-ai")
        assert found is not None
        assert found.display_name == "Korev AI"

    def test_lookup_by_display(self):
        registry = OrganizationRegistry()
        registry.register("Scriptoura")
        found = registry.get("Scriptoura")
        assert found is not None
        assert found.organization_id == "scriptoura"

    def test_get_display_fallback(self):
        registry = OrganizationRegistry()
        assert registry.get_display("unknown-org") == "unknown-org"

    def test_initialize_from_users(self):
        users = {
            "amine": {"organization": "Korev AI"},
            "nicolas": {"organization": "DICA France"},
            "louis": {"organization": "Scriptoura"},
        }
        registry = OrganizationRegistry()
        # Manually set module-level registry for test
        import python.helpers.organization as org_mod
        old = org_mod._registry
        org_mod._registry = registry
        try:
            initialize_registry_from_users(users)
            assert "korev-ai" in registry
            assert "dica-france" in registry
            assert "scriptoura" in registry
        finally:
            org_mod._registry = old

    def test_idempotent_register(self):
        registry = OrganizationRegistry()
        org1 = registry.register("DICA France")
        org2 = registry.register("DICA France")
        assert org1 is org2

    def test_contains_case_insensitive(self):
        registry = OrganizationRegistry()
        registry.register("Korev AI")
        assert "korev-ai" in registry
        assert "Korev AI" in registry
        assert "KOREV AI" in registry
        assert "dica-france" not in registry


# ═══════════════════════════════════════════════════════════════════════════════
# Authorization with normalized org — THE CRITICAL REGRESSION TEST
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthorizationNormalized:
    """Regression tests for the case-sensitive org comparison bug."""

    def _principal(self, username, org, org_role="MEMBER"):
        return AccessPrincipal(
            username=username,
            organization=org,
            org_role=org_role,
            role="user",
            workspace=f"/app/shared/users/{username}",
        )

    def test_dica_display_vs_slug(self):
        """THE BUG: session has 'DICA France', chat has 'dica-france'."""
        principal = self._principal("nicolas", "DICA France")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="nicolas",
            ctx_org="dica-france",
        )
        assert allowed is True, f"Expected access but got: {reason}"

    def test_korev_display_vs_slug(self):
        """Session has 'Korev AI', chat has 'korev-ai'."""
        principal = self._principal("amine", "Korev AI", "OWNER")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="amine",
            ctx_org="korev-ai",
        )
        assert allowed is True, f"Expected access but got: {reason}"

    def test_scriptoura_display_vs_slug(self):
        principal = self._principal("louis", "Scriptoura")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="louis",
            ctx_org="scriptoura",
        )
        assert allowed is True, f"Expected access but got: {reason}"

    def test_cross_org_still_denied(self):
        """DICA user must NOT access Korev chats."""
        principal = self._principal("nicolas", "DICA France")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="amine",
            ctx_org="korev-ai",
        )
        assert allowed is False
        assert reason == "cross_organization_denied"

    def test_korev_cannot_see_dica(self):
        principal = self._principal("amine", "Korev AI", "OWNER")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="nicolas",
            ctx_org="dica-france",
        )
        assert allowed is False
        assert reason == "cross_organization_denied"

    def test_owner_sees_all_org_chats(self):
        """OWNER of Korev sees all Korev chats regardless of owner."""
        principal = self._principal("amine", "Korev AI", "OWNER")
        allowed, _ = can_access_context(
            principal,
            ctx_owner="aya",
            ctx_org="korev-ai",
        )
        assert allowed is True

    def test_member_cannot_see_other_member(self):
        """MEMBER of DICA cannot see another DICA member's chat."""
        principal = self._principal("nicolas", "DICA France", "MEMBER")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="coralie",
            ctx_org="dica-france",
        )
        assert allowed is False
        assert reason == "member_not_owner"

    def test_missing_org_fail_closed(self):
        principal = self._principal("nicolas", "DICA France")
        allowed, reason = can_access_context(
            principal,
            ctx_owner="nicolas",
            ctx_org=None,
        )
        assert allowed is False
        assert reason == "context_missing_organization"

    def test_task_access_normalized(self):
        principal = self._principal("jeremie", "DICA France")
        allowed, _ = can_access_task(
            principal,
            task_owner="jeremie",
            task_org="dica-france",
        )
        assert allowed is True

    def test_task_cross_org_denied(self):
        principal = self._principal("amine", "Korev AI", "OWNER")
        allowed, reason = can_access_task(
            principal,
            task_owner="jeremie",
            task_org="dica-france",
        )
        assert allowed is False


# ═══════════════════════════════════════════════════════════════════════════════
# Full multi-tenant isolation matrix
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiTenantIsolationMatrix:
    """Exhaustive cross-org tests for all 3 organizations."""

    USERS = {
        "amine": ("Korev AI", "OWNER"),
        "aya": ("Korev AI", "MEMBER"),
        "nicolas": ("DICA France", "MEMBER"),
        "jeremie": ("DICA France", "MEMBER"),
        "coralie": ("DICA France", "MEMBER"),
        "louis": ("Scriptoura", "MEMBER"),
        "mathias": ("Scriptoura", "MEMBER"),
    }

    CHATS = {
        "amine_chat": ("amine", "korev-ai"),
        "aya_chat": ("aya", "Korev AI"),
        "nicolas_chat": ("nicolas", "dica-france"),
        "jeremie_chat": ("jeremie", "DICA France"),
        "louis_chat": ("louis", "scriptoura"),
        "mathias_chat": ("mathias", "Scriptoura"),
    }

    def _check(self, user, chat_owner, chat_org):
        org_display, role = self.USERS[user]
        principal = AccessPrincipal(
            username=user,
            organization=org_display,
            org_role=role,
            role="user",
            workspace=f"/app/shared/users/{user}",
        )
        return can_access_context(
            principal, ctx_owner=chat_owner, ctx_org=chat_org
        )

    def test_amine_sees_own_chats(self):
        allowed, _ = self._check("amine", "amine", "korev-ai")
        assert allowed

    def test_amine_sees_aya_chats_as_owner(self):
        allowed, _ = self._check("amine", "aya", "Korev AI")
        assert allowed

    def test_aya_sees_own_chats(self):
        allowed, _ = self._check("aya", "aya", "korev-ai")
        assert allowed

    def test_aya_cannot_see_amine_chats(self):
        allowed, _ = self._check("aya", "amine", "korev-ai")
        assert not allowed

    def test_nicolas_sees_own_chats(self):
        allowed, _ = self._check("nicolas", "nicolas", "dica-france")
        assert allowed

    def test_nicolas_cannot_see_jeremie(self):
        allowed, _ = self._check("nicolas", "jeremie", "dica-france")
        assert not allowed

    def test_nicolas_cannot_see_korev(self):
        allowed, _ = self._check("nicolas", "amine", "korev-ai")
        assert not allowed

    def test_nicolas_cannot_see_scriptoura(self):
        allowed, _ = self._check("nicolas", "louis", "scriptoura")
        assert not allowed

    def test_louis_sees_own(self):
        allowed, _ = self._check("louis", "louis", "scriptoura")
        assert allowed

    def test_louis_cannot_see_dica(self):
        allowed, _ = self._check("louis", "nicolas", "dica-france")
        assert not allowed

    def test_louis_cannot_see_korev(self):
        allowed, _ = self._check("louis", "amine", "korev-ai")
        assert not allowed

    def test_all_cross_org_denied(self):
        """Exhaustive: every user tested against every other org's chat."""
        for user, (user_org, _) in self.USERS.items():
            for chat_name, (chat_owner, chat_org) in self.CHATS.items():
                allowed, reason = self._check(user, chat_owner, chat_org)
                user_org_id = normalize_org_id(user_org)
                chat_org_id = normalize_org_id(chat_org)

                if user_org_id != chat_org_id:
                    assert not allowed, (
                        f"LEAK: {user} ({user_org}) accessed {chat_name} ({chat_org})"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# Regression: reproduce the exact production bug
# ═══════════════════════════════════════════════════════════════════════════════


class TestProductionBugRegression:
    """Reproduce the exact conditions that caused 69/71 chats to be hidden."""

    PRODUCTION_ORGS_IN_CHATS = [
        "dica-france",
        "korev-ai",
        "scriptoura",
        "Korev AI",
    ]

    PRODUCTION_ORGS_IN_SESSION = [
        "DICA France",
        "Korev AI",
        "Scriptoura",
    ]

    def test_all_production_org_pairs_match(self):
        """Every org stored in chats must match its session counterpart."""
        mapping = {
            "dica-france": "DICA France",
            "korev-ai": "Korev AI",
            "scriptoura": "Scriptoura",
            "Korev AI": "Korev AI",
        }
        for chat_org, session_org in mapping.items():
            assert org_match(chat_org, session_org), (
                f"PRODUCTION BUG: '{chat_org}' should match '{session_org}'"
            )

    def test_57_dica_chats_visible(self):
        """All DICA chats with org='dica-france' must be visible to DICA users."""
        principal = AccessPrincipal(
            username="coralie",
            organization="DICA France",
            org_role="MEMBER",
            role="user",
            workspace="/app/shared/users/coralie",
        )
        allowed, reason = can_access_context(
            principal,
            ctx_owner="coralie",
            ctx_org="dica-france",
        )
        assert allowed, f"Coralie should see her DICA chat: {reason}"
