# ============================================================
# WhatsApp Claude Agent — Configuration Template
# ============================================================
# Copy this file to `config.py` and fill in your real values.
# DO NOT commit config.py (already in .gitignore).
# ============================================================

# Token secreto para executar comandos via WhatsApp.
# Mensagens devem comecar com !TOKEN para serem processadas.
# Exemplo: !meutoken liste arquivos da pasta atual
CMD_TOKEN = "CHANGE_ME_secret_token"

# Assinatura automatica anexada em todas as respostas.
# Tambem usada para quebrar loop (ignora mensagens proprias).
SIGNATURE = "*Claude Code*"

# Host da megaAPI (geralmente nao muda)
MEGA_HOST = "https://apibusiness1.megaapi.com.br"

# ------------------------------------------------------------
# Sessoes (instancias megaAPI)
# ------------------------------------------------------------
# Cada sessao = 1 numero de WhatsApp + 1 instancia megaAPI.
# Para descobrir o LID: envie 1a mensagem do numero, olhe
# raw_debug.jsonl, copie o campo "key.remoteJid" (parte antes
# de @lid) ou o "participant".
# ------------------------------------------------------------
SESSIONS = {
    "1": {
        "instance": "megabusiness-SUA_INSTANCIA_AQUI",
        "token":    "SEU_TOKEN_MEGAAPI_AQUI",
        "phone":    "5511999999999",          # numero com DDI+DDD, sem +
        "lid":      "00000000000000",         # preencher apos 1a mensagem
    },
    # Para multi-sessao, descomente e configure:
    # "2": {
    #     "instance": "megabusiness-OUTRA_INSTANCIA",
    #     "token":    "OUTRO_TOKEN",
    #     "phone":    "5511888888888",
    #     "lid":      "00000000000000",
    # },
}

# ------------------------------------------------------------
# Multimodal (opcional - deixe em branco para desativar)
# ------------------------------------------------------------
# OpenAI Whisper para transcrever audios recebidos.
# Pegue chave: https://platform.openai.com/api-keys
OPENAI_API_KEY = ""

# Defaults derivados (nao alterar)
ALLOWED_PHONE = SESSIONS["1"]["phone"]
ALLOWED_LID   = SESSIONS["1"]["lid"]
MEGA_INSTANCE = SESSIONS["1"]["instance"]
MEGA_TOKEN    = SESSIONS["1"]["token"]
MEGA_BASE_URL = f"{MEGA_HOST}/rest/sendMessage/{MEGA_INSTANCE}"
