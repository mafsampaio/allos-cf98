# WhatsApp Agent POC — Claude Code as Brain

> WhatsApp agent that uses the active Claude Code CLI session as its LLM, with no separate API key. Multi-session, single webhook server, persistent dedup, command protocol.

---

## 1. Concept

Conventional WhatsApp bots call an LLM API (OpenAI, Anthropic, etc.) on every message. This POC takes a different route: it pipes incoming messages into the **Claude Code Monitor tool** so the active Claude Code session itself reads the message and decides what to reply. Replies are sent back to WhatsApp through a tiny Python helper.

Result: a fully working WhatsApp agent at zero extra LLM cost while the operator is in a Claude Code session.

---

## 2. Architecture

```
WhatsApp -> megaAPI -> ngrok -> webhook_server.py (port 3020)
                                       |
                                       v
                              messages_sessionN.jsonl
                                       |
                                       v
                              monitor.py (Monitor in Claude Code)
                                       |
                                       v
                              Claude Code reads, decides, replies
                                       |
                                       v
                              send_message.py -> megaAPI -> WhatsApp
```

A single `webhook_server.py` instance serves all sessions. Each megaAPI instance is configured with the same ngrok URL plus a distinct `?session=N` query parameter.

---

## 3. Files

```
teste/
  webhook_server.py        # HTTP server :3020, multi-session router + parser
  send_message.py          # megaAPI sender (curl-based, signs with *Claude Code*)
  monitor.py         # Monitor target — emits one line per new message
  config.py                # SESSIONS dict, CMD_TOKEN, SIGNATURE, MEGA_HOST
  .env.example             # legacy env stub
  messages_sessionN.jsonl  # append-only per-session message log
  processed_ids_sessionN.txt
  raw_debug.jsonl          # raw payload dump for debugging
  PROJETO.md               # this file
```

### `webhook_server.py`
- Listens on `0.0.0.0:3020`.
- Reads `?session=N` from query string; defaults to `1`.
- Parses **flat root** payload (no `data` wrapper).
- Ignores: `@g.us` (groups), `@newsletter`, media (writes `[midia]`).
- Whitelist: **exact** phone match per session (`SESSIONS[session]["phone"]`).
- Accepts self-chat (`fromMe=true` from own number).
- Appends matching messages to `messages_sessionN.jsonl`.
- Always dumps the raw event to `raw_debug.jsonl`.

### `send_message.py`
- Uses `subprocess.run(["curl", ...])` — `urllib` is blocked by Cloudflare.
- Endpoint: `POST {MEGA_HOST}/rest/sendMessage/{instance}/text`.
- Body: `{"messageData":{"to":"...","text":"...","linkPreview":false}}`.
- Auto-appends `*Claude Code*` signature.
- Forces `encoding="utf-8"` (Windows cp1252 breaks on emoji).

### `monitor.py`
- Reads `messages_sessionN.jsonl` from the **start** (NOT `seek(0,2)` — would miss the first message when the file is created with that message inside).
- Skips: empty IDs, already-processed IDs, media markers, lines containing `*Claude Code*`.
- Persists processed IDs in `processed_ids_sessionN.txt` so restarts don't replay.
- Each emitted line = one Monitor notification to Claude Code.

### `config.py`
- `MEGA_HOST = "https://apibusiness1.megaapi.com.br"`
- `CMD_TOKEN = "s7dev"` — security prefix for command-mode messages.
- `SIGNATURE = "*Claude Code*"` — auto-appended on every outbound, used to break the reply-loop on inbound.
- `SESSIONS` dict mapping `"1"`, `"2"`, ... to `{instance, token, phone, lid}`.

---

## 4. Sessions

| Session | Phone | megaAPI Instance | LID |
|---------|-------|------------------|-----|
| 1 | 556195562618 | megabusiness-desenvolivimentoProjeto2 | 22540172955723 |
| 2 | 556182796341 | megabusiness-desenvolivimentoProjeto3 | 90997556006924 |

Add a new session by extending `SESSIONS` in `config.py` and configuring the megaAPI webhook URL with the matching `?session=N`.

