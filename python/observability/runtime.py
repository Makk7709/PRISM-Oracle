from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any


_OBS_LOGGER = logging.getLogger("evidence_observability")
if not _OBS_LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _OBS_LOGGER.addHandler(_handler)
_OBS_LOGGER.setLevel(logging.INFO)
_OBS_LOGGER.propagate = False


class ObservabilityMetrics:
    _instance: "ObservabilityMetrics | None" = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: dict[str, int] = {
            "tasks_created_total": 0,
            "tasks_claimed_total": 0,
            "tasks_claim_conflicts_total": 0,
            "tasks_completed_total": 0,
            "tasks_failed_total": 0,
            "tasks_quarantined_total": 0,
            "notifications_created_total": 0,
            "notifications_read_total": 0,
            "notifications_denied_total": 0,
            "cross_tenant_denied_total": 0,
            "audit_reports_generated_total": 0,
            "audit_reports_failed_total": 0,
            "audit_report_generation_ms_total": 0,
            "audit_report_size_bytes_total": 0,
            "replay_snapshots_captured_total": 0,
            "replay_integrity_checks_total": 0,
            "replay_integrity_failures_total": 0,
            "human_reviews_created_total": 0,
            "human_reviews_approved_total": 0,
            "human_reviews_rejected_total": 0,
            "risk_assessments_total": 0,
            "risk_assessments_low_total": 0,
            "risk_assessments_medium_total": 0,
            "risk_assessments_high_total": 0,
            "risk_assessments_critical_total": 0,
            "risk_human_review_triggered_total": 0,
        }

    @classmethod
    def get(cls) -> "ObservabilityMetrics":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def incr(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = int(self._counters.get(name, 0)) + value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
        claimed = counters.get("tasks_claimed_total", 0)
        claim_conflicts = counters.get("tasks_claim_conflicts_total", 0)
        completed = counters.get("tasks_completed_total", 0)
        failed = counters.get("tasks_failed_total", 0)
        notif_created = counters.get("notifications_created_total", 0)
        notif_read = counters.get("notifications_read_total", 0)
        denied = counters.get("notifications_denied_total", 0)
        cross_denied = counters.get("cross_tenant_denied_total", 0)
        counters["claim_conflict_rate"] = (claim_conflicts / max(claimed + claim_conflicts, 1))
        counters["task_fail_rate"] = (failed / max(completed + failed, 1))
        counters["denied_scope_rate"] = (denied / max(notif_created + denied, 1))
        counters["notification_read_gap"] = max(notif_created - notif_read, 0)
        counters["cross_tenant_denied_rate"] = (cross_denied / max(denied + cross_denied, 1))
        return counters


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_observability_event(
    *,
    event_type: str,
    status: str,
    username: str | None,
    organization: str | None,
    task_uuid: str | None = None,
    notification_id: str | None = None,
    correlation_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "timestamp": _now(),
        "event_type": event_type,
        "status": status,
        "task_uuid": task_uuid,
        "notification_id": notification_id,
        "username": username,
        "organization": organization,
        "correlation_id": correlation_id,
        "reason": reason,
    }
    if metadata:
        payload["metadata"] = metadata
    _OBS_LOGGER.info(json.dumps(payload, ensure_ascii=False))

