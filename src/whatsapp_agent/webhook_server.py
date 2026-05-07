from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os

PORT = 3020

from config import SESSIONS
from whatsapp_agent import media_handler


def messages_file(session: str) -> str:
    return f"messages_session{session}.jsonl"


def allowed_phone(session: str) -> str:
    return SESSIONS.get(session, SESSIONS["1"])["phone"]


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/healthz":
            # Re-read SESSIONS at request time so config edits take effect without restart.
            try:
                import config as _cfg
                sessions = list(_cfg.SESSIONS.keys())
            except Exception:
                sessions = list(SESSIONS.keys())
            body = json.dumps({
                "status": "ok",
                "sessions": sessions,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"not found")

    def do_POST(self):
        # extrai ?session= da URL
        qs = parse_qs(urlparse(self.path).query)
        session = qs.get("session", ["1"])[0]

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        with open("raw_debug.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        msg = self._parse(data, session)
        if msg:
            msg["session"] = session
            fname = messages_file(session)
            with open(fname, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            print(f"MSG|s{session}|{msg['from']}|{msg['name']}|{msg['text']}", flush=True)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def _parse(self, data, session: str = "1"):
        try:
            key = data.get("key", {})
            jid = key.get("remoteJid", "") or data.get("jid", "")

            if "@g.us" in jid or "@newsletter" in jid:
                return None

            from_me = key.get("fromMe", False)
            phone = jid.replace("@s.whatsapp.net", "").replace("@lid", "")
            sess_phone = allowed_phone(session)

            is_self_chat = from_me and phone == sess_phone
            is_authorized_incoming = not from_me and phone == sess_phone

            if not is_self_chat and not is_authorized_incoming:
                return None

            msg_block = data.get("message", {}) or {}
            msg_id = key.get("id", "")

            message_type = media_handler.detect_message_type(data)
            media_path = None
            text = None

            if message_type:
                keys = media_handler.extract_message_keys(msg_block, message_type)
                if keys:
                    media_path = media_handler.download_media(session, msg_id, keys)
                inner = msg_block.get(message_type, {}) or {}
                caption = inner.get("caption") if message_type != "audioMessage" else None
                kind_short = message_type.replace("Message", "")
                text = caption or f"[{kind_short}]"
            else:
                text = (
                    msg_block.get("conversation")
                    or msg_block.get("extendedTextMessage", {}).get("text")
                    or "[midia]"
                )

            return {
                "id":         msg_id,
                "from":       phone,
                "jid":        jid,
                "name":       data.get("pushName", ""),
                "text":       text,
                "ts":         data.get("messageTimestamp", 0),
                "fromMe":     from_me,
                "media_type": message_type,
                "media_path": media_path,
            }
        except Exception as e:
            print(f"PARSE_ERROR: {e}", flush=True)
            return None

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"[webhook] listening on :{PORT}", flush=True)
    print(f"[webhook] use ?session=1, ?session=2 etc. na URL do webhook", flush=True)
    HTTPServer(("0.0.0.0", PORT), WebhookHandler).serve_forever()
