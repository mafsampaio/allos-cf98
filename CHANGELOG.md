# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.1] — 2026-04-29

### Fixed
- `bootstrap.py` now passes `--config nul` (Windows) / `--config /dev/null` (POSIX) when starting the Quick Tunnel, so a pre-existing `~/.cloudflared/config.yml` from a named-tunnel install does not hijack the Quick Tunnel routing with HTTP 404. (Discovered during fresh-clone Allos-test validation on a host that already had `allos.dev-junior.com` configured.)
- Wizard `setup_config.py` post-install instructions refreshed for the post-Task-15 layout (`python scripts/bootstrap.py`, `python -m whatsapp_agent.discover_lid`, etc.) — replaces the obsolete `start.ps1` / `python discover_lid.py` references.
- `send_message.py` strips any pre-existing `*Claude Code*` signature from the body before appending — prevents duplicated signatures when the agent (e.g. on non-Anthropic models) writes the signature into the reply text. Covered by tests.
- Prompt rules: `fromMe` is now explicitly stated as **not** a filter — the only loop guard is the `*Claude Code*` text signature. Self-chat is the default use case; `fromMe: true` must be processed.
- Prompt rules: `send_message` must be called exactly once per user message — no automatic retry with sanitized text. Strip emojis / non-BMP characters before the single call instead.

### Added
- README explicitly notes that the prompt was designed and validated against Anthropic Claude (Sonnet/Opus). Other models (Kimi, GPT-4) work because of the rules in CLAUDE.md and the `send_message` defense, but Anthropic Claude is the canonical choice for first-try-correct behavior.
- `TROUBLESHOOTING.md` covers four new real-world scenarios captured during Allos-test / Allos3 validation:
  1. Quick Tunnel returns 404 because of an inherited `~/.cloudflared/config.yml`.
  2. Stale `monitor.py` from a previous Claude Code session in another folder silently consumes JSONL of the wrong project.
  3. Wizard accepted an instance whose connected phone does not match `ALLOWED_PHONE` (validation gap).
  4. Spam / newsletter traffic from a megaAPI instance whose webhook still points at this tunnel.

## [1.1.0] — 2026-04-29

### Added
- Beads (`bd`) integration for persistent task memory: auto-installed and initialized by `bootstrap.py`, documented in `CLAUDE.md` and `TROUBLESHOOTING.md`.
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

[Unreleased]: https://github.com/giovani-junior-dev/Allos/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/giovani-junior-dev/Allos/releases/tag/v1.1.1
[1.1.0]: https://github.com/giovani-junior-dev/Allos/releases/tag/v1.1.0
[1.0.0-trilha1]: https://github.com/giovani-junior-dev/Allos/releases/tag/v1.0-trilha1
