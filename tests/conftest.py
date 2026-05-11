"""Shared pytest fixtures."""
import sys
import pytest


@pytest.fixture
def tmp_workdir(tmp_path, monkeypatch):
    """Isolated cwd. Repo root on sys.path so production modules import."""
    import os
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    monkeypatch.syspath_prepend(repo_root)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def fake_config(tmp_workdir):
    """Write minimal config.py into tmp cwd. Yields the cwd path."""
    cfg = '''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
EVOLUTION_HOST = "https://evolution.example.com"
PUBLIC_WEBHOOK_URL = "https://allos.example.com"
SESSIONS = {
    "1": {
        "instance": "inst1",
        "token":    "tok1",
        "phone":    "5511999999999",
        "lid":      "11111111111111",
    },
}
ALLOWED_PHONE      = SESSIONS["1"]["phone"]
ALLOWED_LID        = SESSIONS["1"]["lid"]
EVOLUTION_INSTANCE = SESSIONS["1"]["instance"]
EVOLUTION_TOKEN    = SESSIONS["1"]["token"]
EVOLUTION_BASE_URL = f"{EVOLUTION_HOST}/message/sendText/{EVOLUTION_INSTANCE}"
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")
    sys.modules.pop("config", None)
    sys.path.insert(0, str(tmp_workdir))
    yield tmp_workdir
    if str(tmp_workdir) in sys.path:
        sys.path.remove(str(tmp_workdir))
    sys.modules.pop("config", None)
