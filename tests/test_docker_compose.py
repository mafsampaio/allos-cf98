"""Tests for docker-compose.yml."""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE = os.path.join(ROOT, "docker-compose.yml")

yaml = pytest.importorskip("yaml")


def _load():
    with open(COMPOSE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_compose_exists():
    assert os.path.exists(COMPOSE)


def test_three_services():
    c = _load()
    services = c.get("services", {})
    assert "allos-webhook" in services
    assert "allos-tunnel" in services
    assert "allos-agent" in services


def test_all_services_restart_unless_stopped():
    c = _load()
    for name, svc in c["services"].items():
        assert svc.get("restart") == "unless-stopped", f"{name} missing restart policy"


def test_webhook_only_loopback():
    c = _load()
    ports = c["services"]["allos-webhook"].get("ports", [])
    for p in ports:
        assert p.startswith("127.0.0.1:") or p.startswith("localhost:"), \
            f"webhook expondo publicamente: {p}"


def test_agent_depends_on_webhook_healthy():
    c = _load()
    deps = c["services"]["allos-agent"].get("depends_on", {})
    assert "allos-webhook" in deps
    if isinstance(deps, dict):
        assert deps["allos-webhook"].get("condition") == "service_healthy"


def test_tunnel_depends_on_webhook_healthy():
    c = _load()
    deps = c["services"]["allos-tunnel"].get("depends_on", {})
    assert "allos-webhook" in deps


def test_volumes_bind_jsonl():
    c = _load()
    webhook_vols = c["services"]["allos-webhook"].get("volumes", [])
    agent_vols = c["services"]["allos-agent"].get("volumes", [])
    jsonl_str = "messages_session1.jsonl"
    assert any(jsonl_str in v for v in webhook_vols)
    assert any(jsonl_str in v for v in agent_vols)


def test_claude_auth_named_volume():
    c = _load()
    assert "claude-auth" in c.get("volumes", {})
    agent_vols = c["services"]["allos-agent"].get("volumes", [])
    assert any("claude-auth" in v for v in agent_vols)


def test_anthropic_env_vars_passthrough():
    c = _load()
    env = c["services"]["allos-agent"].get("environment", [])
    flat = " ".join(env) if isinstance(env, list) else " ".join(f"{k}={v}" for k, v in env.items())
    for v in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"):
        assert v in flat, f"missing env passthrough: {v}"


def _docker_alive():
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
    return r.returncode == 0


def test_compose_config_valid():
    """`docker compose config` parse OK. Skip if daemon offline."""
    if not _docker_alive():
        return
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE, "config", "--quiet"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, f"compose invalid: {result.stderr}"
