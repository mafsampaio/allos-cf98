"""
Download de media (audio/imagem/video) via endpoint decrypt da Evolution API.

WhatsApp criptografa media end-to-end. URL .enc nao serve direto.
Evolution tem endpoint que decripta server-side e retorna base64.

Endpoint: POST /chat/getBase64FromMediaMessage/{instance}
Body: {"message": {"key": {"id": "<msg_id>"}}, "convertToMp4": false}
Resp: {"mediaType": ..., "fileName": ..., "caption": ..., "size": ..., "mimetype": ..., "base64": "..."}

Layout local: media/sessionN/<msg_id>.<ext>
"""
import base64
import json
import os
import subprocess
from typing import Optional

from config import SESSIONS, EVOLUTION_HOST


MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png":  "png",
    "image/webp": "webp",
    "image/gif":  "gif",
    "audio/ogg":  "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4":  "m4a",
    "audio/wav":  "wav",
    "video/mp4":  "mp4",
    "video/webm": "webm",
}


def ext_for_mime(mimetype: str) -> str:
    base = (mimetype or "").split(";")[0].strip().lower()
    return MIME_EXT.get(base, "bin")


def detect_message_type(payload: dict) -> Optional[str]:
    """Returns 'audioMessage' / 'imageMessage' / 'videoMessage' or None."""
    mt = payload.get("messageType", "")
    if mt in ("audioMessage", "imageMessage", "videoMessage"):
        return mt
    msg = payload.get("message", {}) or {}
    for k in ("audioMessage", "imageMessage", "videoMessage"):
        if k in msg:
            return k
    return None


def extract_message_keys(msg_block: dict, message_type: str) -> Optional[dict]:
    """Builds the messageKeys body for downloadMediaMessage. Returns None if missing fields.

    Evolution doesn't require all the Baileys fields — only message.key.id is mandatory —
    but we still extract the Baileys-shape fields for compatibility with any downstream
    consumer expecting them.
    """
    inner = msg_block.get(message_type) or {}
    required = ("mediaKey", "directPath", "url", "mimetype")
    if not all(inner.get(k) for k in required):
        return None
    return {
        "mediaKey":    inner["mediaKey"],
        "directPath":  inner["directPath"],
        "url":         inner["url"],
        "mimetype":    inner["mimetype"],
        "messageType": message_type,
    }


def decode_data_uri(s: str) -> bytes:
    """Strips 'data:MIME;base64,' prefix if present, decodes base64."""
    if not s:
        return b""
    if s.startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    return base64.b64decode(s)


def download_media(session: str, msg_id: str, message_keys: dict) -> Optional[str]:
    """
    Calls Evolution decrypt endpoint, saves bytes to media/sessionN/<msg_id>.<ext>.
    Returns local path on success, None on failure.

    Evolution v1.x: POST /chat/getBase64FromMediaMessage/{instance}
    Body is {"message": {"key": {"id": msg_id}}, "convertToMp4": false}.
    Resp has base64 directly in `base64` key.
    """
    cfg = SESSIONS.get(session, SESSIONS.get("1"))
    if not cfg:
        return None

    endpoint = f"{EVOLUTION_HOST}/chat/getBase64FromMediaMessage/{cfg['instance']}"
    payload = json.dumps({
        "message": {"key": {"id": msg_id}},
        "convertToMp4": False,
    })

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", endpoint,
                "-H", "accept: */*",
                "-H", f"apikey: {cfg['token']}",
                "-H", "Content-Type: application/json",
                "-d", payload,
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except Exception as e:
        print(f"DOWNLOAD_ERROR: {e}", flush=True)
        return None

    try:
        data = json.loads(result.stdout)
    except Exception:
        print(f"DOWNLOAD_PARSE_ERROR: {result.stdout[:200]}", flush=True)
        return None

    # Evolution returns error as status/message at top-level on failure
    if data.get("status") and data.get("status") != 200:
        print(f"DOWNLOAD_API_ERROR: {data}", flush=True)
        return None

    b64_payload = data.get("base64") or data.get("data") or ""
    try:
        raw = decode_data_uri(b64_payload)
    except Exception:
        print(f"DOWNLOAD_DECODE_ERROR: bad base64 in response", flush=True)
        return None
    if not raw:
        return None

    mimetype = data.get("mimetype") or message_keys.get("mimetype", "")
    ext = ext_for_mime(mimetype)
    safe_session = "".join(c for c in str(session) if c.isalnum())
    out_dir = os.path.join("media", f"session{safe_session}")
    os.makedirs(out_dir, exist_ok=True)
    safe_id = "".join(c for c in msg_id if c.isalnum() or c in "-_")
    out_path = os.path.join(out_dir, f"{safe_id}.{ext}")
    with open(out_path, "wb") as f:
        f.write(raw)
    return out_path
