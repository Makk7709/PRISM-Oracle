import asyncio
import os
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

from flask import Flask, session

from python.api.poll import Poll
from python.api.scheduler_task_create import SchedulerTaskCreate


class _FakeNotificationManager:
    guid = "notif-guid"
    updates = []

    def output(self, start=0, target_username=None, target_organization=None):
        return []


class _FakeContext:
    def __init__(self, ctx_id: str, username: str | None, created_at: str):
        self.id = ctx_id
        self.username = username
        self.type = SimpleNamespace(value="user")
        self.created_at = created_at
        self.log = SimpleNamespace(guid=f"log-{ctx_id}", updates=[], logs=[], progress=0, progress_active=False)
        self.paused = False
        self.last_message = created_at
        self.name = f"ctx-{ctx_id}"

    def output(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "no": 0,
            "log_guid": self.log.guid,
            "log_version": 0,
            "log_length": 0,
            "paused": False,
            "last_message": self.last_message,
            "type": "user",
        }


class _FakeScheduler:
    def __init__(self, tasks):
        self._tasks = tasks
        self.save = AsyncMock()
        self.update_task = AsyncMock()

    async def reload(self):
        return None

    def serialize_all_tasks(self):
        return list(self._tasks)


def _build_poll_handler() -> tuple[Flask, Poll]:
    app = Flask("test-app")
    app.secret_key = os.urandom(16)  # secret éphémère (jamais en dur — SonarQube S6779)
    handler = Poll(app, threading.Lock())
    return app, handler


def test_poll_returns_owned_task_without_loaded_context(monkeypatch):
    app, handler = _build_poll_handler()
    scheduler = _FakeScheduler(
        [
            {
                "uuid": "task-1",
                "context_id": "task-1",
                "username": "jeremie",
                "organization": "dica",
                "name": "Reminder Jeremie",
                "state": "idle",
                "type": "scheduled",
                "system_prompt": "sys",
                "prompt": "remind me",
                "attachments": [],
                "created_at": "2026-03-27T10:00:00+00:00",
                "updated_at": "2026-03-27T10:00:00+00:00",
                "last_run": None,
                "last_result": None,
                "schedule": {"minute": "*", "hour": "*", "day": "*", "month": "*", "weekday": "*", "timezone": "UTC"},
            }
        ]
    )

    fake_agent_context = SimpleNamespace(
        _contexts={},
        get=lambda _ctxid: None,
        get_notification_manager=lambda: _FakeNotificationManager(),
    )
    fake_ctx_type = SimpleNamespace(BACKGROUND="background")

    monkeypatch.setattr("python.api.poll.TaskScheduler.get", lambda: scheduler)
    monkeypatch.setattr("python.api.poll.AgentContext", fake_agent_context)
    monkeypatch.setattr("python.api.poll.AgentContextType", fake_ctx_type)

    with app.test_request_context("/poll", method="POST"):
        session["username"] = "jeremie"
        session["organization"] = "dica"
        session["org_role"] = "MEMBER"
        result = asyncio.run(handler.process({"context": "", "log_from": 0, "notifications_from": 0}, SimpleNamespace()))

    assert "tasks" in result
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["uuid"] == "task-1"
    assert result["tasks"][0]["task_name"] == "Reminder Jeremie"


def test_poll_hides_tasks_from_other_users(monkeypatch):
    app, handler = _build_poll_handler()
    scheduler = _FakeScheduler(
        [
            {
                "uuid": "task-1",
                "context_id": "task-1",
                "username": "alice",
                "organization": "other",
                "name": "Alice reminder",
                "state": "idle",
                "type": "scheduled",
                "system_prompt": "sys",
                "prompt": "alice",
                "attachments": [],
                "created_at": "2026-03-27T10:00:00+00:00",
                "updated_at": "2026-03-27T10:00:00+00:00",
                "last_run": None,
                "last_result": None,
                "schedule": {"minute": "*", "hour": "*", "day": "*", "month": "*", "weekday": "*", "timezone": "UTC"},
            }
        ]
    )

    fake_agent_context = SimpleNamespace(
        _contexts={},
        get=lambda _ctxid: None,
        get_notification_manager=lambda: _FakeNotificationManager(),
    )
    fake_ctx_type = SimpleNamespace(BACKGROUND="background")

    monkeypatch.setattr("python.api.poll.TaskScheduler.get", lambda: scheduler)
    monkeypatch.setattr("python.api.poll.AgentContext", fake_agent_context)
    monkeypatch.setattr("python.api.poll.AgentContextType", fake_ctx_type)

    with app.test_request_context("/poll", method="POST"):
        session["username"] = "jeremie"
        session["organization"] = "dica"
        session["org_role"] = "MEMBER"
        result = asyncio.run(handler.process({"context": "", "log_from": 0, "notifications_from": 0}, SimpleNamespace()))

    assert "tasks" in result
    assert result["tasks"] == []


def test_scheduler_task_create_persists_task_owner(monkeypatch):
    app = Flask("test-app-create")
    app.secret_key = os.urandom(16)  # secret éphémère (jamais en dur — SonarQube S6779)
    handler = SchedulerTaskCreate(app, threading.Lock())

    captured = {}

    class _Scheduler:
        async def reload(self):
            return None

        async def add_task(self, task):
            captured["task"] = task
            return None

        def get_task_by_uuid(self, _task_uuid):
            return captured.get("task")

    monkeypatch.setattr("python.api.scheduler_task_create.TaskScheduler.get", lambda: _Scheduler())

    with app.test_request_context("/scheduler_task_create", method="POST"):
        session["username"] = "jeremie"
        session["workspace"] = "/app/shared/users/jeremie"
        session["organization"] = "dica"
        session["org_role"] = "MEMBER"
        result = asyncio.run(
            handler.process(
                {
                    "name": "Jeremie daily task",
                    "system_prompt": "sys",
                    "prompt": "Do task",
                    "schedule": {"minute": "0", "hour": "*", "day": "*", "month": "*", "weekday": "*", "timezone": "UTC"},
                },
                SimpleNamespace(),
            )
        )

    assert result.get("ok") is True
    task = captured["task"]
    assert task.username == "jeremie"
    assert task.organization == "dica"
    assert task.workspace == "/app/shared/users/jeremie"
