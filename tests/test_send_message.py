"""Tests for send_message routing (Evolution edition)."""
import json
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("whatsapp_agent.send_message", None)
    from whatsapp_agent import send_message
    return send_message


def test_send_text_uses_sendText_endpoint(fake_config):
    sm = _import()
    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"key":{"id":"x"}}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_text("5511888888888", "ola", "1")

    assert result == {"key": {"id": "x"}}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert "/message/sendText/inst1" in url


def test_send_text_uses_apikey_header(fake_config):
    sm = _import()
    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok":true}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "ola", "1")

    # Header must be `apikey: <token>`, never `Authorization: Bearer ...`
    headers = [captured["args"][i + 1] for i, a in enumerate(captured["args"]) if a == "-H"]
    assert any(h == "apikey: tok1" for h in headers), f"missing apikey header: {headers}"
    assert not any("Authorization" in h for h in headers), f"unexpected Bearer header: {headers}"


def test_send_image_posts_sendMedia_with_evolution_payload(fake_config, tmp_workdir):
    sm = _import()
    img = tmp_workdir / "x.jpg"
    img.write_bytes(b"IMGBYTES")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"key":{"id":"img1"}}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_image("5511888888888", str(img), caption="legenda", session="1")

    assert result == {"key": {"id": "img1"}}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert "/message/sendMedia/inst1" in url

    body_idx = captured["args"].index("-d") + 1
    body = json.loads(captured["args"][body_idx])
    assert body["number"] == "5511888888888"
    media = body["mediaMessage"]
    assert media["media"] == "SU1HQllURVM="  # base64 of "IMGBYTES"
    assert media["fileName"] == "x.jpg"
    assert media["mediatype"] == "image"
    assert "legenda" in media["caption"]


def test_send_image_missing_file_returns_error(fake_config):
    sm = _import()
    result = sm.send_image("5511888888888", "/nonexistent.jpg", session="1")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_send_image_rejects_oversized_file(fake_config, tmp_workdir, monkeypatch):
    sm = _import()
    big = tmp_workdir / "big.jpg"
    big.write_bytes(b"X" * 1024)

    monkeypatch.setattr(sm, "MAX_IMAGE_BYTES", 100)
    result = sm.send_image("5511888888888", str(big), session="1")
    assert "error" in result
    assert "too large" in result["error"].lower()


def test_send_text_strips_pre_existing_signature(fake_config):
    sm = _import()
    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok":true}', stderr="", returncode=0)
    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "Tudo certo. *Claude Code*", "1")
    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    text = body["textMessage"]["text"]
    assert text.count("*Claude Code*") == 1, f"Signature deve aparecer 1x, veio: {text!r}"
    assert text.startswith("Tudo certo.")


def test_send_text_appends_signature_when_missing(fake_config):
    sm = _import()
    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok":true}', stderr="", returncode=0)
    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "ola", "1")
    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    text = body["textMessage"]["text"]
    assert text.count("*Claude Code*") == 1
