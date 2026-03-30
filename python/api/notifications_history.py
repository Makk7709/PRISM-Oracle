from python.helpers.api import ApiHandler
from flask import Request, Response, session
from agent import AgentContext
from python.observability.runtime import log_observability_event, ObservabilityMetrics
try:
    from python.security.security_audit import log_security_event
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None


class NotificationsHistory(ApiHandler):
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
        notification_manager = AgentContext.get_notification_manager()
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
                action="notifications_history",
                decision="DENY",
                user=current_username,
                organization=current_org,
                resource_type="notification",
                reason="missing_scope",
            )
            return {"notifications": [], "guid": notification_manager.guid, "count": 0}
        notifications = notification_manager.all_visible(
            target_username=current_username,
            target_organization=current_org,
        )
        log_security_event(
            action="notifications_history",
            decision="ALLOW",
            user=current_username,
            organization=current_org,
            resource_type="notification",
            reason=f"count={len(notifications)}",
        )

        # Return all notifications for history modal
        return {
            "notifications": [n.output() for n in notifications],
            "guid": notification_manager.guid,
            "count": len(notifications),
        }
