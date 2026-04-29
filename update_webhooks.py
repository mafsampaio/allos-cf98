"""
Atualiza webhook URL em todas as sessoes megaAPI a partir de config.PUBLIC_WEBHOOK_URL.

Uso: python update_webhooks.py

Apos alterar PUBLIC_WEBHOOK_URL em config.py, rode este script para empurrar
a nova URL para cada instancia megaAPI registrada em SESSIONS.
"""
import json
import subprocess
import sys

from config import PUBLIC_WEBHOOK_URL, MEGA_HOST, SESSIONS


def configure(session_id: str, instance: str, token: str) -> bool:
    url = f"{PUBLIC_WEBHOOK_URL}/?session={session_id}"
    body = json.dumps({
        "messageData": {
            "webhookUrl": url,
            "webhookEnabled": True,
        }
    })
    endpoint = f"{MEGA_HOST}/rest/webhook/{instance}/configWebhook"
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST", endpoint,
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", body,
        ],
        capture_output=True, text=True, timeout=15,
    )
    out = result.stdout.strip()
    try:
        data = json.loads(out)
    except Exception:
        print(f"  [ERRO] sessao {session_id}: resposta nao-JSON: {out!r}")
        return False
    if data.get("error") is False:
        print(f"  [OK]   sessao {session_id} -> {url}")
        return True
    print(f"  [ERRO] sessao {session_id}: {data}")
    return False


def main():
    if not PUBLIC_WEBHOOK_URL:
        print("ERRO: config.PUBLIC_WEBHOOK_URL vazio.")
        sys.exit(1)
    print(f"Atualizando webhooks megaAPI para base: {PUBLIC_WEBHOOK_URL}")
    print("")
    failures = 0
    for sid, cfg in SESSIONS.items():
        if not cfg.get("instance") or not cfg.get("token"):
            print(f"  [SKIP] sessao {sid}: instance/token vazios")
            continue
        if not configure(sid, cfg["instance"], cfg["token"]):
            failures += 1
    print("")
    print(f"Done. {failures} falha(s).")
    sys.exit(0 if failures == 0 else 2)


if __name__ == "__main__":
    main()
