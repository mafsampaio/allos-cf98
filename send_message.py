"""
Usage:
    python send_message.py <phone> <text> [session]
    python send_message.py --type image <phone> <path> [caption] [session]

Examples:
    python send_message.py 5511999999999 "Ola!" 1
    python send_message.py --type image 5511999999999 ./photo.jpg "veja" 1
"""
import base64
import json
import mimetypes
import os
import subprocess
import sys

from config import SESSIONS, MEGA_HOST, SIGNATURE


TEXT_ENDPOINT  = "{host}/rest/sendMessage/{instance}/text"
MEDIA_ENDPOINT = "{host}/rest/sendMessage/{instance}/mediaBase64"

EXT_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}


def _curl_json(url: str, payload_json: str, token: str) -> dict:
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", url,
                "-H", "accept: */*",
                "-H", f"Authorization: Bearer {token}",
                "-H", "Content-Type: application/json",
                "-d", payload_json,
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
    except Exception as e:
        return {"error": str(e)}
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stderr or result.stdout}


def send_text(phone: str, text: str, session: str = "1") -> dict:
    cfg = SESSIONS.get(session, SESSIONS["1"])
    url = TEXT_ENDPOINT.format(host=MEGA_HOST, instance=cfg["instance"])
    full_text = f"{text}\n\n{SIGNATURE}"
    payload = json.dumps({
        "messageData": {"to": phone, "text": full_text, "linkPreview": False}
    })
    return _curl_json(url, payload, cfg["token"])


def _detect_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in EXT_MIME:
        return EXT_MIME[ext]
    guess, _ = mimetypes.guess_type(path)
    return guess or "application/octet-stream"


def send_image(phone: str, image_path: str, caption: str = "", session: str = "1") -> dict:
    if not os.path.exists(image_path):
        return {"error": f"image not found: {image_path}"}

    cfg = SESSIONS.get(session, SESSIONS["1"])
    url = MEDIA_ENDPOINT.format(host=MEGA_HOST, instance=cfg["instance"])

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    mime = _detect_mime(image_path)
    full_caption = (f"{caption}\n\n{SIGNATURE}" if caption else SIGNATURE).strip()

    payload = json.dumps({
        "messageData": {
            "to":          phone,
            "base64":      b64,
            "fileName":    os.path.basename(image_path),
            "type":        "image",
            "caption":     full_caption,
            "gifPlayback": False,
            "mimeType":    mime,
            "viewOnce":    False,
        }
    })
    return _curl_json(url, payload, cfg["token"])


def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--type":
        if len(args) < 4 or args[1] != "image":
            print(__doc__)
            sys.exit(1)
        phone   = args[2]
        path    = args[3]
        caption = args[4] if len(args) > 4 else ""
        session = args[5] if len(args) > 5 else "1"
        print(json.dumps(send_image(phone, path, caption, session), indent=2, ensure_ascii=False))
    else:
        if len(args) < 2:
            print(__doc__)
            sys.exit(1)
        phone   = args[0]
        text    = args[1]
        session = args[2] if len(args) > 2 else "1"
        print(json.dumps(send_text(phone, text, session), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
