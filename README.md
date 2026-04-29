# WhatsApp Claude Agent

Self-hosted WhatsApp agent that uses **Claude Code CLI** as the LLM engine
(no extra API key for the LLM itself). Receives WhatsApp messages via the
[megaAPI](https://megaapi.com.br) webhook and replies through Claude Code.

[![CI](https://github.com/giovani-junior-dev/Allos/actions/workflows/ci.yml/badge.svg)](https://github.com/giovani-junior-dev/Allos/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## TL;DR

```bash
git clone https://github.com/giovani-junior-dev/Allos.git whatsapp-claude-agent
cd whatsapp-claude-agent
python bootstrap.py
```

`bootstrap.py` runs the config wizard, starts the webhook server, opens a
Cloudflare Quick Tunnel, and pushes the public URL to your megaAPI session.
Then you open Claude Code and paste a one-liner. Done.

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.8+ | runtime | https://python.org |
| curl | HTTP calls | bundled on Windows 10+, Linux, macOS |
| cloudflared | public tunnel | `winget install Cloudflare.cloudflared` / `brew install cloudflared` / [docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| Claude Code CLI | the brain | https://docs.anthropic.com/claude-code |
| megaAPI account | WhatsApp gateway | https://megaapi.com.br (paid SaaS) |
| OpenAI API key (optional) | audio transcription | https://platform.openai.com/api-keys |

## Architecture

```
WhatsApp -> megaAPI -> Cloudflare Tunnel -> webhook_server.py -> messages_sessionN.jsonl
                                                                       |
                                                                       v
WhatsApp <- megaAPI <- send_message.py <- Claude Code session <- monitor.py (Monitor tool)
```

1. `webhook_server.py` listens on `:3020`, validates the whitelisted phone, writes JSONL.
2. `monitor.py N` tails the per-session JSONL — runs **inside** a Claude Code session via the Monitor tool.
3. Claude Code reads each JSON line as user input, processes it, and replies via `send_message.py`.
4. Cloudflare Tunnel (Quick by default, named tunnel for production) exposes `:3020` over HTTPS.

## Two tunnel modes

**Quick Tunnel (default, zero-config):** random `*.trycloudflare.com` URL, regenerated each run, no domain needed. Used by `bootstrap.py`.

**Named Tunnel (production):** stable subdomain on a domain you control in Cloudflare. See [SETUP.md § Named Tunnel](SETUP.md#named-tunnel).

## Multi-session

One deployment can serve multiple WhatsApp instances:

```bash
python add_session.py    # wizard to add session 2, 3, ...
python update_webhooks.py # re-pushes URL to all sessions
```

Open one Claude Code session per WhatsApp session and paste:
`Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: <N>`

## Multimodal

| Direction | Text | Image | Audio | Video |
|-----------|------|-------|-------|-------|
| Receive | yes | yes (Claude reads natively) | yes (Whisper, optional) | rejected |
| Send | yes | yes (`send_message.py --type image`) | no | no |

## Repo layout

```
.
|-- bootstrap.py          # one-command install/run
|-- webhook_server.py     # HTTP :3020 receiver
|-- monitor.py            # JSONL tail (Monitor target)
|-- send_message.py       # outbound megaAPI client
|-- update_webhooks.py    # push PUBLIC_WEBHOOK_URL to all sessions
|-- doctor.py             # diagnostics
|-- add_session.py        # wizard to add another WhatsApp session
|-- discover_lid.py       # auto-fill LID after first message
|-- media_handler.py      # decrypt+save media via megaAPI
|-- transcribe.py         # OpenAI Whisper wrapper
|-- setup_config.py       # interactive config wizard
|-- config.example.py     # template (copy to config.py — gitignored)
|-- start.{sh,ps1}        # start webhook only (tunnel manages itself)
|-- stop.{sh,ps1}         # stop webhook
|-- tests/                # pytest
|-- docs/                 # extended docs and roadmaps
|-- CLAUDE_PROMPT.md      # paste into Claude Code to activate the agent
|-- SETUP.md              # step-by-step walkthrough (megaAPI signup, tunnel modes)
|-- TROUBLESHOOTING.md    # symptom -> fix
|-- CONTRIBUTING.md
|-- CHANGELOG.md
`-- LICENSE               # MIT
```

## Documentation

- **[SETUP.md](SETUP.md)** — full walkthrough including megaAPI account creation and named tunnel.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — common boot/runtime issues.
- **[CLAUDE_PROMPT.md](CLAUDE_PROMPT.md)** — the prompt that activates the agent inside Claude Code.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — dev setup, test commands, commit style.
- **[PROJETO.md](PROJETO.md)** — architecture deep-dive, megaAPI quirks, decision log.
- **[CHANGELOG.md](CHANGELOG.md)** — release history.

## Security

- `config.py` is **gitignored** — your tokens never leave your machine.
- Whitelist by phone number — only your authorized number(s) trigger the agent.
- Loop guard via `*Claude Code*` signature — the agent never replies to its own messages.
- Self-chat is supported (sending to yourself).

## License

MIT — see [LICENSE](LICENSE).

## Status

- Branch `trilha-1-multimodal` (tag `v1.0-trilha1`) — multi-session + multimodal validated end-to-end on 2026-04-28.
- Tunnel migrated from ngrok to Cloudflare Tunnel.
- Trilha 2 (24/7 VPS deploy) — see `docs/plans/2026-04-28-trilha-2-vps-deploy.md`.
