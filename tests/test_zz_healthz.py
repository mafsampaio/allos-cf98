"""Tests for /healthz endpoint.

Note: avoid sys.modules.pop on whatsapp_agent.webhook_server here — it causes
order-dependent isolation issues with test_webhook_parser. We import once and
rely on do_GET re-reading SESSIONS dynamically.
"""
import json


def _handler():
    from whatsapp_agent import webhook_server
    handler = webhook_server.WebhookHandler.__new__(webhook_server.WebhookHandler)
    return webhook_server, handler


class _FakeWFile:
    def __init__(self):
        self.buf = b""

    def write(self, b):
        self.buf += b


def _wire(handler, path):
    captured = {"headers": []}
    handler.path = path
    handler.wfile = _FakeWFile()
    handler.send_response = lambda code: captured.setdefault("status", code)
    handler.send_header = lambda k, v: captured["headers"].append((k, v))
    handler.end_headers = lambda: None
    return captured


def test_healthz_returns_200_json(fake_config):
    _, handler = _handler()
    captured = _wire(handler, "/healthz")
    handler.do_GET()
    assert captured["status"] == 200
    body = json.loads(handler.wfile.buf.decode("utf-8"))
    assert body["status"] == "ok"
    assert isinstance(body["sessions"], list)


def test_healthz_lists_configured_sessions(fake_config):
    _, handler = _handler()
    _wire(handler, "/healthz")
    handler.do_GET()
    body = json.loads(handler.wfile.buf.decode("utf-8"))
    assert "1" in body["sessions"]


def test_healthz_query_string_ignored(fake_config):
    _, handler = _handler()
    captured = _wire(handler, "/healthz?foo=bar")
    handler.do_GET()
    assert captured["status"] == 200


def test_get_unknown_path_returns_404(fake_config):
    _, handler = _handler()
    captured = _wire(handler, "/random")
    handler.do_GET()
    assert captured["status"] == 404
