"""Tests for add_session wizard."""
import sys
from unittest.mock import patch


def _seed(tmp_workdir, sessions_block):
    cfg = f'''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
MEGA_HOST = "https://apibusiness1.megaapi.com.br"
SESSIONS = {{
{sessions_block}
}}
ALLOWED_PHONE = "111"
ALLOWED_LID = ""
MEGA_INSTANCE = "i1"
MEGA_TOKEN = "t1"
MEGA_BASE_URL = ""
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")


def test_appends_second_session(fake_config, tmp_workdir):
    sys.modules.pop("add_session", None)
    _seed(tmp_workdir, '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},')
    import add_session

    inputs = iter(["megabusiness-second", "tok2", "5511888888888"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"2":' in content
    assert "megabusiness-second" in content
    assert "5511888888888" in content
    assert '"1":' in content


def test_picks_next_free_id(fake_config, tmp_workdir):
    sys.modules.pop("add_session", None)
    _seed(tmp_workdir,
          '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},\n'
          '    "2": {"instance": "i2", "token": "t2", "phone": "222", "lid": ""},')
    import add_session

    inputs = iter(["i3", "t3", "5511777777777"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"3":' in content
