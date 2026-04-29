"""
Interactive config wizard. Generates config.py from user input.
Cross-platform (Windows / Linux / macOS).

Run: python setup_config.py
Or via install.ps1 / install.sh.
"""
import os
import re
import sys


CONFIG_PATH = "config.py"


def ask(label: str, default: str = "", required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"  {label}{suffix}: ").strip()
        if not val:
            val = default
        if val or not required:
            return val
        print("    -> obrigatorio, tente novamente.")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    return digits


def write_config(cfg: dict) -> None:
    template = f'''# ============================================================
# WhatsApp Claude Agent - config.py (gerado por setup_config.py)
# ============================================================
# NUNCA commitar este arquivo. Ja esta no .gitignore.
# Para regerar: delete config.py e rode python setup_config.py
# ============================================================

CMD_TOKEN = {cfg["cmd_token"]!r}
SIGNATURE = {cfg["signature"]!r}
MEGA_HOST = {cfg["mega_host"]!r}

SESSIONS = {{
    "1": {{
        "instance": {cfg["instance"]!r},
        "token":    {cfg["token"]!r},
        "phone":    {cfg["phone"]!r},
        "lid":      {cfg["lid"]!r},
    }},
}}

OPENAI_API_KEY = {cfg["openai_key"]!r}

ALLOWED_PHONE = SESSIONS["1"]["phone"]
ALLOWED_LID   = SESSIONS["1"]["lid"]
MEGA_INSTANCE = SESSIONS["1"]["instance"]
MEGA_TOKEN    = SESSIONS["1"]["token"]
MEGA_BASE_URL = f"{{MEGA_HOST}}/rest/sendMessage/{{MEGA_INSTANCE}}"
'''
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(template)


def main() -> int:
    print("")
    print("=" * 60)
    print("WhatsApp Claude Agent - Configuracao Interativa")
    print("=" * 60)
    print("")

    if os.path.exists(CONFIG_PATH):
        ans = input(f"  {CONFIG_PATH} ja existe. Sobrescrever? [s/N]: ").strip().lower()
        if ans not in ("s", "sim", "y", "yes"):
            print("  Cancelado. config.py mantido.")
            return 0
        print("")

    print("Preencha os dados abaixo (Enter usa valor padrao quando mostrado):")
    print("")

    print("  CMD_TOKEN e legado/opcional. Whitelist (numero) sozinha basta.")
    cmd_token = ask("CMD_TOKEN (Enter pra pular)", default="", required=False)
    print("")
    print("--- megaAPI (https://megaapi.com.br) ---")
    instance = ask("Nome da instancia (ex: megabusiness-meuagente)")
    token    = ask("Token da instancia")
    print("")
    print("--- WhatsApp ---")
    phone_raw = ask("Seu numero WhatsApp (formato: 5511999999999)")
    phone     = normalize_phone(phone_raw)
    if not phone:
        print("  ERRO: numero invalido.")
        return 1

    print("")
    print("--- Multimodal (opcional) ---")
    print("  Obtenha sua chave em: https://platform.openai.com/api-keys")
    openai_key = ask("OPENAI_API_KEY (Whisper - transcricao de audio, deixe vazio para pular)",
                     default="", required=False)

    cfg = {
        "cmd_token": cmd_token,
        "signature": "*Claude Code*",
        "mega_host": "https://apibusiness1.megaapi.com.br",
        "instance":  instance,
        "token":     token,
        "phone":     phone,
        "lid":       "",
        "openai_key": openai_key,
    }

    write_config(cfg)
    print("")
    print(f"  OK: {CONFIG_PATH} criado.")
    print("")
    print("Proximos passos:")
    print("  1. Rode start.ps1 (Windows) ou start.sh (Linux/Mac)")
    print("  2. Cole a URL do ngrok no painel megaAPI (webhook)")
    print("  3. Mande mensagem WhatsApp pra voce mesmo")
    print("  4. Rode: python discover_lid.py    (descobre LID e atualiza config)")
    print("  5. Abra Claude Code e siga CLAUDE_PROMPT.md")
    print("")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Cancelado.")
        sys.exit(130)
