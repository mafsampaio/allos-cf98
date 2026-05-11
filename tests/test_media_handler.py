"""Tests for media_handler (Evolution edition)."""
import base64
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("whatsapp_agent.media_handler", None)
    from whatsapp_agent import media_handler
    return media_handler


def test_extract_message_keys_from_audio(fake_config):
    media_handler = _import()
    msg_block = {
        "audioMessage": {
            "url": "https://x/file.enc",
            "mimetype": "audio/ogg; codecs=opus",
            "mediaKey": "MK==",
            "directPath": "/v/path.enc",
        }
    }
    keys = media_handler.extract_message_keys(msg_block, "audioMessage")
    assert keys == {
        "mediaKey": "MK==",
        "directPath": "/v/path.enc",
        "url": "https://x/file.enc",
        "mimetype": "audio/ogg; codecs=opus",
        "messageType": "audioMessage",
    }


def test_ext_for_mime(fake_config):
    media_handler = _import()
    assert media_handler.ext_for_mime("audio/ogg; codecs=opus") == "ogg"
    assert media_handler.ext_for_mime("image/jpeg") == "jpg"
    assert media_handler.ext_for_mime("image/png") == "png"
    assert media_handler.ext_for_mime("video/mp4") == "mp4"
    assert media_handler.ext_for_mime("application/octet-stream") == "bin"


def test_strip_data_uri(fake_config):
    media_handler = _import()
    raw = base64.b64encode(b"HELLO").decode()
    uri = f"data:audio/ogg; codecs=opus;base64,{raw}"
    decoded = media_handler.decode_data_uri(uri)
    assert decoded == b"HELLO"


def test_decode_data_uri_pure_base64_fallback(fake_config):
    media_handler = _import()
    raw = base64.b64encode(b"WORLD").decode()
    decoded = media_handler.decode_data_uri(raw)
    assert decoded == b"WORLD"


def test_download_media_writes_file(fake_config, tmp_workdir):
    """Evolution returns base64 directly (no data: URI prefix needed)."""
    media_handler = _import()

    body = base64.b64encode(b"AUDIOPAYLOAD").decode()
    response = '{"mediaType":"audio","mimetype":"audio/ogg; codecs=opus","base64":"' + body + '"}'

    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="1",
            msg_id="ABC123",
            message_keys={
                "mediaKey": "MK==",
                "directPath": "/v/x.enc",
                "url": "https://x/x.enc",
                "mimetype": "audio/ogg; codecs=opus",
                "messageType": "audioMessage",
            },
        )

    assert path is not None
    assert os.path.exists(path)
    assert path.endswith("ABC123.ogg")
    assert "session1" in path.replace("\\", "/")
    with open(path, "rb") as f:
        assert f.read() == b"AUDIOPAYLOAD"


def test_download_media_returns_none_on_api_error(fake_config, tmp_workdir):
    """Evolution returns status != 200 on failure."""
    media_handler = _import()

    response = '{"status":404,"error":"Not Found","response":{"message":"media not found"}}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "image/jpeg", "messageType": "imageMessage",
            },
        )
    assert path is None


def test_download_media_handles_malformed_base64(fake_config, tmp_workdir):
    media_handler = _import()
    response = '{"mediaType":"audio","mimetype":"audio/ogg","base64":"not!!valid%%base64"}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "audio/ogg; codecs=opus", "messageType": "audioMessage",
            },
        )
    assert path is None


def test_download_media_sanitises_session(fake_config, tmp_workdir):
    """Path traversal in session must be neutralised."""
    media_handler = _import()
    body = base64.b64encode(b"PAYLOAD").decode()
    response = '{"mediaType":"audio","mimetype":"audio/ogg","base64":"' + body + '"}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="../../evil",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "audio/ogg; codecs=opus", "messageType": "audioMessage",
            },
        )
    assert path is not None
    norm = path.replace("\\", "/")
    assert ".." not in norm
    assert "evil" in norm
    assert norm.startswith("media/") or "/media/session" in norm


def test_download_media_uses_apikey_header(fake_config, tmp_workdir):
    media_handler = _import()
    body = base64.b64encode(b"X").decode()
    response = '{"mediaType":"audio","mimetype":"audio/ogg","base64":"' + body + '"}'

    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return MagicMock(stdout=response, stderr="", returncode=0)

    with patch("whatsapp_agent.media_handler.subprocess.run", side_effect=fake_run):
        media_handler.download_media(
            session="1",
            msg_id="Y",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "audio/ogg", "messageType": "audioMessage",
            },
        )

    headers = [captured["cmd"][i + 1] for i, a in enumerate(captured["cmd"]) if a == "-H"]
    assert any(h == "apikey: tok1" for h in headers), f"missing apikey header: {headers}"
    endpoint = captured["cmd"][captured["cmd"].index("POST") + 1]
    assert "/chat/getBase64FromMediaMessage/inst1" in endpoint
