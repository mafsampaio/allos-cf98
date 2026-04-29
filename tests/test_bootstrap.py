"""Tests for bootstrap.py orchestration helpers."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from bootstrap import extract_quick_tunnel_url


def test_extract_url_from_cloudflared_log_quick_tunnel():
    log = """
2026-04-28T20:00:00Z INF Starting tunnel tunnelID=
2026-04-28T20:00:01Z INF |  Your quick Tunnel has been created! Visit it at:  |
2026-04-28T20:00:01Z INF |  https://random-words-1234.trycloudflare.com        |
2026-04-28T20:00:02Z INF Registered tunnel connection
"""
    assert extract_quick_tunnel_url(log) == "https://random-words-1234.trycloudflare.com"


def test_extract_url_returns_none_when_absent():
    log = "2026-04-28T20:00:00Z INF Starting tunnel\n2026-04-28T20:00:01Z INF Registered\n"
    assert extract_quick_tunnel_url(log) is None


def test_extract_url_strips_box_borders_and_whitespace():
    log = "|  https://abc-def-1234.trycloudflare.com  |"
    assert extract_quick_tunnel_url(log) == "https://abc-def-1234.trycloudflare.com"
