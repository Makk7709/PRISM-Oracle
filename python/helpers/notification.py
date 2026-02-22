from dataclasses import dataclass
import threading
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum


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

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.type, str):
            self.type = NotificationType(self.type)

    def mark_read(self):
        self.read = True
        self.manager._update_item(self.no, read=True)

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
        }


class NotificationManager:
    def __init__(self, max_notifications: int = 100):
        self._lock = threading.Lock()
        self.guid: str = str(uuid.uuid4())
        self._next_no: int = 0
        self.updates: list[int] = []
        self._items: dict[int, NotificationItem] = {}
        self.max_notifications = max_notifications

    @property
    def notifications(self) -> list[NotificationItem]:
        return sorted(self._items.values(), key=lambda n: n.no)

    @staticmethod
    def send_notification(
        type: NotificationType,
        priority: NotificationPriority,
        message: str,
        title: str = "",
        detail: str = "",
        display_time: int = 3,
        group: str = "",
    ) -> NotificationItem:
        from agent import AgentContext
        return AgentContext.get_notification_manager().add_notification(
            type, priority, message, title, detail, display_time, group
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
    ) -> NotificationItem:
        with self._lock:
            no = self._next_no
            self._next_no += 1

            item = NotificationItem(
                manager=self,
                no=no,
                type=NotificationType(type),
                priority=NotificationPriority(priority),
                title=title,
                message=message,
                detail=detail,
                timestamp=datetime.now(timezone.utc),
                display_time=display_time,
                group=group,
            )

            self._items[no] = item
            self.updates.append(no)
            self._enforce_limit()

        return item

    def _enforce_limit(self):
        if len(self._items) > self.max_notifications:
            sorted_nos = sorted(self._items.keys())
            to_remove = len(self._items) - self.max_notifications
            for no in sorted_nos[:to_remove]:
                del self._items[no]

    def get_recent_notifications(self, seconds: int = 30) -> list[NotificationItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [n for n in self._items.values() if n.timestamp >= cutoff]

    def output(self, start: int | None = None, end: int | None = None) -> list[dict]:
        with self._lock:
            if start is None:
                start = 0
            if end is None:
                end = len(self.updates)

            out = []
            seen = set()
            for no in self.updates[start:end]:
                if no not in seen and no in self._items:
                    out.append(self._items[no].output())
                    seen.add(no)

            return out

    def _update_item(self, no: int, **kwargs):
        with self._lock:
            if no in self._items:
                item = self._items[no]
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self.updates.append(no)

    def mark_all_read(self):
        with self._lock:
            for item in self._items.values():
                item.read = True

    def clear_all(self):
        with self._lock:
            self._items = {}
            self.updates = []
            self._next_no = 0
            self.guid = str(uuid.uuid4())

    def get_notifications_by_type(self, type: NotificationType) -> list[NotificationItem]:
        return [n for n in self._items.values() if n.type == type]
