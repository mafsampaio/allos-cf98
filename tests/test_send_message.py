"""Tests for send_message routing."""
import json
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("send_message", None)
    import send_message
    return send_message


def test_send_text_uses_text_endpoint(fake_config):
    sm = _import()
    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok": true}', stderr="", returncode=0)

    with patch("send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_text("5511888888888", "ola", "1")

    assert result == {"ok": True}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert url.endswith("/text")


def test_send_image_posts_mediaBase64_with_correct_payload(fake_config, tmp_workdir):
    sm = _import()
    img = tmp_workdir / "x.jpg"
    img.write_bytes(b"IMGBYTES")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"error": false}', stderr="", returncode=0)

    with patch("send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_image("5511888888888", str(img), caption="legenda", session="1")

    assert result == {"error": False}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert "/mediaBase64" in url

    body_idx = captured["args"].index("-d") + 1
    body_raw = captured["args"][body_idx]
    body = json.loads(body_raw)
    md = body["messageData"]
    assert md["to"] == "5511888888888"
    assert md["base64"] == "SU1HQllURVM="  # base64 of "IMGBYTES"
    assert md["fileName"] == "x.jpg"
    assert md["type"] == "image"
    assert "legenda" in md["caption"]
    assert md["mimeType"] == "image/jpeg"
    assert md["gifPlayback"] is False
    assert md["viewOnce"] is False


def test_send_image_missing_file_returns_error(fake_config):
    sm = _import()
    result = sm.send_image("5511888888888", "/nonexistent.jpg", session="1")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_send_image_detects_mime_from_extension(fake_config, tmp_workdir):
    sm = _import()
    png = tmp_workdir / "x.png"
    png.write_bytes(b"PNGDATA")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok": true}', stderr="", returncode=0)

    with patch("send_message.subprocess.run", side_effect=fake_run):
        sm.send_image("5511888888888", str(png), session="1")

    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    assert body["messageData"]["mimeType"] == "image/png"


def test_send_image_rejects_oversized_file(fake_config, tmp_workdir, monkeypatch):
    sm = _import()
    big = tmp_workdir / "big.jpg"
    big.write_bytes(b"X" * 1024)  # only 1KB but we'll lower the limit

    monkeypatch.setattr(sm, "MAX_IMAGE_BYTES", 100)  # force trigger
    result = sm.send_image("5511888888888", str(big), session="1")
    assert "error" in result
    assert "too large" in result["error"].lower()
