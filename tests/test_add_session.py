"""Tests for add_session wizard (Evolution edition)."""
import sys
from unittest.mock import patch


def _seed(tmp_workdir, sessions_block):
    cfg = f'''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
EVOLUTION_HOST = "https://evolution.example.com"
PUBLIC_WEBHOOK_URL = "https://allos.example.com"
SESSIONS = {{
{sessions_block}
}}
ALLOWED_PHONE      = "111"
ALLOWED_LID        = ""
EVOLUTION_INSTANCE = "i1"
EVOLUTION_TOKEN    = "t1"
EVOLUTION_BASE_URL = ""
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")


def test_appends_second_session(fake_config, tmp_workdir):
    sys.modules.pop("whatsapp_agent.add_session", None)
    _seed(tmp_workdir, '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},')
    from whatsapp_agent import add_session

    inputs = iter(["second-instance", "tok2", "5511888888888"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"2":' in content
    assert "second-instance" in content
    assert "5511888888888" in content
    assert '"1":' in content


def test_picks_next_free_id(fake_config, tmp_workdir):
    sys.modules.pop("whatsapp_agent.add_session", None)
    _seed(tmp_workdir,
          '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},\n'
          '    "2": {"instance": "i2", "token": "t2", "phone": "222", "lid": ""},')
    from whatsapp_agent import add_session

    inputs = iter(["i3", "t3", "5511777777777"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"3":' in content
