# WhatsApp Claude Agent

Agente WhatsApp que usa **Claude Code CLI** como cérebro LLM (sem API key extra).
Recebe mensagens via webhook megaAPI e responde automaticamente via Claude Code.

## Quickstart (5 passos)

```bash
# 1. Clone
git clone <repo-url> whatsapp-claude-agent
cd whatsapp-claude-agent

# 2. Install (faz wizard interativo de config)
#    Windows:  powershell -ExecutionPolicy Bypass -File install.ps1
#    Linux:    chmod +x *.sh && ./install.sh

# 3. Sobe webhook + ngrok
#    Windows:  .\start.ps1
#    Linux:    ./start.sh

# 4. Cole a URL ngrok no painel megaAPI (webhook)
#    Mande mensagem WhatsApp pra voce mesmo
#    Auto-descobre LID:
python discover_lid.py

# 5. Abra Claude Code, siga CLAUDE_PROMPT.md
claude
```

Se algo quebrar: `python doctor.py` diagnostica tudo.

## Pré-requisitos

| Ferramenta | Onde instalar |
|------------|---------------|
| Python 3.8+ | https://python.org |
| curl | já vem no Windows 10+, Linux, macOS |
| ngrok | https://ngrok.com/download |
| Claude Code CLI | https://docs.anthropic.com/claude-code |
| Conta megaAPI | https://megaapi.com.br |

## Como funciona

```
WhatsApp → megaAPI → ngrok → webhook_server.py → messages_sessionN.jsonl
                                                          ↓
WhatsApp ← megaAPI ← send_message.py ← Claude Code ← monitor.py (Monitor)
```

1. `webhook_server.py` recebe webhooks megaAPI, filtra whitelist, grava JSONL
2. `monitor.py` lê o JSONL (rodado dentro de sessão Claude Code via Monitor)
3. Claude Code processa cada mensagem como prompt
4. `send_message.py` envia resposta de volta via megaAPI

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `webhook_server.py` | Servidor HTTP :3020 que recebe webhooks |
| `monitor.py` | Tail do JSONL — alvo do Monitor no Claude Code |
| `send_message.py` | Sender via curl + megaAPI |
| `config.py` | **Seus secrets** (criado pelo install, nunca commitar) |
| `config.example.py` | Template público |
| `setup_config.py` | Wizard interativo gera config.py |
| `discover_lid.py` | Auto-descobre LID e atualiza config.py |
| `doctor.py` | Diagnostico (env, config, runtime, megaAPI) |
| `install.{ps1,sh}` | Instalador (chama setup_config.py) |
| `start.{ps1,sh}` | Sobe webhook + ngrok |
| `stop.{ps1,sh}` | Para tudo |
| `CLAUDE_PROMPT.md` | Prompt pronto pra colar no Claude Code |
| `add_session.py` | Wizard pra adicionar nova instancia megaAPI ao config |
| `media_handler.py` | Baixa media decriptada via endpoint megaAPI downloadMediaMessage |
| `transcribe.py` | Transcreve audio recebido via OpenAI Whisper (opcional) |

## Multi-sessão

Adicionar nova instancia ao deployment ja rodando:

```bash
python add_session.py
```

O wizard atribui o proximo ID livre. Configure o webhook da nova instancia
megaAPI como `https://abc.ngrok.app/?session=N`. Cada sessao roda em
sua propria sessao Claude Code (`python monitor.py N`).

## Multimodal

| Direcao | Texto | Imagem | Audio |
|---------|-------|--------|-------|
| Recebe  | OK    | OK (Claude le via Read tool) | OK (Whisper transcreve) |
| Envia   | OK    | OK (`--type image`) | nao suportado |

Multimodal e opcional: sem `OPENAI_API_KEY`, recebimento de audio ainda
funciona (arquivo salvo em `media/sessionN/`), mas sem transcricao automatica.

## Documentação completa

- [`PROJETO.md`](./PROJETO.md) — arquitetura detalhada, bugs corrigidos,
  quirks da megaAPI, roadmap.
- [`SETUP.md`](./SETUP.md) — passo-a-passo do zero (criar conta megaAPI,
  configurar ngrok, primeira mensagem).

## Segurança

- `config.py` está no `.gitignore` — nunca será commitado.
- Whitelist por número telefone — só processa mensagens autorizadas (sem prefixo obrigatório).
- Self-chat suportado (mande mensagem para si mesmo no WhatsApp).
- Slash commands do Claude Code: `/skill-name args` direto na mensagem.
- `CMD_TOKEN` em config.py é legado — mantido pra quem quiser camada extra de segurança.

## Status

- Branch atual: `trilha-1-multimodal` (tag `v1.0-trilha1`)
- Trilha 1 (multi-sessao + multimodal) **concluida e validada E2E** em 2026-04-28
- 26 testes pytest passando

## Trilha 2 — VPS produção

Próxima fase: deploy 24/7 em VPS com Cloudflare Tunnel + systemd.
Ver [`docs/TRILHA_2_ROADMAP.md`](./docs/TRILHA_2_ROADMAP.md) e
[`PROJETO.md`](./PROJETO.md) seção roadmap.
