# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- One-command bootstrap (`python bootstrap.py`) with Quick Tunnel.
- Cloudflare Tunnel support replacing ngrok.
- `update_webhooks.py` to push webhook URL to all megaAPI sessions.
- Parametric `<SESSAO>` placeholder in `CLAUDE_PROMPT.md` for multi-session reuse.
- MIT license, CONTRIBUTING, TROUBLESHOOTING, GitHub issue/PR templates.
- CI workflow running pytest on every push.
- `pyproject.toml` for `pip install -e .` developer install.

### Changed
- Repository reorganized: source under `src/whatsapp_agent/`, scripts under `scripts/`.
- README rewritten for OSS audience.

### Removed
- ngrok references in scripts and docs (kept as historical mention only).

## [1.0.0-trilha1] — 2026-04-28

### Added
- Multi-session support (multiple WhatsApp instances per deployment).
- Multimodal: image (Claude Read tool), audio (OpenAI Whisper), text in/out.
- `add_session.py` wizard, `discover_lid.py`, `media_handler.py`, `transcribe.py`.
- 26 pytest tests.

[Unreleased]: https://github.com/giovani-junior-dev/Allos/compare/v1.0-trilha1...HEAD
[1.0.0-trilha1]: https://github.com/giovani-junior-dev/Allos/releases/tag/v1.0-trilha1
