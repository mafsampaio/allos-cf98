"""Tests for setup_config wizard."""
from unittest.mock import patch


def test_writes_config_with_openai_key(fake_config, tmp_workdir):
    # delete the seeded config so wizard writes fresh
    import sys
    sys.modules.pop("setup_config", None)
    (tmp_workdir / "config.py").unlink()

    import setup_config

    inputs = iter([
        "meutoken",
        "megabusiness-test",
        "abc123",
        "5511999999999",
        "sk-test123",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'meutoken'" in content
    assert "'sk-test123'" in content
    assert "OPENAI_API_KEY" in content


def test_blank_openai_key_allowed(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("setup_config", None)
    (tmp_workdir / "config.py").unlink()
    import setup_config

    inputs = iter([
        "meutoken",
        "megabusiness-test",
        "abc123",
        "5511999999999",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY = ''" in content
