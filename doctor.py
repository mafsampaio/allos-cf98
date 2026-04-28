"""
Diagnostico do agente WhatsApp.

Roda checks rapidos e diz exatamente o que esta quebrado.

Usage: python doctor.py
"""
import json
import os
import shutil
import socket
import subprocess
import sys
from urllib.request import urlopen


def ok(msg): print(f"  [OK]   {msg}")
def warn(msg): print(f"  [WARN] {msg}")
def err(msg): print(f"  [ERRO] {msg}")


def check_python():
    v = sys.version_info
    if v >= (3, 8):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    err(f"Python {v.major}.{v.minor} muito antigo. Precisa 3.8+")
    return False


def check_curl():
    if shutil.which("curl"):
        ok("curl disponivel")
        return True
    err("curl nao encontrado no PATH")
    return False


def check_ngrok():
    if shutil.which("ngrok"):
        ok("ngrok disponivel")
        return True
    warn("ngrok nao encontrado no PATH (necessario pra start.ps1/sh)")
    return False


def check_config():
    if not os.path.exists("config.py"):
        err("config.py nao existe. Rode: python setup_config.py")
        return False, None
    try:
        from config import SESSIONS, CMD_TOKEN, MEGA_HOST
    except Exception as e:
        err(f"config.py nao importa: {e}")
        return False, None

    if not SESSIONS:
        err("SESSIONS vazio em config.py")
        return False, None

    issues = 0
    for sid, cfg in SESSIONS.items():
        for key in ("instance", "token", "phone"):
            v = cfg.get(key, "")
            if not v or "CHANGE_ME" in str(v) or "SUA_" in str(v) or "SEU_" in str(v):
                err(f"sessao {sid}: campo '{key}' nao preenchido ({v!r})")
                issues += 1
        if not cfg.get("lid"):
            warn(f"sessao {sid}: lid vazio. Rode: python discover_lid.py {sid}")

    if issues == 0:
        ok(f"config.py valido ({len(SESSIONS)} sessao(oes))")
    return issues == 0, SESSIONS


def check_webhook_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", 3020))
        ok("webhook_server.py rodando em :3020")
        return True
    except Exception:
        err("nada rodando em :3020. Rode: ./start.sh ou .\\start.ps1")
        return False
    finally:
        s.close()


def check_ngrok_url():
    try:
        with urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
            data = json.loads(r.read())
        tunnels = data.get("tunnels", [])
        if not tunnels:
            warn("ngrok rodando mas sem tunnels ativos")
            return None
        url = tunnels[0]["public_url"]
        ok(f"ngrok URL publica: {url}")
        return url
    except Exception:
        warn("ngrok api (4040) nao responde. ngrok rodando?")
        return None


def check_megaapi(sessions):
    if not sessions:
        return
    if not shutil.which("curl"):
        return
    for sid, cfg in sessions.items():
        if not cfg.get("token") or "CHANGE" in str(cfg.get("token", "")):
            continue
        url = f"{cfg.get('instance', '')}"
        # quick ping via status endpoint
        full = f"https://apibusiness1.megaapi.com.br/rest/instance/{cfg['instance']}"
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
                 "-H", f"Authorization: Bearer {cfg['token']}",
                 full],
                capture_output=True, text=True, timeout=10
            )
            code = result.stdout.strip()
            if code in ("200", "201"):
                ok(f"megaAPI sessao {sid}: instancia '{cfg['instance']}' alcancavel ({code})")
            elif code == "401" or code == "403":
                err(f"megaAPI sessao {sid}: token invalido ({code})")
            elif code == "404":
                err(f"megaAPI sessao {sid}: instancia '{cfg['instance']}' nao existe ({code})")
            else:
                warn(f"megaAPI sessao {sid}: HTTP {code}")
        except Exception as e:
            warn(f"megaAPI sessao {sid}: erro de rede ({e})")


def check_runtime_files():
    files = [
        ("messages_session1.jsonl", "criado pelo webhook quando 1a msg chega"),
        ("raw_debug.jsonl",         "criado pelo webhook em qualquer requisicao"),
    ]
    for f, hint in files:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            ok(f"{f} tem dados")
        else:
            warn(f"{f} vazio - {hint}")


def main():
    print("")
    print("=" * 60)
    print("WhatsApp Claude Agent - Doctor")
    print("=" * 60)
    print("")
    print("[ENV]")
    check_python()
    check_curl()
    check_ngrok()
    print("")
    print("[CONFIG]")
    config_ok, sessions = check_config()
    print("")
    print("[RUNTIME]")
    check_webhook_port()
    check_ngrok_url()
    print("")
    print("[MEGAAPI]")
    check_megaapi(sessions)
    print("")
    print("[FILES]")
    check_runtime_files()
    print("")
    print("Doctor done.")


if __name__ == "__main__":
    main()
