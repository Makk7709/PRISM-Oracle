import threading
from types import SimpleNamespace

import pytest

from python.api.observability_metrics import ObservabilityMetrics as ObservabilityMetricsApi
from python.observability.runtime import ObservabilityMetrics


@pytest.mark.asyncio
async def test_observability_metrics_api_returns_snapshot():
    ObservabilityMetrics.reset_for_tests()
    metrics = ObservabilityMetrics.get()
    metrics.incr("tasks_created_total", 2)

    from run_ui import create_app

    app = create_app(testing=True, secret_key="obs-metrics")
    handler = ObservabilityMetricsApi(app, threading.Lock())
    result = await handler.process({}, SimpleNamespace())
    assert result["ok"] is True
    assert result["metrics"]["tasks_created_total"] == 2
    assert "claim_conflict_rate" in result["metrics"]
