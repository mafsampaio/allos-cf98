from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os

PORT = 3020

from config import SESSIONS


def messages_file(session: str) -> str:
    return f"messages_session{session}.jsonl"


def allowed_phone(session: str) -> str:
    return SESSIONS.get(session, SESSIONS["1"])["phone"]


class WebhookHandler(BaseHTTPRequestHandler):
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

            # ignorar grupos e newsletters
            if "@g.us" in jid or "@newsletter" in jid:
                return None

            from_me = key.get("fromMe", False)
            phone = jid.replace("@s.whatsapp.net", "").replace("@lid", "")
            sess_phone = allowed_phone(session)

            is_self_chat = from_me and phone == sess_phone
            is_authorized_incoming = not from_me and phone == sess_phone

            if not is_self_chat and not is_authorized_incoming:
                return None

            msg = data.get("message", {})
            text = (
                msg.get("conversation")
                or msg.get("extendedTextMessage", {}).get("text")
                or "[midia]"
            )
            return {
                "id": key.get("id"),
                "from": phone,
                "jid": jid,
                "name": data.get("pushName", ""),
                "text": text,
                "ts": data.get("messageTimestamp", 0),
                "fromMe": from_me,
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
