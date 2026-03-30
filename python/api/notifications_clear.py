from python.helpers.api import ApiHandler
from flask import Request, Response, session
from agent import AgentContext
from python.observability.runtime import log_observability_event, ObservabilityMetrics
try:
    from python.security.security_audit import log_security_event
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None


class NotificationsClear(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            current_username, _ = self._session_user_info()
        except Exception:
            current_username = session.get("username")
        try:
            current_org, _ = self._session_org_info()
        except Exception:
            current_org = session.get("organization")
        if not current_username or not current_org:
            ObservabilityMetrics.get().incr("notifications_denied_total")
            log_observability_event(
                event_type="notification_denied_scope",
                status="DENY",
                username=current_username,
                organization=current_org,
                reason="missing_scope",
            )
            log_security_event(
                action="notifications_clear",
                decision="DENY",
                user=current_username,
                organization=current_org,
                resource_type="notification",
                reason="missing_scope",
            )
            return {"success": False, "error": "Missing notification scope"}
        notification_manager = AgentContext.get_notification_manager()

        notification_manager.clear_all(
            target_username=current_username,
            target_organization=current_org,
        )
        log_security_event(
            action="notifications_clear",
            decision="ALLOW",
            user=current_username,
            organization=current_org,
            resource_type="notification",
        )

        return {"success": True, "message": "All notifications cleared"}
