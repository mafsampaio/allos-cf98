# Setup walkthrough

This is the slow path. If you just want to try the agent, follow the
[README TL;DR](README.md#tldr) instead.

## 1. Create a megaAPI account and instance

1. Sign up at https://megaapi.com.br.
2. In the dashboard, create a new instance. Note the **instance name**
   (e.g. `megabusiness-yourname`) and the **token**.
3. Connect a WhatsApp number to the instance — scan the QR code with
   the WhatsApp app on the phone.
   _If you have a screenshot of this step, drop it into `docs/images/megaapi-qr.png`
   and reference it here._

## 2. Install dependencies

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| Python 3.8+ | https://python.org or `winget install Python.Python.3.12` | `brew install python` | `apt install python3` |
| cloudflared | `winget install Cloudflare.cloudflared` | `brew install cloudflared` | https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ |
| Claude Code CLI | https://docs.anthropic.com/claude-code | same | same |

## 3. Clone and bootstrap

```bash
git clone https://github.com/giovani-junior-dev/Allos.git whatsapp-claude-agent
cd whatsapp-claude-agent
python bootstrap.py
```

`bootstrap.py` will:

1. Verify Python, curl, and cloudflared are present.
2. Run the config wizard if `config.py` does not exist (asks for instance, token, phone, optional OpenAI key).
3. Start `webhook_server.py` on `:3020`.
4. Open a Cloudflare Quick Tunnel and capture the public URL.
5. Write `PUBLIC_WEBHOOK_URL` into `config.py`.
6. Run `update_webhooks.py` to push the URL to every megaAPI session.
7. Print a "READY" banner with the URL and the next step.

## 4. Discover your LID

Send any WhatsApp message to your own number. Then run:

```bash
python discover_lid.py
```

This reads `messages_session1.jsonl`, extracts the LID, and writes it back into `config.py`. Without the LID, the whitelist cannot match LID-based group messages.

## 5. Activate Claude Code

Open a new terminal:

```bash
cd whatsapp-claude-agent
claude
```

In the Claude Code session, send as the first message:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1
```

Claude will read the prompt, run `python doctor.py`, activate the Monitor tool on `python monitor.py 1`, and start replying to incoming WhatsApp messages.

## 6. Test it

Send any text message to your WhatsApp number. Claude replies within seconds, signed `*Claude Code*`.

## Multi-session

Add another WhatsApp instance:

```bash
python add_session.py        # asks for instance/token/phone, assigns next ID
python update_webhooks.py    # re-pushes PUBLIC_WEBHOOK_URL to all sessions
```

Open a second Claude Code session in another terminal and paste:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 2
```

Each Claude Code session monitors **exactly one** WhatsApp session.

## Named Tunnel (production)

Quick Tunnel URLs are random and regenerate on every restart. For a stable URL, switch to a named tunnel.

```bash
cloudflared tunnel login
cloudflared tunnel create whatsapp-webhook
cloudflared tunnel route dns whatsapp-webhook agent.your-domain.com
```

Edit `~/.cloudflared/config.yml`:

```yaml
tunnel: <tunnel-id-printed-by-create>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: agent.your-domain.com
    service: http://127.0.0.1:3020
  - service: http_status:404
```

Update `config.PUBLIC_WEBHOOK_URL` to `https://agent.your-domain.com` and run `python update_webhooks.py`.

Run the tunnel as a background service:

```bash
# Linux: systemd unit (sudo cloudflared service install)
# Windows (admin PowerShell):
cloudflared service install
```

## Stopping

```bash
./stop.sh        # Linux/macOS
.\stop.ps1       # Windows
```

This stops the webhook. The Cloudflare Tunnel is managed separately (Quick Tunnel exits when the spawning shell does; named tunnel runs as a service).

## Diagnostics

```bash
python doctor.py
```

Prints `[OK]` / `[WARN]` / `[ERRO]` for each component. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes.
