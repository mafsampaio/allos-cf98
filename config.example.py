# ============================================================
# WhatsApp Claude Agent — Configuration Template (Evolution edition)
# ============================================================
# Copy this file to `config.py` and fill in your real values.
# DO NOT commit config.py (already in .gitignore).
# ============================================================

# Token legado/opcional. Whitelist (SESSIONS phone) ja restringe quem pode
# disparar o agente. Deixe vazio se nao quiser camada extra.
# Quando definido, voce pode opcionalmente exigir prefixo "!TOKEN " no
# CLAUDE_PROMPT.md (precisa editar manualmente).
CMD_TOKEN = ""

# Assinatura automatica anexada em todas as respostas.
# Tambem usada para quebrar loop (ignora mensagens proprias).
SIGNATURE = "*Claude Code*"

# Host da Evolution API (self-hosted ou SaaS).
# Exemplo CF98: https://evolution.cf98.online
EVOLUTION_HOST = "https://evolution.cf98.online"

# URL publica do seu webhook (Cloudflare Tunnel ou subdominio com TLS).
# Atualizada via `python -m whatsapp_agent.update_webhooks`.
PUBLIC_WEBHOOK_URL = "https://allos.cf98.online"

# ------------------------------------------------------------
# Sessoes (instancias Evolution)
# ------------------------------------------------------------
# Cada sessao = 1 numero de WhatsApp + 1 instancia Evolution.
# Para descobrir o LID: envie 1a mensagem do numero, olhe
# raw_debug.jsonl, copie o campo "key.remoteJid" (parte antes
# de @lid) ou o "participant".
# ------------------------------------------------------------
SESSIONS = {
    "1": {
        "instance": "SUA_INSTANCIA_EVOLUTION_AQUI",
        "token":    "SEU_TOKEN_INSTANCIA_AQUI",   # apikey por-instancia (NAO o master)
        "phone":    "5511999999999",              # numero com DDI+DDD, sem +
        "lid":      "",                           # preencher apos 1a mensagem
    },
    # Para multi-sessao, descomente e configure:
    # "2": {
    #     "instance": "outra-instancia",
    #     "token":    "OUTRO_TOKEN",
    #     "phone":    "5511888888888",
    #     "lid":      "",
    # },
}

# ------------------------------------------------------------
# Multimodal (opcional - deixe em branco para desativar)
# ------------------------------------------------------------
# OpenAI Whisper para transcrever audios recebidos.
# Pegue chave: https://platform.openai.com/api-keys
OPENAI_API_KEY = ""

# Defaults derivados (nao alterar)
ALLOWED_PHONE     = SESSIONS["1"]["phone"]
ALLOWED_LID       = SESSIONS["1"]["lid"]
EVOLUTION_INSTANCE = SESSIONS["1"]["instance"]
EVOLUTION_TOKEN    = SESSIONS["1"]["token"]
EVOLUTION_BASE_URL = f"{EVOLUTION_HOST}/message/sendText/{EVOLUTION_INSTANCE}"