---

## 5. Setup & Run

### Prereqs
- Python 3 on PATH
- `curl` available on PATH
- `ngrok` (or any public tunnel)
- A megaAPI account with at least one configured instance

### Boot
```bash
# Terminal 1 — webhook server (single process for all sessions)
python webhook_server.py

# Terminal 2 — public tunnel
ngrok http 3020
```

Configure each megaAPI instance webhook to:
```
https://<ngrok-id>.ngrok-free.app/?session=<N>
```

### Per-session loop inside Claude Code
- Set Monitor command: `python monitor.py 1`  (or 2, 3, ...)
- When Claude Code receives a notification (a JSON line), reply with:
  ```bash
  python -c "from send_message import send_text; send_text('PHONE', 'reply', 'SESSION')"
  ```

---

## 6. Message Protocol

| Inbound | Treated as |
|---------|-----------|
| Plain text | Chat — Claude responds conversationally |
| `!s7dev <task>` | Command — Claude executes (bash, files, etc.) |

Outbound replies are always signed with `*Claude Code*` on a new line; this prevents the bot from replying to its own echoes.

---

## 7. Bugs Fixed (POC log)

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Empty parse output | Assumed `data` wrapper | Parse from payload root |
| 2 | `403 Forbidden` on send | Cloudflare blocks urllib UA | Use `curl` via subprocess |
| 3 | `UnicodeDecodeError` (emoji) | Windows cp1252 default | Force `encoding="utf-8"` everywhere |
| 4 | First message not emitted | `seek(0,2)` skipped already-written line | Read from start + persistent dedup |
| 5 | Wrong sender accepted | Substring whitelist + LID-or-phone fallback | Exact phone match per session |
| 6 | Bot replied to itself in a loop | Webhook captured outbound echoes | Filter `*Claude Code*` signature in tail |

---

## 8. megaAPI Quirks (essentials)

- Host is `https://apibusiness1.megaapi.com.br`, NOT `api.megaapi.com.br`.
- Inbound payload is flat (no `data` wrapper).
- `@lid` at payload root is the **instance** LID, not the sender's.
- `fromMe: true` self-chat events do arrive — opt in or filter explicitly.
- Cloudflare in front — `curl` works, `urllib` does not.
- Outbound payload: `{"messageData":{"to":"<phone>","text":"...","linkPreview":false}}`.

Full reference: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/reference_megaapi.md`.

---

## 9. Current State

- Multi-session running (sessions 1 and 2).
- Loops eliminated, dedup persistent, whitelist exact.
- POC validated end-to-end: WhatsApp -> webhook -> Claude reply -> WhatsApp.
- Local-only: depends on the operator's machine running Python + ngrok + an active Claude Code session.

---

## 10. Roadmap

### 10.1 Install Skill
Author a Claude Code skill that scaffolds this project on any machine/VPS:
- creates the file layout
- writes `config.py` from a guided prompt (sessions, tokens, phones)
- prints next-step instructions for ngrok and webhook URL configuration
- optional sample megaAPI smoke test

### 10.2 VPS Deployment
Move the runtime off the local box:
- `webhook_server.py` running on a VPS with a public IP (no ngrok)
- HTTPS via Caddy/nginx + Let's Encrypt, or a managed reverse proxy
- Process supervision: `pm2` (Node-style) or `systemd` units for the webhook server
- Open question: Claude Code still needs an active session. Options:
  - Keep an interactive Claude Code session running on the VPS (tmux/screen)
  - **Fallback**: switch the brain to the Anthropic API for headless operation; keep the same `tail/send` interface so the local-Claude-Code mode still works for development

### 10.3 Share with Students
Package as an installable skill/template:
- one-command bootstrap
- safe default config + `.env` separation
- documented megaAPI account setup steps
- short walkthrough video / README

---

## 11. Memory Pointers

- Project memory: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/project_whatsapp_agent.md`
- megaAPI reference: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/reference_megaapi.md`
- Memory index: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/MEMORY.md`
