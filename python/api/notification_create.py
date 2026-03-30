from python.helpers.api import ApiHandler
from flask import Request, Response, session
from python.helpers.notification import NotificationManager, NotificationPriority, NotificationType
from python.observability.runtime import ObservabilityMetrics, log_observability_event
try:
    from python.security.security_audit import log_security_event
except Exception:  # pragma: no cover - legacy deployments without audit module
    def log_security_event(**kwargs):
        return None


class NotificationCreate(ApiHandler):
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
                reason="missing_notification_scope",
            )
            log_security_event(
                action="notification_create",
                decision="DENY",
                user=current_username,
                organization=current_org,
                resource_type="notification",
                reason="missing_notification_scope",
            )
            return {"success": False, "error": "Missing notification scope"}

        # Extract notification data
        notification_type = input.get("type", NotificationType.INFO.value)
        priority = input.get("priority", NotificationPriority.NORMAL.value)
        message = input.get("message", "")
        title = input.get("title", "")
        detail = input.get("detail", "")
        display_time = input.get("display_time", 3)  # Default to 3 seconds
        group = input.get("group", "")  # Group parameter for notification grouping

        # Validate required fields
        if not message:
            return {"success": False, "error": "Message is required"}

        # Validate display_time
        try:
            display_time = int(display_time)
            if display_time <= 0:
                display_time = 3  # Reset to default if invalid
        except (ValueError, TypeError):
            display_time = 3  # Reset to default if not convertible to int

        # Validate notification type
        try:
            if isinstance(notification_type, str):
                notification_type = NotificationType(notification_type.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid notification type: {notification_type}",
            }

        # Create notification using the appropriate helper method
        try:
            notification = NotificationManager.send_notification(
                notification_type,
                priority,
                message,
                title,
                detail,
                display_time,
                group,
                target_username=current_username,
                target_organization=current_org,
                source="api_notification_create",
                severity="normal",
            )
            log_observability_event(
                event_type="notification_created",
                status="ALLOW",
                username=current_username,
                organization=current_org,
                notification_id=notification.id,
                correlation_id=notification.correlation_id,
            )

            return {
                "success": True,
                "notification_id": notification.id,
                "message": "Notification created successfully",
            }

        except Exception as e:
            ObservabilityMetrics.get().incr("notifications_denied_total")
            log_security_event(
                action="notification_create",
                decision="DENY",
                user=current_username,
                organization=current_org,
                resource_type="notification",
                reason=str(e),
            )
            return {
                "success": False,
                "error": f"Failed to create notification: {str(e)}",
            }
