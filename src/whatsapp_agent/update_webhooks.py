"""
Atualiza webhook URL em todas as sessoes Evolution a partir de config.PUBLIC_WEBHOOK_URL.

Uso: python update_webhooks.py

Apos alterar PUBLIC_WEBHOOK_URL em config.py, rode este script para empurrar
a nova URL para cada instancia Evolution registrada em SESSIONS.

Endpoint: POST /webhook/set/{instance}  (Evolution API v1.x)
"""
import json
import subprocess
import sys

from config import PUBLIC_WEBHOOK_URL, EVOLUTION_HOST, SESSIONS


# MESSAGES_UPSERT cobre inbound text/image/audio/video novos.
# Adicione mais eventos se precisar (https://doc.evolution-api.com/).
WEBHOOK_EVENTS = ["MESSAGES_UPSERT"]


def configure(session_id: str, instance: str, token: str) -> bool:
    url = f"{PUBLIC_WEBHOOK_URL}/?session={session_id}"
    body = json.dumps({
        "enabled":         True,
        "url":             url,
        "webhookByEvents": False,
        "webhookBase64":   False,
        "events":          WEBHOOK_EVENTS,
    })
    endpoint = f"{EVOLUTION_HOST}/webhook/set/{instance}"
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", endpoint,
                "-H", f"apikey: {token}",
                "-H", "Content-Type: application/json",
                "-d", body,
            ],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        print(f"  [ERRO] sessao {session_id}: timeout (>15s) em {endpoint}")
        return False
    except OSError as e:
        print(f"  [ERRO] sessao {session_id}: falha ao executar curl ({e})")
        return False
    out = result.stdout.strip()
    try:
        data = json.loads(out)
    except Exception:
        print(f"  [ERRO] sessao {session_id}: resposta nao-JSON: {out!r}")
        return False
    # Evolution returns the webhook config object on success, error field on failure.
    if data.get("webhook") or data.get("enabled") is True:
        print(f"  [OK]   sessao {session_id} -> {url}")
        return True
    if "error" in data or "status" in data:
        print(f"  [ERRO] sessao {session_id}: {data}")
        return False
    # Defensive: unknown shape, treat as success if no error key.
    print(f"  [OK?]  sessao {session_id} -> {url}  resp={out[:200]}")
    return True


def main():
    if not PUBLIC_WEBHOOK_URL:
        print("ERRO: config.PUBLIC_WEBHOOK_URL vazio.")
        sys.exit(1)
    print(f"Atualizando webhooks Evolution para base: {PUBLIC_WEBHOOK_URL}")
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
