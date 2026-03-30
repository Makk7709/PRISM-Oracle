import json
import os
import threading
from types import SimpleNamespace

import pytest
from flask import session

from python.helpers.notification import NotificationManager, NotificationPriority, NotificationType
from python.observability.runtime import ObservabilityMetrics
import python.observability.runtime as obs_runtime
from python.api.notifications_mark_read import NotificationsMarkRead


@pytest.fixture(autouse=True)
def _reset_metrics_env():
    os.environ["KOREV_PERSISTENCE_BACKEND"] = "json"
    ObservabilityMetrics.reset_for_tests()
    yield
    ObservabilityMetrics.reset_for_tests()


def test_notification_observability_logs_and_correlation(monkeypatch):
    captured_messages = []
    monkeypatch.setattr(obs_runtime._OBS_LOGGER, "info", lambda msg: captured_messages.append(msg))
    manager = NotificationManager()
    created = manager.add_notification(
        NotificationType.INFO,
        NotificationPriority.NORMAL,
        "hello",
        target_username="amine",
        target_organization="korev-ai",
        task_uuid="task-1",
        correlation_id="task:task-1",
        source="test",
    )
    out = manager.output(start=0, target_username="amine", target_organization="korev-ai")
    assert created.correlation_id == "task:task-1"
    assert out[0]["correlation_id"] == "task:task-1"
    metrics = ObservabilityMetrics.get().snapshot()
    assert metrics["notifications_created_total"] >= 1

    payloads = []
    for line in captured_messages:
        try:
            payloads.append(json.loads(line))
        except Exception:
            continue
    events = {p.get("event_type") for p in payloads}
    assert "notification_created" in events
    assert "notification_delivered" in events


@pytest.mark.asyncio
async def test_notification_mark_read_denied_emits_log(monkeypatch):
    captured_messages = []
    monkeypatch.setattr(obs_runtime._OBS_LOGGER, "info", lambda msg: captured_messages.append(msg))
    manager = NotificationManager()
    manager.add_notification(
        NotificationType.INFO,
        NotificationPriority.NORMAL,
        "x",
        target_username="amine",
        target_organization="korev-ai",
        source="test",
    )

    from run_ui import create_app

    app = create_app(testing=True, secret_key="obs")
    handler = NotificationsMarkRead(app, threading.Lock())
    with app.test_request_context("/notifications_mark_read", method="POST"):
        session["authentication"] = "ok"
        session["username"] = "aya"
        session["organization"] = "korev-ai"
        result = await handler.process(
            {"notification_ids": [manager.notifications[0].id]},
            SimpleNamespace(),
        )
    assert result["success"] is True
    assert result["marked_count"] == 0
    metrics = ObservabilityMetrics.get().snapshot()
    assert metrics["notifications_denied_total"] >= 1

    payloads = []
    for line in captured_messages:
        try:
            payloads.append(json.loads(line))
        except Exception:
            continue
    assert any(p.get("event_type") == "notification_mark_read_denied" for p in payloads)
