import json
import threading
from concurrent.futures import ThreadPoolExecutor

from python.helpers.persistence.stores import RedisTaskStore, RedisNotificationStore


class _FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def watch(self, key):
        return None

    def unwatch(self):
        return None

    def get(self, key):
        return self.redis.get(key)

    def multi(self):
        return None

    def set(self, key, value):
        self.ops.append(("set", key, value))
        return self

    def sadd(self, key, value):
        self.ops.append(("sadd", key, value))
        return self

    def delete(self, key):
        self.ops.append(("delete", key, None))
        return self

    def srem(self, key, value):
        self.ops.append(("srem", key, value))
        return self

    def execute(self):
        for op, key, value in self.ops:
            if op == "set":
                self.redis.set(key, value)
            elif op == "sadd":
                self.redis.sadd(key, value)
            elif op == "delete":
                self.redis.delete(key)
            elif op == "srem":
                self.redis.srem(key, value)
            elif op == "zrem":
                self.redis.zrem(key, value)
            elif op == "zadd":
                self.redis.zadd(key, value)
        self.ops = []
        return True

    def zrem(self, key, value):
        self.ops.append(("zrem", key, value))
        return self

    def zadd(self, key, mapping):
        self.ops.append(("zadd", key, mapping))
        return self


class _FakeRedis:
    def __init__(self):
        self.lock = threading.RLock()
        self.kv = {}
        self.sets = {}
        self.zsets = {}
        self.counters = {}

    def pipeline(self):
        return _FakePipeline(self)

    def get(self, key):
        with self.lock:
            return self.kv.get(key)

    def set(self, key, value):
        with self.lock:
            self.kv[key] = value
            return True

    def smembers(self, key):
        with self.lock:
            return set(self.sets.get(key, set()))

    def sadd(self, key, value):
        with self.lock:
            self.sets.setdefault(key, set()).add(value)
            return 1

    def srem(self, key, value):
        with self.lock:
            self.sets.setdefault(key, set()).discard(value)
            return 1

    def delete(self, key):
        with self.lock:
            self.kv.pop(key, None)
            self.sets.pop(key, None)
            self.zsets.pop(key, None)
            return 1

    def incr(self, key):
        with self.lock:
            self.counters[key] = int(self.counters.get(key, 0)) + 1
            return self.counters[key]

    def zadd(self, key, mapping):
        with self.lock:
            z = self.zsets.setdefault(key, {})
            z.update(mapping)
            return 1

    def zrange(self, key, start, end):
        with self.lock:
            z = self.zsets.get(key, {})
            ordered = [k for k, _ in sorted(z.items(), key=lambda kv: kv[1])]
            if end == -1:
                return ordered[start:]
            return ordered[start : end + 1]

    def zrem(self, key, member):
        with self.lock:
            z = self.zsets.get(key, {})
            z.pop(member, None)
            return 1

    def zcard(self, key):
        with self.lock:
            return len(self.zsets.get(key, {}))


def test_redis_task_store_claim_is_single_winner():
    fake = _FakeRedis()
    store = RedisTaskStore(redis_url="redis://fake")
    store._client = fake
    task = {"uuid": "t1", "state": "idle", "username": "jeremie", "organization": "dica", "workspace": "/w"}
    store.put_task(task)

    def _claim():
        return store.claim_task("t1")

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(lambda _: _claim(), [0, 1]))

    assert sum(1 for r in results if r) == 1
    current = [t for t in store.list_tasks() if t.get("uuid") == "t1"][0]
    assert current["state"] == "running"


def test_redis_notification_store_scope_and_mark_read():
    fake = _FakeRedis()
    store = RedisNotificationStore(redis_url="redis://fake")
    store._client = fake
    n1 = store.create(
        {
            "id": "n1",
            "type": "info",
            "priority": 10,
            "title": "ok",
            "message": "m1",
            "detail": "",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "display_time": 3,
            "read": False,
            "group": "g",
            "target_username": "amine",
            "target_organization": "korev-ai",
            "task_uuid": None,
            "source": "test",
            "severity": "normal",
            "status": "new",
            "read_at": None,
        }
    )
    store.create({**n1, "id": "n2", "target_username": "aya"})

    mine = store.list_scoped(username="amine", organization="korev-ai")
    other = store.list_scoped(username="aya", organization="korev-ai")
    assert len(mine) == 1
    assert len(other) == 1

    marked = store.mark_read_ids(username="amine", organization="korev-ai", notification_ids=["n1", "n2"])
    assert marked == 1
    mine_after = store.list_scoped(username="amine", organization="korev-ai")
    assert mine_after[0]["read"] is True
    updates = store.list_updates_scoped(username="amine", organization="korev-ai", start=0, end=None)
    assert len(updates) >= 2
    paged = store.list_updates_scoped(username="amine", organization="korev-ai", start=1, end=1)
    assert len(paged) == 1
