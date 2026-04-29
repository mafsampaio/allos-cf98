# Troubleshooting

When in doubt, run `python doctor.py` first. It prints the state of every component.

## Boot

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bootstrap.py` exits "ERROR: cloudflared not found" | binary not on PATH | `winget install Cloudflare.cloudflared` (Windows), `brew install cloudflared` (macOS), or download from Cloudflare. |
| `bootstrap.py` exits "ERROR: cloudflared did not print a Quick Tunnel URL" | Cloudflare blocked the run, or the network has outbound QUIC blocked | check `cloudflared.log` for the real error. Re-run with `cloudflared tunnel --url http://127.0.0.1:3020 --protocol http2` if QUIC is blocked. |
| `webhook_server.py` exits immediately | `:3020` is in use | `lsof -iTCP:3020 -sTCP:LISTEN` (Linux/macOS) or `netstat -ano \| findstr :3020` (Windows) — kill the offending process. |
| `setup_config.py` runs every time | `config.py` was deleted or never written | run `python setup_config.py` once and verify the file lands in the project root. |

## megaAPI

| Symptom | Cause | Fix |
|---------|-------|-----|
| `doctor.py` reports `megaAPI sessao N: HTTP 404` | wrong instance name | check the instance string in `config.py` matches the megaAPI dashboard. |
| `doctor.py` reports `megaAPI sessao N: HTTP 401` | bad token | regenerate the token in the megaAPI dashboard, update `config.py`, run `python update_webhooks.py`. |
| Webhook never fires | URL not registered or instance disconnected | run `python update_webhooks.py`; verify the WhatsApp connection in the megaAPI dashboard. |

## Runtime

| Symptom | Cause | Fix |
|---------|-------|-----|
| Message arrives in JSONL but Claude does not reply | no Claude Code session has the Monitor tool active on `python monitor.py N` | open a Claude Code session and paste `Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: N`. |
| Two replies for one message | duplicate `monitor.py` processes | `ps -ef \| grep monitor.py \| grep -v grep` — kill all but one. |
| `monitor.py` runs but messages are silently dropped | `monitor.py` was launched standalone (nohup/&) — its stdout has no consumer; it marks every message as processed | kill it (`pkill -f "monitor.py"`), then activate it inside a Claude Code session via the Monitor tool. |
| Replies loop infinitely | the loop guard signature `*Claude Code*` was removed from outgoing messages | restore `SIGNATURE = "*Claude Code*"` in `config.py`. |
| Image upload returns HTTP 413 | larger than 16MB | resize before sending; megaAPI caps `mediaBase64` at 16MB. |
| Audio transcription returns `[audio - transcricao desativada]` | `OPENAI_API_KEY` empty | set the key in `config.py` or accept the fallback (the audio file is still saved under `media/sessionN/`). |

## Tunnel

| Symptom | Cause | Fix |
|---------|-------|-----|
| Quick Tunnel URL changes on every run | by design — Quick Tunnels are ephemeral | switch to a named tunnel (see [SETUP.md § Named Tunnel](SETUP.md#named-tunnel)). |
| Named tunnel returns 502 | service runs as LocalSystem and cannot read user-profile config | edit the service binPath to include `--config "C:\Users\YOU\.cloudflared\config.yml"` (admin PowerShell: `sc.exe config cloudflared binPath= "..."`). |
| Tunnel up but `POST` returns 502 | `ingress.service` set to `http://localhost:3020` and the OS resolves `localhost` to `::1` first | change to `http://127.0.0.1:3020` in `~/.cloudflared/config.yml`. |

## Tests

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pytest` fails on a fresh clone | dependencies missing | `pip install -e .[dev]` (after Task 12 lands `pyproject.toml`). |
| `pytest` fails with `ModuleNotFoundError: config` | the test fixture pre-pop is broken | check `tests/conftest.py` — fixture must inject a fake `config` module before importing the unit under test. |

## Resetting everything

If state is corrupted and you want a clean slate:

```bash
./stop.sh
rm -f messages_session*.jsonl processed_ids_session*.txt raw_debug.jsonl
rm -rf media/
python bootstrap.py
```

`config.py` is preserved.
