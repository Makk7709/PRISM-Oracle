from __future__ import annotations

from dataclasses import dataclass
import threading
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional
from python.helpers.persistence.stores import get_notification_store, NotificationStore
from python.observability.runtime import ObservabilityMetrics, log_observability_event
from python.helpers.organization import normalize_org_id


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class NotificationPriority(Enum):
    NORMAL = 10
    HIGH = 20


@dataclass
class NotificationItem:
    manager: "NotificationManager"
    no: int
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    detail: str
    timestamp: datetime
    display_time: int = 3
    read: bool = False
    id: str = ""
    group: str = ""
    target_username: str | None = None
    target_organization: str | None = None
    task_uuid: str | None = None
    correlation_id: str | None = None
    source: str = "system"
    severity: str = "normal"
    status: str = "new"
    read_at: datetime | None = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.type, str):
            self.type = NotificationType(self.type)

    def mark_read(self):
        self.read = True
        self.read_at = datetime.now(timezone.utc)
        self.status = "read"
        self.manager._update_item(self.no, read=True, read_at=self.read_at, status="read")

    def output(self):
        return {
            "no": self.no,
            "id": self.id,
            "type": self.type.value if isinstance(self.type, NotificationType) else self.type,
            "priority": self.priority.value if isinstance(self.priority, NotificationPriority) else self.priority,
            "title": self.title,
            "message": self.message,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
            "display_time": self.display_time,
            "read": self.read,
            "group": self.group,
            "target_username": self.target_username,
            "target_organization": self.target_organization,
            "task_uuid": self.task_uuid,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "severity": self.severity,
            "status": self.status,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class NotificationManager:
    def __init__(self, max_notifications: int = 100):
        self._lock = threading.Lock()
        self._store: NotificationStore = get_notification_store()
        self.guid: str = self._store.guid()
        self._next_no: int = 0
        self.updates: list[int] = []
        self._items: dict[int, NotificationItem] = {}
        self.max_notifications = max_notifications

    @property
    def notifications(self) -> list[NotificationItem]:
        return sorted(self._items.values(), key=lambda n: n.no)

    def _dict_to_item(self, payload: dict[str, Any]) -> NotificationItem:
        read_at = payload.get("read_at")
        parsed_read_at = None
        if isinstance(read_at, str):
            try:
                parsed_read_at = datetime.fromisoformat(read_at)
            except Exception:
                parsed_read_at = None
        ts = payload.get("timestamp")
        parsed_ts = datetime.now(timezone.utc)
        if isinstance(ts, str):
            try:
                parsed_ts = datetime.fromisoformat(ts)
            except Exception:
                parsed_ts = datetime.now(timezone.utc)
        return NotificationItem(
            manager=self,
            no=int(payload.get("no", 0)),
            type=NotificationType(payload.get("type", NotificationType.INFO.value)),
            priority=NotificationPriority(payload.get("priority", NotificationPriority.NORMAL.value)),
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            detail=payload.get("detail", ""),
            timestamp=parsed_ts,
            display_time=int(payload.get("display_time", 3)),
            read=bool(payload.get("read", False)),
            id=payload.get("id", ""),
            group=payload.get("group", ""),
            target_username=payload.get("target_username"),
            target_organization=payload.get("target_organization"),
            task_uuid=payload.get("task_uuid"),
            correlation_id=payload.get("correlation_id"),
            source=payload.get("source", "system"),
            severity=payload.get("severity", "normal"),
            status=payload.get("status", "new"),
            read_at=parsed_read_at,
        )

    @staticmethod
    def send_notification(
        type: NotificationType,
        priority: NotificationPriority,
        message: str,
        title: str = "",
        detail: str = "",
        display_time: int = 3,
        group: str = "",
        target_username: str | None = None,
        target_organization: str | None = None,
        task_uuid: str | None = None,
        correlation_id: str | None = None,
        source: str = "system",
        severity: str = "normal",
    ) -> NotificationItem:
        from agent import AgentContext
        if not target_username or not target_organization:
            current_ctx = AgentContext.current()
            if current_ctx:
                target_username = target_username or getattr(current_ctx, "username", None)
                target_organization = target_organization or getattr(current_ctx, "organization", None)
        return AgentContext.get_notification_manager().add_notification(
            type=type,
            priority=priority,
            message=message,
            title=title,
            detail=detail,
            display_time=display_time,
            group=group,
            target_username=target_username,
            target_organization=target_organization,
            task_uuid=task_uuid,
            correlation_id=correlation_id,
            source=source,
            severity=severity,
        )

    def add_notification(
        self,
        type: NotificationType,
        priority: NotificationPriority,
        message: str,
        title: str = "",
        detail: str = "",
        display_time: int = 3,
        group: str = "",
        target_username: str | None = None,
        target_organization: str | None = None,
        task_uuid: str | None = None,
        correlation_id: str | None = None,
        source: str = "system",
        severity: str = "normal",
    ) -> NotificationItem:
        with self._lock:
            # Fail-closed for authenticated user notifications.
            # System/global notifications without explicit recipient are rejected.
            if not target_username or not target_organization:
                raise ValueError("Scoped notification requires target_username and target_organization")
            item = NotificationItem(
                manager=self,
                no=-1,
                type=NotificationType(type),
                priority=NotificationPriority(priority),
                title=title,
                message=message,
                detail=detail,
                timestamp=datetime.now(timezone.utc),
                display_time=display_time,
                group=group,
                target_username=target_username,
                target_organization=target_organization,
                task_uuid=task_uuid,
                correlation_id=correlation_id,
                source=source,
                severity=severity,
            )

            persisted = self._store.create(item.output())
            item = self._dict_to_item(persisted)
            self._items[item.no] = item
            self.guid = self._store.guid()
            self.updates = list(range(self._store.total_updates()))
            self._enforce_limit()
            ObservabilityMetrics.get().incr("notifications_created_total")
            log_observability_event(
                event_type="notification_created",
                status="ALLOW",
                username=target_username,
                organization=target_organization,
                task_uuid=task_uuid,
                notification_id=item.id,
                correlation_id=correlation_id or (f"task:{task_uuid}" if task_uuid else None),
            )

        return item

    def _enforce_limit(self):
        if len(self._items) > self.max_notifications:
            sorted_nos = sorted(self._items.keys())
            to_remove = len(self._items) - self.max_notifications
            for no in sorted_nos[:to_remove]:
                del self._items[no]

    def get_recent_notifications(
        self,
        seconds: int = 30,
        *,
        target_username: str | None,
        target_organization: str | None,
    ) -> list[NotificationItem]:
        if not target_username or not target_organization:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [
            n
            for n in self._items.values()
            if n.timestamp >= cutoff
            and self._is_visible(
                n,
                target_username=target_username,
                target_organization=target_organization,
            )
        ]

    def _is_visible(
        self,
        item: NotificationItem,
        *,
        target_username: Optional[str],
        target_organization: Optional[str],
    ) -> bool:
        if not target_username or not target_organization:
            return False
        return (
            item.target_username == target_username
            and normalize_org_id(item.target_organization) == normalize_org_id(target_organization)
        )

    def output(
        self,
        start: int | None = None,
        end: int | None = None,
        *,
        target_username: str | None = None,
        target_organization: str | None = None,
    ) -> list[dict]:
        with self._lock:
            if not target_username or not target_organization:
                return []
            if start is None:
                start = 0
            payloads = self._store.list_updates_scoped(
                username=target_username,
                organization=target_organization,
                start=start,
                end=end,
            )
            items = [self._dict_to_item(p) for p in payloads]
            for item in items:
                self._items[item.no] = item
            self.guid = self._store.guid()
            self.updates = list(
                range(
                    self._store.scoped_updates_count(
                        username=target_username,
                        organization=target_organization,
                    )
                )
            )
            if items:
                log_observability_event(
                    event_type="notification_delivered",
                    status="ALLOW",
                    username=target_username,
                    organization=target_organization,
                    metadata={
                        "count": len(items),
                        "notification_ids": [i.id for i in items[:5]],
                    },
                )
            return [item.output() for item in items]

    def _update_item(self, no: int, **kwargs):
        with self._lock:
            if no in self._items:
                item = self._items[no]
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self.updates.append(no)

    def mark_all_read(self, *, target_username: str | None, target_organization: str | None):
        with self._lock:
            if not target_username or not target_organization:
                return
            marked_count = self._store.mark_all_read(username=target_username, organization=target_organization)
            if marked_count > 0:
                ObservabilityMetrics.get().incr("notifications_read_total", marked_count)
                log_observability_event(
                    event_type="notification_read",
                    status="ALLOW",
                    username=target_username,
                    organization=target_organization,
                    reason="mark_all_read",
                    metadata={"count": marked_count},
                )
            self.updates = list(
                range(
                    self._store.scoped_updates_count(
                        username=target_username,
                        organization=target_organization,
                    )
                )
            )

    def mark_read_ids(
        self,
        notification_ids: list[str],
        *,
        target_username: str | None,
        target_organization: str | None,
    ) -> int:
        with self._lock:
            if not target_username or not target_organization:
                return 0
            marked = self._store.mark_read_ids(
                username=target_username,
                organization=target_organization,
                notification_ids=notification_ids,
            )
            if marked > 0:
                ObservabilityMetrics.get().incr("notifications_read_total", marked)
                log_observability_event(
                    event_type="notification_read",
                    status="ALLOW",
                    username=target_username,
                    organization=target_organization,
                    reason="mark_read_ids",
                    metadata={"count": marked},
                )
            self.updates = list(
                range(
                    self._store.scoped_updates_count(
                        username=target_username,
                        organization=target_organization,
                    )
                )
            )
            return marked

    def clear_all(self, *, target_username: str | None, target_organization: str | None):
        with self._lock:
            if not target_username or not target_organization:
                return
            self._store.clear_all(username=target_username, organization=target_organization)
            # keep local cache eventually-consistent; do a scoped drop
            self._items = {
                no: item for no, item in self._items.items()
                if not (
                    item.target_username == target_username
                    and normalize_org_id(item.target_organization) == normalize_org_id(target_organization)
                )
            }
            self.updates = list(
                range(
                    self._store.scoped_updates_count(
                        username=target_username,
                        organization=target_organization,
                    )
                )
            )

    def all_visible(
        self,
        *,
        target_username: str | None,
        target_organization: str | None,
    ) -> list[NotificationItem]:
        with self._lock:
            if not target_username or not target_organization:
                return []
            payloads = self._store.list_scoped(username=target_username, organization=target_organization)
            items = [self._dict_to_item(p) for p in payloads]
            for item in items:
                self._items[item.no] = item
            self.guid = self._store.guid()
            self.updates = list(
                range(
                    self._store.scoped_updates_count(
                        username=target_username,
                        organization=target_organization,
                    )
                )
            )
            return items

    def get_notifications_by_type(
        self,
        type: NotificationType,
        *,
        target_username: str | None,
        target_organization: str | None,
    ) -> list[NotificationItem]:
        if not target_username or not target_organization:
            return []
        return [
            n
            for n in self._items.values()
            if n.type == type
            and self._is_visible(
                n,
                target_username=target_username,
                target_organization=target_organization,
            )
        ]
