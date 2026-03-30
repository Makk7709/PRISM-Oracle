from abc import abstractmethod
import json
import os
import threading
from typing import Union, TypedDict, Dict, Any
from attr import dataclass
from flask import Request, Response, jsonify, Flask, session, request, send_file, g, current_app
from agent import AgentContext
from initialize import initialize_agent
from python.helpers.print_style import PrintStyle
from python.helpers.errors import format_error
from python.security.authorization import (
    AccessPrincipal,
    can_access_context,
    can_access_task,
    can_access_workspace,
)
try:
    from python.observability.runtime import ObservabilityMetrics, log_observability_event
except Exception:  # pragma: no cover - compatibility for deployments without observability module
    class ObservabilityMetrics:  # type: ignore[override]
        @staticmethod
        def get():
            class _Noop:
                @staticmethod
                def incr(*args, **kwargs):
                    return None

            return _Noop()

    def log_observability_event(**kwargs):
        return None
try:
    from python.security.security_audit import log_security_event
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None
from werkzeug.serving import make_server

Input = dict
Output = Union[Dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app: Flask, thread_lock: threading.Lock):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_admin(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output:
        pass

    async def handle_request(self, request: Request) -> Response:
        try:
            # input data from request based on type
            input_data: Input = {}
            if request.is_json:
                try:
                    if request.data:  # Check if there's any data
                        input_data = request.get_json()
                    # If empty or not valid JSON, use empty dict
                except Exception as e:
                    # Just log the error and continue with empty input
                    PrintStyle().print(f"Error parsing JSON: {str(e)}")
                    input_data = {}
            else:
                # input_data = {"data": request.get_data(as_text=True)}
                input_data = {}


            # process via handler
            output = await self.process(input_data, request)

            # return output based on type
            if isinstance(output, Response):
                return output
            else:
                response_json = json.dumps(output)
                return Response(
                    response=response_json, status=200, mimetype="application/json"
                )

            # return exceptions with 500
        except Exception as e:
            error = format_error(e)
            try:
                request_id = getattr(g, "request_id", "-")
            except RuntimeError:
                request_id = "-"
            PrintStyle.error(f"API error [{request_id}] {request.path}: {error}")
            if os.getenv("KOREV_PRODUCTION", "false").lower() == "true":
                return Response(
                    response='{"error":"Internal server error"}',
                    status=500,
                    mimetype="application/json",
                )
            return Response(response=error, status=500, mimetype="text/plain")

    def _resolve_session_scope(self) -> dict[str, str | None]:
        """
        Resolve session scope from session source-of-truth and durable user metadata.
        Keeps fail-closed semantics: if organization cannot be resolved, returns None for it.
        """
        username = session.get("username")
        workspace = session.get("workspace")
        organization = session.get("organization")
        org_role = session.get("org_role")
        role = session.get("role")

        if username:
            cfg = None
            try:
                cfg = self.app.config
            except Exception:
                try:
                    cfg = current_app.config
                except Exception:
                    cfg = None
            user_mgr = cfg.get("USER_MANAGER") if cfg else None
            ws_mgr = cfg.get("WORKSPACE_MANAGER") if cfg else None

            if not organization and user_mgr:
                try:
                    organization = user_mgr.get_organization(username)
                    if organization:
                        session["organization"] = organization
                except Exception:
                    organization = organization

            if not org_role and user_mgr:
                try:
                    org_role = user_mgr.get_org_role(username)
                    if org_role:
                        session["org_role"] = org_role
                except Exception:
                    org_role = org_role

            if not workspace and ws_mgr:
                try:
                    workspace = ws_mgr.ensure_workspace(username)
                    if workspace:
                        session["workspace"] = workspace
                except Exception:
                    workspace = workspace
            if not organization:
                log_observability_event(
                    event_type="invalid_session_scope",
                    status="DENY",
                    username=username,
                    organization=organization,
                    reason="missing_organization_after_scope_resolution",
                )
                ObservabilityMetrics.get().incr("notifications_denied_total")

        return {
            "username": username,
            "workspace": workspace,
            "organization": organization,
            "org_role": org_role,
            "role": role,
        }

    def _session_user_info(self) -> tuple[str | None, str | None]:
        """Extract username and workspace from the current Flask session."""
        try:
            scope = self._resolve_session_scope()
            return scope.get("username"), scope.get("workspace")
        except RuntimeError:
            return None, None

    def _session_org_info(self) -> tuple[str | None, str | None]:
        """Extract organization and org_role from the current Flask session."""
        try:
            scope = self._resolve_session_scope()
            return scope.get("organization"), scope.get("org_role")
        except RuntimeError:
            return None, None

    def _principal(self) -> AccessPrincipal:
        username, workspace = None, None
        organization, org_role, role = None, None, None
        try:
            scope = self._resolve_session_scope()
            username = scope.get("username")
            workspace = scope.get("workspace")
            organization = scope.get("organization")
            org_role = scope.get("org_role")
            role = scope.get("role")
        except RuntimeError:
            role = None
        return AccessPrincipal(
            username=username,
            organization=organization,
            org_role=org_role,
            role=role,
            workspace=workspace,
        )

    def _is_admin(self) -> bool:
        """True if the current session user has admin role."""
        try:
            return session.get("role") == "admin"
        except RuntimeError:
            return False

    def _is_org_owner(self) -> bool:
        """True if the current session user is OWNER of their organization."""
        try:
            return session.get("org_role") == "OWNER"
        except RuntimeError:
            return False

    def _is_owner(self, ctx: AgentContext, username: str | None) -> bool:
        """Compatibility helper backed by centralized authorization policy."""
        principal = self._principal()
        allowed, _ = can_access_context(
            principal,
            ctx_owner=getattr(ctx, "username", None),
            ctx_org=getattr(ctx, "organization", None),
        )
        return allowed

    def _authorize_context_access(self, ctx: AgentContext, action: str) -> tuple[bool, str]:
        principal = self._principal()
        allowed, reason = can_access_context(
            principal,
            ctx_owner=getattr(ctx, "username", None),
            ctx_org=getattr(ctx, "organization", None),
        )
        log_security_event(
            action=action,
            decision="ALLOW" if allowed else "DENY",
            user=principal.username,
            organization=principal.organization,
            resource_type="context",
            resource_id=getattr(ctx, "id", None),
            reason=reason,
        )
        if not allowed:
            ObservabilityMetrics.get().incr("cross_tenant_denied_total")
            log_observability_event(
                event_type="cross_tenant_access_denied",
                status="DENY",
                username=principal.username,
                organization=principal.organization,
                task_uuid=getattr(ctx, "id", None),
                reason=reason,
            )
        return allowed, reason

    def _authorize_task_access(self, task: Any, action: str) -> tuple[bool, str]:
        principal = self._principal()
        allowed, reason = can_access_task(
            principal,
            task_owner=getattr(task, "username", None),
            task_org=getattr(task, "organization", None),
        )
        log_security_event(
            action=action,
            decision="ALLOW" if allowed else "DENY",
            user=principal.username,
            organization=principal.organization,
            resource_type="task",
            resource_id=getattr(task, "uuid", None),
            reason=reason,
        )
        if not allowed:
            ObservabilityMetrics.get().incr("cross_tenant_denied_total")
            log_observability_event(
                event_type="cross_tenant_access_denied",
                status="DENY",
                username=principal.username,
                organization=principal.organization,
                task_uuid=getattr(task, "uuid", None),
                reason=reason,
            )
        return allowed, reason

    def _authorize_workspace_access(self, target_workspace: str | None, action: str) -> tuple[bool, str]:
        principal = self._principal()
        allowed, reason = can_access_workspace(
            principal,
            target_workspace=target_workspace,
        )
        log_security_event(
            action=action,
            decision="ALLOW" if allowed else "DENY",
            user=principal.username,
            organization=principal.organization,
            resource_type="workspace",
            resource_id=target_workspace,
            reason=reason,
        )
        if not allowed:
            ObservabilityMetrics.get().incr("cross_tenant_denied_total")
            log_observability_event(
                event_type="cross_tenant_access_denied",
                status="DENY",
                username=principal.username,
                organization=principal.organization,
                reason=reason,
                metadata={"workspace": target_workspace},
            )
        return allowed, reason

    def use_context(self, ctxid: str, create_if_not_exists: bool = True):
        username, workspace = self._session_user_info()
        organization, _ = self._session_org_info()
        with self.thread_lock:
            def _new_context(*, config, id=None, set_current=False):
                try:
                    kwargs = {
                        "config": config,
                        "set_current": set_current,
                        "username": username,
                        "workspace": workspace,
                        "organization": organization,
                    }
                    if id is not None:
                        kwargs["id"] = id
                    return AgentContext(**kwargs)
                except TypeError:
                    # Backward compatibility for deployments where AgentContext
                    # does not yet support organization constructor argument.
                    kwargs = {
                        "config": config,
                        "set_current": set_current,
                        "username": username,
                        "workspace": workspace,
                    }
                    if id is not None:
                        kwargs["id"] = id
                    context = AgentContext(**kwargs)
                    try:
                        setattr(context, "organization", organization)
                    except Exception:
                        pass
                    return context

            if not ctxid:
                owned = [
                    c for c in AgentContext.all()
                    if self._is_owner(c, username)
                ]
                first = owned[0] if owned else None
                if first:
                    if username and getattr(first, "username", None) == username and not getattr(first, "workspace", None):
                        first.workspace = workspace
                    if organization and getattr(first, "organization", None) == organization and not getattr(first, "workspace", None):
                        first.workspace = workspace
                    AgentContext.use(first.id)
                    return first
                context = _new_context(
                    config=initialize_agent(),
                    set_current=True,
                )
                return context
            got = AgentContext.use(ctxid)
            if got:
                allowed, reason = self._authorize_context_access(got, action="context_use")
                if not allowed:
                    raise Exception(f"Context {ctxid} not found")
                if username and getattr(got, "username", None) == username and not getattr(got, "workspace", None):
                    got.workspace = workspace
                if organization and getattr(got, "organization", None) == organization and not getattr(got, "workspace", None):
                    got.workspace = workspace
                return got
            if create_if_not_exists:
                context = _new_context(
                    config=initialize_agent(),
                    id=ctxid,
                    set_current=True,
                )
                return context
            else:
                raise Exception(f"Context {ctxid} not found")
            
