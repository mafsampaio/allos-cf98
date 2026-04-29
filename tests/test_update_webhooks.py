"""Tests for update_webhooks.configure (no real network)."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def fake_config(monkeypatch, tmp_path):
    fake = types.ModuleType("config")
    fake.PUBLIC_WEBHOOK_URL = "https://example.test"
    fake.MEGA_HOST = "https://mega.example"
    fake.SESSIONS = {
        "1": {"instance": "inst-1", "token": "tok-1"},
        "2": {"instance": "inst-2", "token": "tok-2"},
    }
    monkeypatch.setitem(sys.modules, "config", fake)
    return fake


def test_configure_success(fake_config, monkeypatch):
    import update_webhooks

    captured = {}

    class FakeResult:
        stdout = '{"error": false, "message": "Webhooks configured"}'

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(update_webhooks.subprocess, "run", fake_run)

    ok = update_webhooks.configure("1", "inst-1", "tok-1")
    assert ok is True
    body = json.loads(captured["cmd"][captured["cmd"].index("-d") + 1])
    assert body["messageData"]["webhookUrl"] == "https://example.test/?session=1"
    assert body["messageData"]["webhookEnabled"] is True


def test_configure_failure_returns_false(fake_config, monkeypatch):
    import update_webhooks

    class FakeResult:
        stdout = '{"error": true, "message": "bad token"}'

    monkeypatch.setattr(
        update_webhooks.subprocess,
        "run",
        lambda *a, **kw: FakeResult(),
    )
    assert update_webhooks.configure("1", "inst-1", "tok-1") is False
