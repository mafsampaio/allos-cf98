"""Tests for setup_config wizard (Evolution edition)."""
from unittest.mock import patch


def test_writes_config_with_openai_key(fake_config, tmp_workdir):
    # delete the seeded config so wizard writes fresh
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()

    from whatsapp_agent import setup_config

    inputs = iter([
        "meutoken",                              # cmd_token
        "https://evolution.cf98.online",         # evolution host
        "marcilio-claude",                       # instance
        "abc123",                                # token
        "https://allos.cf98.online",             # public webhook url
        "5511999999999",                         # phone
        "sk-test123",                            # openai key
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'meutoken'" in content
    assert "'sk-test123'" in content
    assert "OPENAI_API_KEY" in content
    assert "'https://evolution.cf98.online'" in content
    assert "'marcilio-claude'" in content
    assert "'https://allos.cf98.online'" in content


def test_blank_openai_key_allowed(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()
    from whatsapp_agent import setup_config

    inputs = iter([
        "meutoken",
        "https://evolution.cf98.online",
        "marcilio-claude",
        "abc123",
        "https://allos.cf98.online",
        "5511999999999",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY = ''" in content


def test_host_validation_rejects_then_accepts(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()
    from whatsapp_agent import setup_config

    inputs = iter([
        "",                                        # cmd_token skip
        "not-a-url",                               # invalid host -> retry
        "https://evolution.cf98.online/",          # trailing slash, valid -> stripped
        "marcilio-claude",
        "tok-x",
        "https://allos.cf98.online",
        "5511988888888",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'https://evolution.cf98.online'" in content
    assert "evolution.cf98.online/'" not in content  # trailing slash stripped
