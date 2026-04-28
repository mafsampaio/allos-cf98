"""
Usage: python send_message.py <phone> "<text>" [session]
Example: python send_message.py 5511999999999 "Ola!" 2
"""
import sys
import json
import subprocess
import os

from config import SESSIONS, MEGA_HOST, SIGNATURE


def send_text(phone: str, text: str, session: str = "1") -> dict:
    cfg = SESSIONS.get(session, SESSIONS["1"])
    url = f"{MEGA_HOST}/rest/sendMessage/{cfg['instance']}/text"
    full_text = f"{text}\n\n{SIGNATURE}"
    payload = json.dumps({
        "messageData": {"to": phone, "text": full_text, "linkPreview": False}
    })
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST", url,
            "-H", "accept: */*",
            "-H", f"Authorization: Bearer {cfg['token']}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True, encoding="utf-8", timeout=15
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stderr or result.stdout}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python send_message.py <phone> <text> [session]")
        sys.exit(1)
    phone = sys.argv[1]
    text  = sys.argv[2]
    sess  = sys.argv[3] if len(sys.argv) > 3 else "1"
    result = send_text(phone, text, sess)
    print(json.dumps(result, indent=2, ensure_ascii=False))
