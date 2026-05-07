# Allos — WhatsApp Claude Agent

Allos is a self-hosted WhatsApp agent that uses **Claude Code CLI** as the LLM
engine (no extra API key for the LLM itself). It receives WhatsApp messages
through an HTTP gateway and replies via Claude Code.

The reference WhatsApp gateway is [megaAPI](https://megaapi.io). Allos is built
to its request/response shape — but the host URL is configurable, and any
backend that mirrors the contract documented in
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) works as a drop-in replacement.
See [Swapping the WhatsApp gateway](#swapping-the-whatsapp-gateway) below.

[![CI](https://github.com/giovani-junior-dev/Allos/actions/workflows/ci.yml/badge.svg)](https://github.com/giovani-junior-dev/Allos/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## TL;DR

```bash
git clone https://github.com/giovani-junior-dev/Allos.git allos
cd allos
python scripts/bootstrap.py
```

`scripts/bootstrap.py` runs the config wizard, starts the webhook server, opens
a Cloudflare Quick Tunnel, and pushes the public URL to your gateway session.
Then you open Claude Code and paste a one-liner. Done.

## Quick Start with Docker (recommended for OSS users)

If you want a one-command containerized setup with auto-restart on reboot/crash:

```bash
git clone https://github.com/giovani-junior-dev/Allos.git allos
cd allos
python3 scripts/docker_setup.py    # interactive wizard
docker compose up -d --build
docker compose logs -f
```

The wizard configures provider (Anthropic / MiniMax / Kimi K2 / Z.ai / custom),
megaAPI credentials, and tunnel mode. The stack runs as 3 containers
(`webhook`, `cloudflared`, `agent`) with `restart: unless-stopped`.

Full docs: [`docs/DOCKER.md`](docs/DOCKER.md). Plan: [`docs/plans/2026-05-07-trilha-3-docker-oss.md`](docs/plans/2026-05-07-trilha-3-docker-oss.md).

> Prefer native systemd + tmux on Linux instead of Docker? See **Trilha 2** —
> plan in [`docs/plans/2026-04-28-trilha-2-vps-deploy.md`](docs/plans/2026-04-28-trilha-2-vps-deploy.md)
> (Docker and systemd paths coexist; pick whichever fits your ops style).

## Zero-to-running on a fresh machine

Don't have Python / git / curl / cloudflared installed yet? Open Claude Code
in an empty folder and paste the prompt in
[`INSTALL_PROMPT.md`](INSTALL_PROMPT.md). Claude detects your OS, installs
every dependency (winget / brew / apt), clones the repo, and walks you through
the bootstrap.

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.8+ | runtime | https://python.org |
| curl | HTTP calls | bundled on Windows 10+, Linux, macOS |
| cloudflared | public tunnel | `winget install Cloudflare.cloudflared` / `brew install cloudflared` / [docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| Claude Code CLI | the brain | https://docs.anthropic.com/claude-code |
| WhatsApp gateway account | inbound/outbound WhatsApp | [megaAPI](https://megaapi.io) (paid SaaS) — or any megaAPI-compatible backend, see [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) |
| OpenAI API key (optional) | audio transcription | https://platform.openai.com/api-keys |

> **Model recommendation:** the prompt in `CLAUDE_PROMPT.md` was designed and
> validated against **Anthropic Claude** (Sonnet/Opus). Other models (Kimi,
> GPT-4, etc.) work but tend to add their own instincts (e.g. blocking
> `fromMe:true`, retrying with sanitized text, writing the signature into the
> body). The defenses in `CLAUDE.md` and `send_message.py` make those
> edge-cases safe, but if you want first-try-correct behavior, stick with
> Anthropic Claude.

## Architecture

```
WhatsApp -> gateway -> Cloudflare Tunnel -> webhook_server.py -> messages_sessionN.jsonl
                                                                       |
                                                                       v
WhatsApp <- gateway <- send_message.py <- Claude Code session <- monitor.py (Monitor tool)
```

1. `webhook_server.py` listens on `:3020`, validates the whitelisted phone,
   writes JSONL.
2. `monitor.py N` tails the per-session JSONL — runs **inside** a Claude Code
   session via the Monitor tool.
3. Claude Code reads each JSON line as user input, processes it, and replies
   via `send_message.py`.
4. Cloudflare Tunnel (Quick by default, named tunnel for production) exposes
   `:3020` over HTTPS.

## Two tunnel modes

**Quick Tunnel (default, zero-config):** random `*.trycloudflare.com` URL,
regenerated each run, no domain needed. Used by `scripts/bootstrap.py`.

**Named Tunnel (production):** stable subdomain on a domain you control in
Cloudflare. See [SETUP.md § Named Tunnel](SETUP.md#named-tunnel).

## Multi-session

One deployment can serve multiple WhatsApp instances:

```bash
python -m whatsapp_agent.add_session    # wizard to add session 2, 3, ...
python -m whatsapp_agent.update_webhooks # re-pushes URL to all sessions
```

Open one Claude Code session per WhatsApp session and paste:
`Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: <N>`

## Multimodal

| Direction | Text | Image | Audio | Video |
|-----------|------|-------|-------|-------|
| Receive | yes | yes (Claude reads natively) | yes (Whisper, optional) | rejected |
| Send | yes | yes (`send_message.py --type image`) | no | no |

## Swapping the WhatsApp gateway

Allos was built against [megaAPI](https://megaapi.io), but the host URL is a
runtime config value, not hardcoded. Any backend that implements the contract
in [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) — same endpoints, same JSON
payloads, same `Authorization: Bearer` header — drops in by changing one
field.

**To switch gateways** (whether to a different megaAPI plan, a self-hosted
megaAPI clone, or any compatible backend):

1. Re-run the wizard with `rm config.py && python -m whatsapp_agent.setup_config`.
2. Enter the new `API base URL` when prompted.
3. Run `python -m whatsapp_agent.update_webhooks` to push the public webhook
   URL to the new instance.

**Where the gateway is referenced in the code** (in case you need to adapt to
a backend that's almost-but-not-quite megaAPI-shaped):

| File | What it does |
|------|--------------|
| `src/whatsapp_agent/send_message.py` lines 20-21 | Outbound text + image endpoints (`/rest/sendMessage/{instance}/text`, `/mediaBase64`). |
| `src/whatsapp_agent/send_message.py` lines 71-114 | Outbound JSON payloads for text and image. |
| `src/whatsapp_agent/update_webhooks.py` line 24 | `configWebhook` endpoint. |
| `src/whatsapp_agent/media_handler.py` line 86 | Media download endpoint. |
| `src/whatsapp_agent/webhook_server.py` lines 46-95 | Inbound payload parser — field names the gateway must produce (`key.remoteJid`, `key.fromMe`, `message.conversation`, `message.imageMessage.{caption,mediaKey,...}`, etc.). |
| `src/whatsapp_agent/doctor.py` lines 125-135 | Health-check endpoint (`/rest/instance/{instance}`). |

If your gateway uses different paths or payload shapes, edit those locations.
Everything else (whitelist, JSONL queue, monitor, signature handling) is
gateway-agnostic.

## Persistent task memory (beads)

Allos uses [beads](https://github.com/gastownhall/beads) to maintain a
dependency-aware task graph that survives session restarts. `bootstrap.py`
installs and initializes it automatically on Linux/macOS; on Windows install
the binary manually from the beads releases page.

How Claude Code uses it (full rules in [CLAUDE.md](CLAUDE.md)):

- `bd ready --json` to find work that has no open blockers.
- `bd create "Title" -p 1` to log a new task.
- `bd update <id> --claim` to atomically take ownership.
- `bd close <id> "what was done"` to finish.

The database lives in `.beads/` (gitignored).

## Repo layout

```
.
|-- src/whatsapp_agent/   # installable package (pip install -e .)
|   |-- webhook_server.py # HTTP :3020 receiver (gateway-shape parser)
|   |-- monitor.py        # JSONL tail (Monitor target)
|   |-- send_message.py   # outbound gateway client (text + image)
|   |-- update_webhooks.py# push PUBLIC_WEBHOOK_URL to all sessions
|   |-- doctor.py         # diagnostics
|   |-- add_session.py    # wizard to add another WhatsApp session
|   |-- discover_lid.py   # auto-fill LID after first message
|   |-- media_handler.py  # decrypt+save media via gateway
|   |-- transcribe.py     # OpenAI Whisper wrapper
|   `-- setup_config.py   # interactive config wizard
|-- scripts/
|   |-- bootstrap.py      # one-command install/run
|   |-- start.{sh,ps1}    # start webhook only (tunnel manages itself)
|   `-- stop.{sh,ps1}     # stop webhook
|-- config.example.py     # template (copy to config.py — gitignored)
|-- tests/                # pytest
|-- docs/                 # extended docs and roadmaps
|   |-- API_CONTRACT.md   # gateway contract (auth + endpoints + payloads)
|   `-- plans/            # design plans
|-- CLAUDE_PROMPT.md      # paste into Claude Code to activate the agent
|-- INSTALL_PROMPT.md     # zero-to-running prompt for fresh machines
|-- SETUP.md              # step-by-step walkthrough (gateway signup, tunnel modes)
|-- TROUBLESHOOTING.md    # symptom -> fix
|-- CONTRIBUTING.md
|-- CHANGELOG.md
`-- LICENSE               # MIT
```

## Documentation

- **[SETUP.md](SETUP.md)** — full walkthrough including gateway account creation and named tunnel.
- **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)** — HTTP contract a gateway backend must implement.
- **[INSTALL_PROMPT.md](INSTALL_PROMPT.md)** — zero-to-running prompt for fresh machines.
- **[CLAUDE_PROMPT.md](CLAUDE_PROMPT.md)** — the prompt that activates the agent inside Claude Code.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — common boot/runtime issues.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — dev setup, test commands, commit style.
- **[CHANGELOG.md](CHANGELOG.md)** — release history.

## Security

- `config.py` is **gitignored** — your tokens never leave your machine.
- Whitelist by phone number — only your authorized number(s) trigger the agent.
- Loop guard via `*Claude Code*` signature — the agent never replies to its own messages.
- Self-chat is supported (sending to yourself).

## License

MIT — see [LICENSE](LICENSE).

## Status

- Branch `trilha-1-multimodal` (tag `v1.1.1`) — multi-session + multimodal validated end-to-end on 2026-04-28; OSS distribution + provider-agnostic API host shipped 2026-04-30.
- Tunnel migrated from ngrok to Cloudflare Tunnel.
- Trilha 2 (24/7 VPS deploy) — see `docs/plans/2026-04-28-trilha-2-vps-deploy.md`.
