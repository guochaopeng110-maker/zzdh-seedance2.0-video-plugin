import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as plugin_main


class _AlwaysRunningResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"data": {"status": "running"}}


def test_poll_task_status_honors_max_attempts(monkeypatch):
    calls = {"get": 0, "sleep": 0}

    def fake_get(*args, **kwargs):
        calls["get"] += 1
        return _AlwaysRunningResponse()

    def fake_sleep(_seconds):
        calls["sleep"] += 1
        if calls["sleep"] > 3:
            raise RuntimeError("sleep_guard_triggered")

    monkeypatch.setattr(plugin_main.requests, "get", fake_get)
    monkeypatch.setattr(plugin_main.time, "sleep", fake_sleep)

    with pytest.raises(plugin_main.PluginFatalError, match="超过最大轮询次数"):
        plugin_main._poll_task_status(
            api_key="test-key",
            task_query_url="https://api.zlhub.cn/v1/task/get",
            task_id="task-123",
            timeout=30,
            max_attempts=3,
            poll_interval=1,
            progress_callback=None,
        )

    assert calls["get"] == 3
