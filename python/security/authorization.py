from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from python.helpers.organization import normalize_org_id


@dataclass(frozen=True)
class AccessPrincipal:
    username: str | None
    organization: str | None
    org_role: str | None
    role: str | None
    workspace: str | None
    compliance_role: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.username)

    @property
    def is_org_owner(self) -> bool:
        return self.org_role == "OWNER"

    @property
    def organization_id(self) -> str:
        """Canonical normalized org slug for comparisons."""
        return normalize_org_id(self.organization)


def can_access_context(
    principal: AccessPrincipal,
    *,
    ctx_owner: Optional[str],
    ctx_org: Optional[str],
) -> tuple[bool, str]:
    if not principal.is_authenticated:
        if ctx_owner is None and ctx_org is None:
            return True, "anonymous_unscoped_context"
        return False, "anonymous_cannot_access_scoped_context"

    if not ctx_org:
        return False, "context_missing_organization"

    if not principal.organization:
        return False, "user_missing_organization"

    if normalize_org_id(ctx_org) != principal.organization_id:
        return False, "cross_organization_denied"

    if principal.is_org_owner:
        return True, "org_owner_access"

    if not ctx_owner:
        return False, "context_missing_owner_for_member"

    if ctx_owner != principal.username:
        return False, "member_not_owner"

    return True, "member_owner_access"


COMPLIANCE_ROLES = frozenset({"DPO", "RSSI", "COMPLIANCE_OFFICER"})


def can_access_audit_reports(
    principal: AccessPrincipal,
    *,
    target_org: Optional[str],
) -> tuple[bool, str]:
    """Check if the principal can access audit reports for target_org.

    Access is granted to:
      - Org OWNER
      - Users with a compliance role (DPO, RSSI, COMPLIANCE_OFFICER)
    """
    if not principal.is_authenticated:
        return False, "anonymous_audit_access_denied"

    if not target_org or not principal.organization:
        return False, "audit_missing_organization"

    if normalize_org_id(target_org) != principal.organization_id:
        return False, "audit_cross_organization_denied"

    if principal.is_org_owner:
        return True, "audit_org_owner_access"

    if principal.compliance_role and principal.compliance_role in COMPLIANCE_ROLES:
        return True, f"audit_{principal.compliance_role.lower()}_access"

    return False, "audit_access_denied_no_compliance_role"


def can_access_task(
    principal: AccessPrincipal,
    *,
    task_owner: Optional[str],
    task_org: Optional[str],
) -> tuple[bool, str]:
    return can_access_context(
        principal,
        ctx_owner=task_owner,
        ctx_org=task_org,
    )


def can_access_workspace(
    principal: AccessPrincipal,
    *,
    target_workspace: Optional[str],
) -> tuple[bool, str]:
    if not principal.is_authenticated:
        return False, "anonymous_workspace_access_denied"

    if not principal.workspace:
        return False, "user_missing_workspace"

    if not target_workspace:
        return False, "target_workspace_missing"

    if target_workspace != principal.workspace:
        return False, "workspace_mismatch_denied"

    return True, "workspace_owner_access"


def validate_task_scope(
    *,
    task_owner: Optional[str],
    task_org: Optional[str],
    task_workspace: Optional[str],
) -> tuple[bool, str]:
    if not task_owner:
        return False, "task_missing_owner"
    if not task_org:
        return False, "task_missing_organization"
    if not task_workspace:
        return False, "task_missing_workspace"
    return True, "task_scope_valid"
