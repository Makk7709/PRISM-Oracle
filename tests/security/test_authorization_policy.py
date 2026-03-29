from python.security.authorization import (
    AccessPrincipal,
    can_access_context,
    can_access_task,
    can_access_workspace,
)


def _owner() -> AccessPrincipal:
    return AccessPrincipal(
        username="amine",
        organization="korev-ai",
        org_role="OWNER",
        role="admin",
        workspace="/app/shared/users/amine",
    )


def _member() -> AccessPrincipal:
    return AccessPrincipal(
        username="aya",
        organization="korev-ai",
        org_role="MEMBER",
        role="admin",
        workspace="/app/shared/users/aya",
    )


def _other_org_owner() -> AccessPrincipal:
    return AccessPrincipal(
        username="nicolas",
        organization="dica-france",
        org_role="OWNER",
        role="user",
        workspace="/app/shared/users/nicolas",
    )


def test_owner_can_access_same_org_context() -> None:
    allowed, reason = can_access_context(
        _owner(),
        ctx_owner="aya",
        ctx_org="korev-ai",
    )
    assert allowed is True
    assert reason == "org_owner_access"


def test_member_cannot_access_other_member_context() -> None:
    allowed, reason = can_access_context(
        _member(),
        ctx_owner="amine",
        ctx_org="korev-ai",
    )
    assert allowed is False
    assert reason == "member_not_owner"


def test_cross_org_always_denied() -> None:
    allowed, reason = can_access_context(
        _owner(),
        ctx_owner="nicolas",
        ctx_org="dica-france",
    )
    assert allowed is False
    assert reason == "cross_organization_denied"


def test_legacy_unscoped_context_denied_for_authenticated_user() -> None:
    allowed, reason = can_access_context(
        _member(),
        ctx_owner=None,
        ctx_org=None,
    )
    assert allowed is False
    assert reason == "context_missing_organization"


def test_task_policy_same_as_context_policy() -> None:
    allowed, reason = can_access_task(
        _other_org_owner(),
        task_owner="luc",
        task_org="dica-france",
    )
    assert allowed is True
    assert reason == "org_owner_access"


def test_workspace_policy_enforces_exact_workspace() -> None:
    principal = _member()
    allowed, _ = can_access_workspace(
        principal,
        target_workspace="/app/shared/users/aya",
    )
    denied, reason = can_access_workspace(
        principal,
        target_workspace="/app/shared/users/amine",
    )
    assert allowed is True
    assert denied is False
    assert reason == "workspace_mismatch_denied"


def test_expired_or_anonymous_session_is_denied_for_scoped_resources() -> None:
    principal = AccessPrincipal(
        username=None,
        organization=None,
        org_role=None,
        role=None,
        workspace=None,
    )
    allowed, reason = can_access_context(
        principal,
        ctx_owner="aya",
        ctx_org="korev-ai",
    )
    assert allowed is False
    assert reason == "anonymous_cannot_access_scoped_context"


def test_deleted_or_malformed_principal_without_org_is_denied() -> None:
    principal = AccessPrincipal(
        username="former-user",
        organization=None,
        org_role="MEMBER",
        role="user",
        workspace="/app/shared/users/former-user",
    )
    allowed, reason = can_access_task(
        principal,
        task_owner="former-user",
        task_org="korev-ai",
    )
    assert allowed is False
    assert reason == "user_missing_organization"
