"""Tests for update_webhooks.configure (Evolution edition)."""
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
    fake.EVOLUTION_HOST = "https://evo.example"
    fake.SESSIONS = {
        "1": {"instance": "inst-1", "token": "tok-1"},
        "2": {"instance": "inst-2", "token": "tok-2"},
    }
    monkeypatch.setitem(sys.modules, "config", fake)
    return fake


def test_configure_success(fake_config, monkeypatch):
    sys.modules.pop("whatsapp_agent.update_webhooks", None)
    from whatsapp_agent import update_webhooks

    captured = {}

    class FakeResult:
        # Evolution returns the webhook config object on success
        stdout = '{"webhook":{"enabled":true,"url":"https://example.test/?session=1","events":["MESSAGES_UPSERT"]}}'

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(update_webhooks.subprocess, "run", fake_run)

    ok = update_webhooks.configure("1", "inst-1", "tok-1")
    assert ok is True

    body = json.loads(captured["cmd"][captured["cmd"].index("-d") + 1])
    assert body["url"] == "https://example.test/?session=1"
    assert body["enabled"] is True
    assert body["events"] == ["MESSAGES_UPSERT"]

    # Endpoint must be Evolution shape: /webhook/set/{instance}
    endpoint = captured["cmd"][captured["cmd"].index("POST") + 1]
    assert endpoint == "https://evo.example/webhook/set/inst-1"

    # Header must be apikey, not Bearer
    headers = [captured["cmd"][i + 1] for i, a in enumerate(captured["cmd"]) if a == "-H"]
    assert any(h == "apikey: tok-1" for h in headers), f"missing apikey header: {headers}"


def test_configure_failure_returns_false(fake_config, monkeypatch):
    sys.modules.pop("whatsapp_agent.update_webhooks", None)
    from whatsapp_agent import update_webhooks

    class FakeResult:
        stdout = '{"status":401,"error":"Unauthorized","response":{"message":"Invalid apikey"}}'

    monkeypatch.setattr(
        update_webhooks.subprocess,
        "run",
        lambda *a, **kw: FakeResult(),
    )
    assert update_webhooks.configure("1", "inst-1", "tok-1") is False
