#!/usr/bin/env python3
"""
AllosAgent — Wizard interativo Docker (Trilha 3).

Coleta:
  - Provider LLM (Anthropic/MiniMax/Kimi/Z.ai/Custom)
  - Credenciais megaAPI (delega pro setup_config existente)
  - Modo tunnel (Named c/ token, ou Quick)
  - Sessao + defaults claude

Gera:
  - .env  (env vars)
  - docker-compose.override.yml (apenas se Quick Tunnel)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROVIDERS = {
    "1": {
        "name": "Anthropic oficial (assinatura Claude Code)",
        "env": {},
        "post_setup": (
            "Apos `docker compose up -d`, faca login 1x:\n"
            "  docker exec -it allos-agent claude /login"
        ),
    },
    "2": {
        "name": "MiniMax",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
            "ANTHROPIC_MODEL": "MiniMax-M2.7",
            "ANTHROPIC_SMALL_FAST_MODEL": "MiniMax-M2.7",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M2.7",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.7",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.7",
            "API_TIMEOUT_MS": "3000000",
        },
        "needs_token": True,
    },
    "3": {
        "name": "Kimi K2 (Moonshot)",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.moonshot.ai/anthropic",
            "ANTHROPIC_MODEL": "kimi-k2-instruct",
            "ANTHROPIC_SMALL_FAST_MODEL": "kimi-k2-instruct",
        },
        "needs_token": True,
    },
    "4": {
        "name": "Z.ai GLM",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.z.ai/anthropic",
            "ANTHROPIC_MODEL": "glm-4-plus",
        },
        "needs_token": True,
    },
    "5": {
        "name": "DeepSeek",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
            "ANTHROPIC_MODEL": "deepseek-v4-pro",
            "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-v4-pro",
            "API_TIMEOUT_MS": "600000",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        "needs_token": True,
    },
    "6": {
        "name": "OpenRouter (escolhe modelo)",
        "env": {
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
            "ANTHROPIC_API_KEY": "",  # OpenRouter usa AUTH_TOKEN; mantem var presente vazia
        },
        "needs_token": True,
        "ask_model": True,
    },
    "7": {
        "name": "Custom (cole BASE_URL/MODEL/TOKEN manual)",
        "env": {},
        "custom": True,
    },
}

# Sugestoes populares OpenRouter (usuario pode digitar livre)
OPENROUTER_MODELS_HINTS = [
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-haiku-4.5",
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k2-instruct",
    "z-ai/glm-4-plus",
    "openai/gpt-5",
    "google/gemini-2.5-pro",
    "meta-llama/llama-4-maverick",
    "qwen/qwen3-235b",
]


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or (default or "")


def _ensure_docker() -> None:
    if not shutil.which("docker"):
        print("ERRO: docker nao encontrado no PATH. Instale antes (https://docs.docker.com/engine/install/).")
        sys.exit(1)


def _pick_provider() -> dict:
    print("Escolha o provider LLM:")
    for k, v in PROVIDERS.items():
        print(f"  [{k}] {v['name']}")
    while True:
        choice = _ask("Opcao", default="1")
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print("  Opcao invalida.")


def _collect_provider_env(provider: dict) -> dict:
    env = dict(provider["env"])
    if provider.get("custom"):
        env["ANTHROPIC_BASE_URL"] = _ask("ANTHROPIC_BASE_URL")
        env["ANTHROPIC_MODEL"] = _ask("ANTHROPIC_MODEL")
        env["ANTHROPIC_AUTH_TOKEN"] = _ask("ANTHROPIC_AUTH_TOKEN")
        return env
    if provider.get("needs_token"):
        env["ANTHROPIC_AUTH_TOKEN"] = _ask("ANTHROPIC_AUTH_TOKEN (cole token do provider)")
    if provider.get("ask_model"):
        print("\nSugestoes populares OpenRouter:")
        for m in OPENROUTER_MODELS_HINTS:
            print(f"  - {m}")
        model = _ask("\nANTHROPIC_MODEL (cole nome completo do modelo)",
                     default="anthropic/claude-sonnet-4.6")
        env["ANTHROPIC_MODEL"] = model
        # OpenRouter aceita override per-tier
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = _ask(
            "ANTHROPIC_DEFAULT_OPUS_MODEL (Enter = mesmo do principal)",
            default=model)
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = _ask(
            "ANTHROPIC_DEFAULT_SONNET_MODEL (Enter = mesmo do principal)",
            default=model)
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = _ask(
            "ANTHROPIC_DEFAULT_HAIKU_MODEL (Enter = mesmo do principal)",
            default=model)
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = _ask(
            "CLAUDE_CODE_SUBAGENT_MODEL (Enter = mesmo do principal)",
            default=model)
    return env


def _setup_config_py() -> None:
    cfg = ROOT / "config.py"
    if cfg.exists():
        print(f"\nconfig.py ja existe — pulando wizard megaAPI.")
        print(f"Edite {cfg} manualmente se precisar.")
        return
    print("\n--- megaAPI / config.py setup ---")
    print("Rodando wizard existente (whatsapp_agent.setup_config)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "whatsapp_agent.setup_config"],
            cwd=ROOT, check=False,
        )
    except Exception as exc:
        print(f"AVISO: setup_config falhou: {exc}")
        print("Voce precisa criar config.py manualmente antes do `docker compose up -d`.")


def _pick_tunnel(env: dict) -> None:
    print("\n--- Cloudflare Tunnel ---")
    print("  [1] Named Tunnel (URL fixa, precisa token CF Zero Trust)")
    print("  [2] Quick Tunnel (URL random a cada restart, zero config)")
    choice = _ask("Opcao", default="2")
    if choice == "1":
        env["TUNNEL_TOKEN"] = _ask("TUNNEL_TOKEN (cole do painel CF Zero Trust)")
    else:
        override_src = ROOT / "docker-compose.override.yml.example"
        override_dst = ROOT / "docker-compose.override.yml"
        if override_src.exists() and not override_dst.exists():
            shutil.copy(override_src, override_dst)
            print(f"  Copiado: {override_dst.name} (Quick Tunnel ativo)")
        env["TUNNEL_TOKEN"] = ""


def _write_env(env: dict) -> Path:
    env_path = ROOT / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# Gerado por scripts/docker_setup.py\n")
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    return env_path


def main() -> None:
    _ensure_docker()

    print("=" * 60)
    print("AllosAgent — Wizard Docker (Trilha 3)")
    print("=" * 60)
    print()

    provider = _pick_provider()
    env = _collect_provider_env(provider)

    _setup_config_py()
    _pick_tunnel(env)

    env["SESSION_NUM"] = _ask("Numero da sessao", default="1")
    env["CLAUDE_MODEL"] = _ask("Modelo Claude Code", default="claude-sonnet-4-6")
    env["CLAUDE_EFFORT"] = _ask("Effort", default="medium")

    env_path = _write_env(env)
    print(f"\nGerado: {env_path}")

    print()
    print("=" * 60)
    print("Setup concluido. Proximos passos:")
    print()
    print("  docker compose up -d --build")
    print("  docker compose logs -f")
    print()
    if provider.get("post_setup"):
        print(provider["post_setup"])
        print()
    print(f"Webhook URL pra megaAPI: <URL_DO_TUNNEL>/?session={env['SESSION_NUM']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
