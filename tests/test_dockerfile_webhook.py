"""Tests for docker/Dockerfile.webhook."""
import os
import re
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE = os.path.join(ROOT, "docker", "Dockerfile.webhook")


def _content():
    with open(DOCKERFILE, encoding="utf-8") as f:
        return f.read()


def test_dockerfile_exists():
    assert os.path.exists(DOCKERFILE)


def test_uses_python_slim_base():
    assert re.search(r"^FROM python:3\.\d+-slim", _content(), re.MULTILINE)


def test_exposes_port_3020():
    assert "EXPOSE 3020" in _content()


def test_runs_webhook_server_module():
    c = _content()
    assert "whatsapp_agent.webhook_server" in c
    assert "CMD" in c or "ENTRYPOINT" in c


def test_copies_source_module():
    c = _content()
    assert "src/whatsapp_agent" in c or "whatsapp_agent" in c


def test_has_healthcheck():
    c = _content()
    assert "HEALTHCHECK" in c
    assert "/healthz" in c


def test_no_secrets_baked_in():
    c = _content().lower()
    for forbidden in ("mega_token", "openai_api_key", "anthropic_auth_token", "sk-"):
        assert forbidden not in c, f"secret {forbidden} hardcoded"


def _docker_daemon_alive():
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
    return r.returncode == 0


def test_docker_build_succeeds():
    """Smoke test build. Skip if Docker daemon indisponivel."""
    if not _docker_daemon_alive():
        return
    result = subprocess.run(
        ["docker", "build", "-f", DOCKERFILE, "-t", "allos-webhook-test:ci", ROOT],
        capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, f"build failed: {result.stderr[-500:]}"
