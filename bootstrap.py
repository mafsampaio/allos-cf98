"""
WhatsApp Claude Agent — one-command bootstrap.

Runs deps check, config wizard, webhook server, Quick Tunnel via cloudflared,
captures the public URL, persists it in config.PUBLIC_WEBHOOK_URL, and pushes
it to every megaAPI session registered in config.SESSIONS.

Usage: python bootstrap.py
"""
import re
from typing import Optional


_QUICK_TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def extract_quick_tunnel_url(log_text: str) -> Optional[str]:
    """Find the trycloudflare.com URL inside cloudflared stdout/stderr."""
    match = _QUICK_TUNNEL_RE.search(log_text)
    return match.group(0) if match else None


if __name__ == "__main__":
    raise SystemExit("bootstrap.main is implemented in Task 5; only helpers exist now.")
