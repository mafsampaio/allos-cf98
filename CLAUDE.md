# CLAUDE.md — project rules for Claude Code in this repo

This file is auto-loaded by Claude Code when a session opens in this directory. Every rule below is **default behavior** for any session — it can be overridden by an explicit user instruction in the session.

## Rule 1 — when this session is acting as the WhatsApp agent

This project's purpose is to let users drive Claude Code over WhatsApp. When this Claude Code session has an active Monitor tool watching a `python -m whatsapp_agent.monitor N` process, you are operating as the WhatsApp agent for session `N`. In that role:

- **Always** reply to the user by calling `python -m whatsapp_agent.send_message <from> "<reply text>" <N>` (or `--type image <from> <path> "<caption>" <N>` for images). Use the `from` field of the JSONL message you are responding to.
- **Never** answer inline in the CLI as plain assistant text. The end user is on WhatsApp — text in the CLI is invisible to them.
- The CLI session output is reserved for tool-call traces, doctor checks, and the local operator's debugging. Treat it as logs, not as a reply channel.
- If a reply is too long for one WhatsApp message (over ~4000 chars), split into multiple `send_message` calls preserving order.
- On error, send a short WhatsApp reply ("Erro ao processar — tente reformular") in addition to logging the traceback in the CLI. The user must always get an answer.

When this session is **not** acting as the WhatsApp agent (no Monitor tool active on `monitor.py`), reply normally in the CLI.

### Self-chat is the default use case — `fromMe` is NOT a filter

The point of this project is the user driving Claude Code through their own WhatsApp number, sending messages to themselves. Every legitimate user message in that mode arrives with `fromMe: true` (the user IS the instance). DO NOT ignore those messages.

The single loop-guard criterion is the literal string `*Claude Code*` in the text field — that is the signature your own replies carry, and it is how you avoid replying to your own echoed message. `fromMe` (true or false) is irrelevant for filtering. The webhook already applied the phone whitelist before writing the JSONL line; if a line is in the file, it is authorized and you must process it (unless its text contains `*Claude Code*`).

## Rule 2 — persistent task memory via beads (`bd`)

This repo uses [beads](https://github.com/gastownhall/beads) as a persistent, dependency-aware task graph. The database lives in `.beads/` at the project root. Beads survives across sessions; markdown TODO lists do not.

### Bootstrap (first session in a fresh clone)
- Check whether `.beads/` exists. If it does not, run `bd init` once. Do not re-init if it already exists.

### Before creating any new task
- Run `bd ready --json` to list open tasks with no blockers. Read the result. Do not create a duplicate of an existing open task.

### Creating tasks
- `bd create "Short imperative title" -p 0` for a critical / blocker task.
- `bd create "Short imperative title" -p 1` for important work.
- `bd create "Short imperative title" -p 2` for nice-to-have / cleanup.
- For epics that decompose, create the parent first, then children: `bd create "Subtask" -p 1 --parent <parent-id>`.

### Working on a task
- Atomically claim before starting: `bd update <id> --claim`. This prevents two parallel sessions from grabbing the same task.
- Link dependencies as you discover them: `bd dep add <blocked-id> <blocker-id>`.

### Finishing a task
- Close with a one-line reason: `bd close <id> "what was done and where (commit SHA, file path, etc.)"`. The reason becomes audit trail.

### Querying
- `bd ready --json` — work available now (no open blockers).
- `bd show <id>` — full task details and audit trail.
- `bd list --status open --json` — every open task.
- Always use `--json` when piping to another tool.

### When to use beads vs ad-hoc tracking
- Use beads for any work that spans more than one session, has dependencies, or might be picked up by a different agent later.
- Use the in-session task-list tool (TaskCreate / TodoWrite) for the current session's bookkeeping; promote anything outliving the session into beads via `bd create`.

## Rule 3 — runtime hygiene

These apply whenever you make changes in this repo:

- Source modules live under `src/whatsapp_agent/`. Always invoke them with `python -m whatsapp_agent.<module>` — never `python <module>.py` (the latter only works for the legacy flat layout pre-Task-15 and is not supported anymore).
- The webhook server, Cloudflare Tunnel, and `monitor.py` instances are long-running. **Do not kill them** unless the user explicitly asks. If you need to know whether one is alive, use `ps -ef | grep ...` or `python -m whatsapp_agent.doctor`.
- `monitor.py` MUST be launched via Claude Code's Monitor tool, never via `nohup`/`&`/`run_in_background`. Standalone monitors silently consume messages because their stdout has no reader. This is enforced in `CLAUDE_PROMPT.md` and re-stated here as a default.
- After edits to `src/whatsapp_agent/`, always run `python -m pytest -q` before claiming the change is done.
- After edits to user-facing config (`config.py`, `PUBLIC_WEBHOOK_URL`), run `python -m whatsapp_agent.update_webhooks` to re-register the URL with megaAPI.

## Rule 4 — secrets

- `config.py` is gitignored and contains live tokens (`MEGA_TOKEN`, `OPENAI_API_KEY`). Never stage it. Never `cat` its contents into a chat or commit message.
- `config.example.py` is the public template; keep it in sync with `config.py`'s schema (variable names + comments) but never with actual secret values.
- The bearer token passed to `curl` in `update_webhooks.py` and `send_message.py` is visible in process command lines on Linux. Acceptable for the local-dev scope; document any change to network exposure in `TROUBLESHOOTING.md`.

## Rule 5 — when in doubt, run the doctor

`python -m whatsapp_agent.doctor` is the single command that tells you whether the system is healthy. Run it at the start of any debugging session and any time the user reports something is wrong before changing code.
