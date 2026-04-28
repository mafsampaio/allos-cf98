"""Tests for media_handler."""
import base64
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("media_handler", None)
    import media_handler
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
    media_handler = _import()

    body = base64.b64encode(b"AUDIOPAYLOAD").decode()
    response = '{"error": false, "message": "ok", "data": "data:audio/ogg;base64,' + body + '"}'

    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("media_handler.subprocess.run", return_value=fake_proc):
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
    media_handler = _import()

    response = '{"error": true, "message": "media not found"}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "image/jpeg", "messageType": "imageMessage",
            },
        )
    assert path is None
