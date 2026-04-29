"""Tests for webhook payload parsing with media."""
import os
import sys
from unittest.mock import patch


def _import_ws():
    sys.modules.pop("whatsapp_agent.webhook_server", None)
    from whatsapp_agent import webhook_server
    return webhook_server


def test_text_unchanged(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "M1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "message": {"conversation": "ola"},
        "messageTimestamp": 1234,
    }
    msg = handler._parse(payload, session="1")
    assert msg["text"] == "ola"
    assert msg.get("media_path") is None
    assert msg.get("media_type") is None


def test_image_downloaded(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "IMG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "imageMessage",
        "message": {
            "imageMessage": {
                "url": "https://x/x.enc",
                "directPath": "/v/x.enc",
                "mediaKey": "K",
                "mimetype": "image/jpeg",
                "caption": "veja isso",
            }
        },
        "messageTimestamp": 1234,
    }

    def fake_download(session, msg_id, message_keys):
        os.makedirs(f"media/session{session}", exist_ok=True)
        p = f"media/session{session}/{msg_id}.jpg"
        with open(p, "wb") as f:
            f.write(b"X")
        return p

    with patch("whatsapp_agent.webhook_server.media_handler.download_media", side_effect=fake_download):
        msg = handler._parse(payload, session="1")

    assert msg["media_type"] == "imageMessage"
    assert msg["media_path"].endswith("IMG1.jpg")
    assert msg["text"] == "veja isso"


def test_audio_no_autotranscribe(fake_config, tmp_workdir):
    """Webhook only downloads. Transcription is done by Claude on demand."""
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "AUD1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "audioMessage",
        "message": {
            "audioMessage": {
                "url": "https://x/a.enc",
                "directPath": "/v/a.enc",
                "mediaKey": "K",
                "mimetype": "audio/ogg; codecs=opus",
            }
        },
        "messageTimestamp": 1234,
    }

    def fake_download(session, msg_id, message_keys):
        os.makedirs(f"media/session{session}", exist_ok=True)
        p = f"media/session{session}/{msg_id}.ogg"
        with open(p, "wb") as f:
            f.write(b"X")
        return p

    with patch("whatsapp_agent.webhook_server.media_handler.download_media", side_effect=fake_download):
        msg = handler._parse(payload, session="1")

    assert msg["media_type"] == "audioMessage"
    assert msg["media_path"].endswith("AUD1.ogg")
    assert msg["text"] == "[audio]"


def test_image_without_caption_uses_placeholder(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "IMG2", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "imageMessage",
        "message": {
            "imageMessage": {
                "url": "https://x/x.enc", "directPath": "/v/x.enc",
                "mediaKey": "K", "mimetype": "image/png",
            }
        },
        "messageTimestamp": 1234,
    }
    with patch("whatsapp_agent.webhook_server.media_handler.download_media",
               return_value="media/session1/IMG2.png"):
        msg = handler._parse(payload, session="1")
    assert msg["text"] == "[image]"
    assert msg["media_type"] == "imageMessage"
