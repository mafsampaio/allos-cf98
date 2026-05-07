"""Tests for docker/agent_loop.sh."""
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "docker", "agent_loop.sh")


def _content():
    with open(SCRIPT, encoding="utf-8") as f:
        return f.read()


def test_script_exists():
    assert os.path.exists(SCRIPT)


def test_has_shebang():
    with open(SCRIPT, encoding="utf-8") as f:
        first = f.readline().strip()
    assert first.startswith("#!/usr/bin/env bash") or first.startswith("#!/bin/bash")


def test_uses_continue_loop():
    c = _content()
    assert "--continue" in c
    assert "while true" in c


def test_dangerously_skip_permissions():
    assert "--dangerously-skip-permissions" in _content()


def test_first_run_flag():
    c = _content()
    assert "FIRST_RUN_FLAG" in c


def test_heartbeat_touch():
    assert "/tmp/agent-alive" in _content()


def test_supports_session_num_env():
    assert "SESSION_NUM" in _content()


def test_supports_model_env():
    c = _content()
    assert "CLAUDE_MODEL" in c


def test_bash_syntax_valid():
    if not shutil.which("bash"):
        return
    # Convert Windows path to POSIX for git-bash if available
    script_path = SCRIPT
    cygpath = shutil.which("cygpath")
    if cygpath:
        r = subprocess.run([cygpath, "-u", SCRIPT], capture_output=True, text=True)
        if r.returncode == 0:
            script_path = r.stdout.strip()
    result = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
    if result.returncode == 127:
        return  # bash cannot resolve path; skip on this platform
    assert result.returncode == 0, f"syntax: {result.stderr}"
