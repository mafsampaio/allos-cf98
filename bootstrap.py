"""
WhatsApp Claude Agent — one-command bootstrap.

Runs deps check, config wizard, webhook server, Quick Tunnel via cloudflared,
captures the public URL, persists it in config.PUBLIC_WEBHOOK_URL, and pushes
it to every megaAPI session registered in config.SESSIONS.

Usage: python bootstrap.py
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


_QUICK_TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def extract_quick_tunnel_url(log_text: str) -> Optional[str]:
    """Find the trycloudflare.com URL inside cloudflared stdout/stderr."""
    match = _QUICK_TUNNEL_RE.search(log_text)
    return match.group(0) if match else None


def find_cloudflared() -> Optional[str]:
    """Return path to cloudflared.exe / cloudflared, or None."""
    direct = shutil.which("cloudflared")
    if direct:
        return direct
    if sys.platform == "win32":
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / (
            "Microsoft/WinGet/Packages/"
            "Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe/"
            "cloudflared.exe"
        )
        if winget.exists():
            return str(winget)
    return None


def check_python() -> None:
    if sys.version_info < (3, 8):
        sys.exit(f"ERROR: Python 3.8+ required (you have {sys.version.split()[0]}).")


def check_curl() -> None:
    if not shutil.which("curl"):
        sys.exit("ERROR: curl not found. Install it and re-run.")


def ensure_config() -> None:
    if Path("config.py").exists():
        return
    print("[bootstrap] config.py not found - running wizard...")
    code = subprocess.call([sys.executable, "setup_config.py"])
    if code != 0 or not Path("config.py").exists():
        sys.exit("ERROR: config wizard did not produce config.py.")


def start_webhook() -> subprocess.Popen:
    print("[bootstrap] starting webhook_server.py on :3020...")
    log = open("webhook.log", "ab")
    proc = subprocess.Popen(
        [sys.executable, "webhook_server.py"],
        stdout=log, stderr=log,
    )
    time.sleep(2)
    if proc.poll() is not None:
        sys.exit("ERROR: webhook_server.py exited immediately. Check webhook.log.")
    return proc


def start_quick_tunnel(cloudflared_path: str) -> tuple:
    print("[bootstrap] starting Quick Tunnel via cloudflared...")
    log_path = Path("cloudflared.log")
    log = open(log_path, "wb")
    proc = subprocess.Popen(
        [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:3020"],
        stdout=log, stderr=log,
    )
    deadline = time.time() + 30
    url: Optional[str] = None
    while time.time() < deadline:
        time.sleep(1)
        if proc.poll() is not None:
            sys.exit("ERROR: cloudflared exited. Check cloudflared.log.")
        url = extract_quick_tunnel_url(
            log_path.read_text(encoding="utf-8", errors="ignore")
        )
        if url:
            break
    if not url:
        proc.terminate()
        sys.exit("ERROR: cloudflared did not print a Quick Tunnel URL within 30s.")
    print(f"[bootstrap] tunnel up: {url}")
    return proc, url


def write_public_url(url: str) -> None:
    """Update config.PUBLIC_WEBHOOK_URL in-place (or append if missing)."""
    text = Path("config.py").read_text(encoding="utf-8")
    pat = re.compile(r'^PUBLIC_WEBHOOK_URL\s*=\s*[\'"][^\'"]*[\'"]', re.M)
    text, n = pat.subn(f'PUBLIC_WEBHOOK_URL = "{url}"', text)
    if n == 0:
        text += f'\n\nPUBLIC_WEBHOOK_URL = "{url}"\n'
    Path("config.py").write_text(text, encoding="utf-8")


def push_webhooks() -> None:
    print("[bootstrap] pushing webhook URL to megaAPI sessions...")
    code = subprocess.call([sys.executable, "update_webhooks.py"])
    if code != 0:
        sys.exit("ERROR: update_webhooks.py failed.")


def main() -> int:
    print("=" * 60)
    print("WhatsApp Claude Agent - Bootstrap")
    print("=" * 60)
    os.chdir(Path(__file__).resolve().parent)
    check_python()
    check_curl()
    cf = find_cloudflared()
    if not cf:
        sys.exit(
            "ERROR: cloudflared not found.\n"
            "  Windows: winget install Cloudflare.cloudflared\n"
            "  macOS:   brew install cloudflared\n"
            "  Linux:   see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        )
    ensure_config()
    webhook = start_webhook()
    try:
        tunnel, url = start_quick_tunnel(cf)
    except SystemExit:
        webhook.terminate()
        raise
    try:
        write_public_url(url)
        push_webhooks()
    except SystemExit:
        webhook.terminate()
        tunnel.terminate()
        raise
    print("")
    print("=" * 60)
    print("READY")
    print("=" * 60)
    print(f"  Public URL: {url}")
    print(f"  Webhook PID: {webhook.pid}  (logs: webhook.log)")
    print(f"  Tunnel  PID: {tunnel.pid}   (logs: cloudflared.log)")
    print("")
    print("Next:")
    print("  1. Open another terminal: claude")
    print("  2. Paste: 'Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1'")
    print("  3. Send a WhatsApp message to your number.")
    print("")
    print("To stop everything: ./scripts/stop.sh   (or .\\scripts\\stop.ps1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
