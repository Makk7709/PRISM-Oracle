from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AccessPrincipal:
    username: str | None
    organization: str | None
    org_role: str | None
    role: str | None
    workspace: str | None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.username)

    @property
    def is_org_owner(self) -> bool:
        return self.org_role == "OWNER"


def can_access_context(
    principal: AccessPrincipal,
    *,
    ctx_owner: Optional[str],
    ctx_org: Optional[str],
) -> tuple[bool, str]:
    # API key / no-user flows are allowed only for unscoped contexts.
    if not principal.is_authenticated:
        if ctx_owner is None and ctx_org is None:
            return True, "anonymous_unscoped_context"
        return False, "anonymous_cannot_access_scoped_context"

    # Fail closed for legacy/unscoped contexts in authenticated mode.
    if not ctx_org:
        return False, "context_missing_organization"

    if not principal.organization:
        return False, "user_missing_organization"

    if ctx_org != principal.organization:
        return False, "cross_organization_denied"

    if principal.is_org_owner:
        return True, "org_owner_access"

    if not ctx_owner:
        return False, "context_missing_owner_for_member"

    if ctx_owner != principal.username:
        return False, "member_not_owner"

    return True, "member_owner_access"


def can_access_task(
    principal: AccessPrincipal,
    *,
    task_owner: Optional[str],
    task_org: Optional[str],
) -> tuple[bool, str]:
    # Same authorization model as contexts.
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
