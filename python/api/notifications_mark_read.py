from python.helpers.api import ApiHandler
from flask import Request, Response, session
from agent import AgentContext
from python.observability.runtime import ObservabilityMetrics, log_observability_event
try:
    from python.security.security_audit import log_security_event
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None


class NotificationsMarkRead(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        notification_ids = input.get("notification_ids", [])
        mark_all = input.get("mark_all", False)
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
                event_type="notification_mark_read_denied",
                status="DENY",
                username=current_username,
                organization=current_org,
                reason="missing_scope",
            )
            log_security_event(
                action="notifications_mark_read",
                decision="DENY",
                user=current_username,
                organization=current_org,
                resource_type="notification",
                reason="missing_scope",
            )
            return {"success": False, "error": "Missing notification scope"}

        notification_manager = AgentContext.get_notification_manager()

        if mark_all:
            notification_manager.mark_all_read(
                target_username=current_username,
                target_organization=current_org,
            )
            log_security_event(
                action="notifications_mark_read_all",
                decision="ALLOW",
                user=current_username,
                organization=current_org,
                resource_type="notification",
            )
            return {"success": True, "message": "All notifications marked as read"}

        if not notification_ids:
            return {"success": False, "error": "No notification IDs provided"}

        marked_count = notification_manager.mark_read_ids(
            notification_ids=list(notification_ids),
            target_username=current_username,
            target_organization=current_org,
        )
        if notification_ids and marked_count == 0:
            ObservabilityMetrics.get().incr("notifications_denied_total")
            log_observability_event(
                event_type="notification_mark_read_denied",
                status="DENY",
                username=current_username,
                organization=current_org,
                reason="cross_scope_or_not_found",
                metadata={"requested_count": len(notification_ids)},
            )
        elif marked_count > 0:
            log_observability_event(
                event_type="notification_read",
                status="ALLOW",
                username=current_username,
                organization=current_org,
                metadata={"count": marked_count},
            )
        log_security_event(
            action="notifications_mark_read",
            decision="ALLOW",
            user=current_username,
            organization=current_org,
            resource_type="notification",
            reason=f"marked={marked_count}",
        )

        return {
            "success": True,
            "marked_count": marked_count,
            "message": f"Marked {marked_count} notifications as read"
        }
