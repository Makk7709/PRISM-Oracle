from __future__ import annotations

import json
import os
import threading
import fcntl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from python.helpers.files import get_abs_path, make_dirs, read_file, write_file
from python.observability.runtime import ObservabilityMetrics, log_observability_event
from python.helpers.organization import normalize_org_id


def _org_eq(a, b) -> bool:
    """Normalized organization comparison for store filtering."""
    return normalize_org_id(a) == normalize_org_id(b)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def list_tasks(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def put_task(self, task: dict[str, Any]) -> None:
        raise NotImplementedError

    def put_tasks(self, tasks: list[dict[str, Any]]) -> None:
        for task in tasks:
            self.put_task(task)

    def delete_task(self, task_uuid: str) -> None:
        raise NotImplementedError

    def claim_task(self, task_uuid: str) -> bool:
        raise NotImplementedError


class NotificationStore:
    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def list_scoped(self, *, username: str, organization: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_updates_scoped(self, *, username: str, organization: str, start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def mark_read_ids(self, *, username: str, organization: str, notification_ids: list[str]) -> int:
        raise NotImplementedError

    def mark_all_read(self, *, username: str, organization: str) -> int:
        raise NotImplementedError

    def clear_all(self, *, username: str, organization: str) -> int:
        raise NotImplementedError

    def total_updates(self) -> int:
        raise NotImplementedError

    def scoped_updates_count(self, *, username: str, organization: str) -> int:
        raise NotImplementedError

    def guid(self) -> str:
        raise NotImplementedError


class JsonTaskStore(TaskStore):
    def __init__(self, path: Optional[str] = None):
        self.path = path or get_abs_path("tmp/scheduler", "tasks.json")
        self._lock = threading.RLock()

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            if not os.path.exists(self.path):
                return []
            raw = read_file(self.path)
            if not raw.strip():
                return []
            data = json.loads(raw)
            tasks = data.get("tasks", [])
            return tasks if isinstance(tasks, list) else []

    def put_task(self, task: dict[str, Any]) -> None:
        with self._lock:
            tasks = self.list_tasks()
            by_uuid = {t.get("uuid"): t for t in tasks if isinstance(t, dict)}
            by_uuid[task.get("uuid")] = task
            self.put_tasks(list(by_uuid.values()))

    def put_tasks(self, tasks: list[dict[str, Any]]) -> None:
        with self._lock:
            if not os.path.exists(self.path):
                make_dirs(self.path)
            payload = {"tasks": tasks}
            write_file(self.path, json.dumps(payload, ensure_ascii=False))

    def delete_task(self, task_uuid: str) -> None:
        with self._lock:
            tasks = [t for t in self.list_tasks() if t.get("uuid") != task_uuid]
            self.put_tasks(tasks)

    def claim_task(self, task_uuid: str) -> bool:
        # Cross-process claim guard for JSON backend.
        lock_path = f"{self.path}.claim.lock"
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            try:
                tasks = self.list_tasks()
                changed = False
                claimed = False
                now = _now_iso()
                for task in tasks:
                    if task.get("uuid") != task_uuid:
                        continue
                    if task.get("state") == "running":
                        claimed = False
                        break
                    task["state"] = "running"
                    task["updated_at"] = now
                    changed = True
                    claimed = True
                    break
                if changed:
                    self.put_tasks(tasks)
                return claimed
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


class RedisTaskStore(TaskStore):
    def __init__(self, redis_url: Optional[str] = None, key_prefix: str = "evidence:scheduler:"):
        self.redis_url = redis_url or os.environ.get("KOREV_REDIS_URL", "redis://localhost:6379/0")
        self.key_prefix = key_prefix
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis

            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _tasks_key(self) -> str:
        return f"{self.key_prefix}tasks"

    def _task_key(self, task_uuid: str) -> str:
        return f"{self.key_prefix}task:{task_uuid}"

    def list_tasks(self) -> list[dict[str, Any]]:
        client = self._get_client()
        task_ids = client.smembers(self._tasks_key()) or set()
        out: list[dict[str, Any]] = []
        for task_uuid in task_ids:
            raw = client.get(self._task_key(task_uuid))
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except Exception:
                continue
        return out

    def put_task(self, task: dict[str, Any]) -> None:
        client = self._get_client()
        task_uuid = task.get("uuid")
        if not task_uuid:
            raise ValueError("task uuid required")
        pipe = client.pipeline()
        pipe.set(self._task_key(task_uuid), json.dumps(task, ensure_ascii=False))
        pipe.sadd(self._tasks_key(), task_uuid)
        pipe.execute()

    def delete_task(self, task_uuid: str) -> None:
        client = self._get_client()
        pipe = client.pipeline()
        pipe.delete(self._task_key(task_uuid))
        pipe.srem(self._tasks_key(), task_uuid)
        pipe.execute()

    def claim_task(self, task_uuid: str) -> bool:
        client = self._get_client()
        key = self._task_key(task_uuid)
        retries = 5
        for _ in range(retries):
            try:
                with client.pipeline() as pipe:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if not raw:
                        pipe.unwatch()
                        return False
                    task = json.loads(raw)
                    if task.get("state") == "running":
                        pipe.unwatch()
                        return False
                    task["state"] = "running"
                    task["updated_at"] = _now_iso()
                    pipe.multi()
                    pipe.set(key, json.dumps(task, ensure_ascii=False))
                    pipe.execute()
                    return True
            except Exception as exc:
                # Retry only optimistic lock conflicts. For other failures fail-closed.
                if "WatchError" in exc.__class__.__name__:
                    continue
                ObservabilityMetrics.get().incr("tasks_failed_total")
                log_observability_event(
                    event_type="task_claim_store_error",
                    status="DENY",
                    username=None,
                    organization=None,
                    task_uuid=task_uuid,
                    correlation_id=f"task:{task_uuid}",
                    reason=exc.__class__.__name__,
                )
                return False
        return False


class InMemoryNotificationStore(NotificationStore):
    def __init__(self):
        self._lock = threading.RLock()
        self._guid = os.urandom(16).hex()
        self._next_no = 0
        self._items: dict[int, dict[str, Any]] = {}
        self._updates: list[int] = []

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            item = dict(item)
            item["no"] = self._next_no
            self._next_no += 1
            self._items[item["no"]] = item
            self._updates.append(item["no"])
            return item

    def _scoped(self, username: str, organization: str) -> list[dict[str, Any]]:
        return [
            n for _, n in sorted(self._items.items(), key=lambda kv: kv[0])
            if n.get("target_username") == username and _org_eq(n.get("target_organization"), organization)
        ]

    def list_scoped(self, *, username: str, organization: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._scoped(username, organization))

    def list_updates_scoped(self, *, username: str, organization: str, start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            end = len(self._updates) if end is None else end
            out: list[dict[str, Any]] = []
            for no in self._updates[start:end]:
                item = self._items.get(no)
                if not item:
                    continue
                if item.get("target_username") == username and _org_eq(item.get("target_organization"), organization):
                    out.append(item)
            return out

    def mark_read_ids(self, *, username: str, organization: str, notification_ids: list[str]) -> int:
        with self._lock:
            ids = set(notification_ids)
            changed = 0
            for no, item in self._items.items():
                if item.get("id") not in ids:
                    continue
                if item.get("target_username") != username or not _org_eq(item.get("target_organization"), organization):
                    continue
                if item.get("read"):
                    continue
                item["read"] = True
                item["status"] = "read"
                item["read_at"] = _now_iso()
                self._updates.append(no)
                changed += 1
            return changed

    def mark_all_read(self, *, username: str, organization: str) -> int:
        with self._lock:
            changed = 0
            for no, item in self._items.items():
                if item.get("target_username") != username or not _org_eq(item.get("target_organization"), organization):
                    continue
                if item.get("read"):
                    continue
                item["read"] = True
                item["status"] = "read"
                item["read_at"] = _now_iso()
                self._updates.append(no)
                changed += 1
            return changed

    def clear_all(self, *, username: str, organization: str) -> int:
        with self._lock:
            to_delete = [
                no for no, item in self._items.items()
                if item.get("target_username") == username and _org_eq(item.get("target_organization"), organization)
            ]
            for no in to_delete:
                del self._items[no]
                self._updates.append(no)
            return len(to_delete)

    def total_updates(self) -> int:
        with self._lock:
            return len(self._updates)

    def scoped_updates_count(self, *, username: str, organization: str) -> int:
        with self._lock:
            count = 0
            for no in self._updates:
                item = self._items.get(no)
                if not item:
                    continue
                if item.get("target_username") == username and _org_eq(item.get("target_organization"), organization):
                    count += 1
            return count

    def guid(self) -> str:
        return self._guid


class RedisNotificationStore(NotificationStore):
    def __init__(self, redis_url: Optional[str] = None, key_prefix: str = "evidence:notifications:"):
        self.redis_url = redis_url or os.environ.get("KOREV_REDIS_URL", "redis://localhost:6379/0")
        self.key_prefix = key_prefix
        self._client = None
        self._guid_cache = None

    def _get_client(self):
        if self._client is None:
            import redis

            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _counter_key(self) -> str:
        return f"{self.key_prefix}counter"

    def _guid_key(self) -> str:
        return f"{self.key_prefix}guid"

    def _notif_key(self, no: int) -> str:
        return f"{self.key_prefix}item:{no}"

    def _scope_index(self, username: str, organization: str) -> str:
        return f"{self.key_prefix}scope:{organization}:{username}"

    def _scope_updates(self, username: str, organization: str) -> str:
        return f"{self.key_prefix}scope_updates:{organization}:{username}"

    def _scope_seq(self, username: str, organization: str) -> str:
        return f"{self.key_prefix}scope_seq:{organization}:{username}"

    def _append_scope_update(self, username: str, organization: str, no: int) -> None:
        client = self._get_client()
        seq = int(client.incr(self._scope_seq(username, organization)))
        member = f"{seq}:{no}"
        client.zadd(self._scope_updates(username, organization), {member: seq})

    def _trim_scope_streams(self, username: str, organization: str, max_items: int = 1000, max_updates: int = 5000) -> None:
        client = self._get_client()
        scope_key = self._scope_index(username, organization)
        updates_key = self._scope_updates(username, organization)

        scoped_ids = client.zrange(scope_key, 0, -1) or []
        overflow_items = max(0, len(scoped_ids) - max_items)
        if overflow_items > 0:
            old_ids = scoped_ids[:overflow_items]
            pipe = client.pipeline()
            for old_no in old_ids:
                pipe.delete(self._notif_key(int(old_no)))
                pipe.zrem(scope_key, old_no)  # type: ignore[attr-defined]
            pipe.execute()

        scoped_updates = client.zrange(updates_key, 0, -1) or []
        overflow_updates = max(0, len(scoped_updates) - max_updates)
        if overflow_updates > 0:
            pipe = client.pipeline()
            for member in scoped_updates[:overflow_updates]:
                pipe.zrem(updates_key, member)  # type: ignore[attr-defined]
            pipe.execute()

    def guid(self) -> str:
        if self._guid_cache:
            return self._guid_cache
        client = self._get_client()
        g = client.get(self._guid_key())
        if not g:
            g = os.urandom(16).hex()
            client.set(self._guid_key(), g)
        self._guid_cache = g
        return g

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        no = int(client.incr(self._counter_key()) - 1)
        username = item["target_username"]
        organization = item["target_organization"]
        payload = dict(item)
        payload["no"] = no
        key = self._notif_key(no)
        pipe = client.pipeline()
        pipe.set(key, json.dumps(payload, ensure_ascii=False))
        pipe.zadd(self._scope_index(username, organization), {str(no): no})
        pipe.execute()
        self._append_scope_update(username, organization, no)
        self._trim_scope_streams(username, organization)
        self.guid()
        return payload

    def list_scoped(self, *, username: str, organization: str) -> list[dict[str, Any]]:
        client = self._get_client()
        nos = client.zrange(self._scope_index(username, organization), 0, -1) or []
        out: list[dict[str, Any]] = []
        for no in nos:
            raw = client.get(self._notif_key(int(no)))
            if not raw:
                continue
            out.append(json.loads(raw))
        return out

    def list_updates_scoped(self, *, username: str, organization: str, start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
        client = self._get_client()
        if end is None:
            end = -1
        members = client.zrange(self._scope_updates(username, organization), start, end)
        out: list[dict[str, Any]] = []
        for member in members:
            try:
                no = int(str(member).split(":", 1)[1])
            except Exception:
                continue
            raw = client.get(self._notif_key(no))
            if not raw:
                continue
            out.append(json.loads(raw))
        return out

    def mark_read_ids(self, *, username: str, organization: str, notification_ids: list[str]) -> int:
        ids = set(notification_ids)
        changed = 0
        client = self._get_client()
        for item in self.list_scoped(username=username, organization=organization):
            if item.get("id") not in ids:
                continue
            if item.get("read"):
                continue
            item["read"] = True
            item["status"] = "read"
            item["read_at"] = _now_iso()
            client.set(self._notif_key(int(item["no"])), json.dumps(item, ensure_ascii=False))
            self._append_scope_update(username, organization, int(item["no"]))
            changed += 1
        self._trim_scope_streams(username, organization)
        return changed

    def mark_all_read(self, *, username: str, organization: str) -> int:
        changed = 0
        client = self._get_client()
        for item in self.list_scoped(username=username, organization=organization):
            if item.get("read"):
                continue
            item["read"] = True
            item["status"] = "read"
            item["read_at"] = _now_iso()
            client.set(self._notif_key(int(item["no"])), json.dumps(item, ensure_ascii=False))
            self._append_scope_update(username, organization, int(item["no"]))
            changed += 1
        self._trim_scope_streams(username, organization)
        return changed

    def clear_all(self, *, username: str, organization: str) -> int:
        client = self._get_client()
        items = self.list_scoped(username=username, organization=organization)
        pipe = client.pipeline()
        for item in items:
            pipe.delete(self._notif_key(int(item["no"])))
        pipe.delete(self._scope_index(username, organization))
        pipe.delete(self._scope_updates(username, organization))
        pipe.delete(self._scope_seq(username, organization))
        pipe.execute()
        return len(items)

    def total_updates(self) -> int:
        client = self._get_client()
        value = client.get(self._counter_key())
        return int(value or "0")

    def scoped_updates_count(self, *, username: str, organization: str) -> int:
        client = self._get_client()
        return int(client.zcard(self._scope_updates(username, organization)))  # type: ignore[attr-defined]


@dataclass(frozen=True)
class PersistenceConfig:
    backend: str
    redis_url: str

    @classmethod
    def from_env(cls) -> "PersistenceConfig":
        return cls(
            backend=os.environ.get("KOREV_PERSISTENCE_BACKEND", "json").strip().lower(),
            redis_url=os.environ.get("KOREV_REDIS_URL", "redis://localhost:6379/0"),
        )


_task_store_singleton: TaskStore | None = None
_notification_store_singleton: NotificationStore | None = None
_store_lock = threading.RLock()


def get_task_store() -> TaskStore:
    global _task_store_singleton
    with _store_lock:
        if _task_store_singleton is not None:
            return _task_store_singleton
        cfg = PersistenceConfig.from_env()
        if cfg.backend == "redis":
            _task_store_singleton = RedisTaskStore(redis_url=cfg.redis_url)
        else:
            _task_store_singleton = JsonTaskStore()
        return _task_store_singleton


def get_notification_store() -> NotificationStore:
    global _notification_store_singleton
    with _store_lock:
        cfg = PersistenceConfig.from_env()
        if cfg.backend == "redis":
            if _notification_store_singleton is not None:
                return _notification_store_singleton
            _notification_store_singleton = RedisNotificationStore(redis_url=cfg.redis_url)
            return _notification_store_singleton
        else:
            # Per-instance store for deterministic unit tests in JSON mode.
            return InMemoryNotificationStore()
