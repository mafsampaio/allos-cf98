# Trilha 3 — Docker OSS Distribution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Planejada (2026-05-07). bd ticket: `teste-iac`.

**Goal:** Disponibilizar AllosAgent como **stack Docker one-command** pra leigos rodarem em VPS sem mexer em systemd/tmux/Cloudflare login interativo. **Não substitui Trilha 2** — convive como caminho alternativo (Trilha 2 = systemd nativo, Trilha 3 = containers).

**Trilha 2 status:** já implementada manualmente pelo usuário em VPS Ubuntu 24.04 via tutorial `DEPLOY_24_7_LINUX.md` (rodando 24/7 com 3 systemd user services). Plano `2026-04-28-trilha-2-vps-deploy.md` permanece intocado como referência arquitetural.

---

## Contexto

**Problema:** README atual orienta setup local Windows (Trilha 1) ou VPS via systemd (Trilha 2). Ambos exigem conhecimento de shell, systemd, e/ou Cloudflare CLI. Pra distribuição OSS, falta caminho que um leigo execute em <5 min.

**Solução proposta:** stack Docker Compose com 3 services + wizard interativo. `git clone` → `python scripts/docker_setup.py` → `docker compose up -d`.

**Insights chave do tutorial real `C:\Users\GEOVANE\Desktop\DEPLOY_24_7_LINUX.md`** que viabilizam Docker headless robusto:

1. **`claude --continue "continue monitorando"` em loop bash** retoma sessão sem precisar re-colar `CLAUDE_PROMPT.md`. Elimina hack frágil de `tmux send-keys` cole prompt após restart.
2. **`--dangerously-skip-permissions`** = headless real, zero prompts de aprovação.
3. **Env vars `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_MODEL`** = Claude Code provider-agnostic (Anthropic oficial, MiniMax, Kimi K2, Z.ai GLM, qualquer endpoint Anthropic-compatible) sem OAuth interativo.
4. **Flags `--model` / `--effort`** estáveis pra escolher modelo + esforço por chamada.
5. **Limitação aceita** (do próprio tutorial linha 546): crash de auth Claude oficial requer attach manual. Aceitável pra OSS self-host.

---

## Arquitetura

```
docker-compose.yml
├── allos-webhook   Python 3.11-slim, :3020 (loopback only)
├── allos-tunnel    cloudflare/cloudflared:latest (Named ou Quick)
└── allos-agent     custom image (Node + Python + claude CLI + bash loop)
```

Fluxo:

```
WhatsApp → megaAPI → CF Tunnel → allos-webhook:3020
                                      ↓ append JSONL (volume bind-mount)
                                 messages_session1.jsonl
                                      ↓ tail (volume bind-mount)
                                 allos-agent
                                  (claude --continue loop)
                                      ↓ send_message.py
                                 megaAPI → WhatsApp
```

**Volumes** (path absoluto host → container):

- `./config.py:/app/config.py:ro`
- `./messages_session1.jsonl:/app/messages_session1.jsonl` (rw — webhook escreve, agent lê)
- `./processed_ids_session1.txt:/app/processed_ids_session1.txt`
- `./media/:/app/media/`
- `./CLAUDE_PROMPT.md:/app/CLAUDE_PROMPT.md:ro`
- `./raw_debug.jsonl:/app/raw_debug.jsonl`
- `claude-auth:/home/allos/.claude` (volume nomeado, persiste auth Anthropic oficial)

**Restart policy:** `unless-stopped` em todos. VPS reboot → Docker daemon sobe → containers voltam.

**Healthchecks:**
- `allos-webhook`: `curl -f http://localhost:3020/healthz` cada 30s
- `allos-agent`: arquivo `/tmp/agent-alive` modificado nos últimos 180s
- `allos-tunnel`: imagem oficial Cloudflare já tem healthcheck embutido

---

## Por que cada decisão

| Decisão | Razão |
|---------|-------|
| 3 containers separados (vs 1 monolítico) | Falha isolada — webhook crash não derruba agent. Logs separados. |
| Bind-mount JSONL (vs network IPC) | Zero refactor de `webhook_server.py`/`monitor.py`. Já é o protocolo atual. |
| `claude --continue` em loop bash | Reaproveita solução validada da Trilha 2. Sem `tmux send-keys` frágil. |
| Env vars `ANTHROPIC_*` | Provider-agnostic. Container reproducible. Sem OAuth interativo bloqueante. |
| `restart: unless-stopped` (vs `always`) | Não reinicia se user `docker compose down` deliberado. |
| Cloudflared via imagem oficial | Mantida pela Cloudflare, healthcheck pronto, atualização separada do app. |
| Wizard Python (vs shell) | Reusa código de validação do `bootstrap.py` existente. Cross-platform. |
| `tmux` removido do agent (vs incluído) | Não necessário — bash loop direto faz mesma função em container. |
| Volume nomeado `claude-auth` | Persiste login OAuth Anthropic entre `docker compose down/up`. |
| `127.0.0.1:3020` no host | Webhook não exposto na internet — só cloudflared acessa. |

---

## File Structure

**Novos arquivos:**
- `docker/Dockerfile.webhook` — Python 3.11-slim
- `docker/Dockerfile.agent` — Node 20-slim + Python + tmux + claude CLI
- `docker/agent_loop.sh` — bash loop com `claude --continue` (adaptação `claude_monitor_loop.sh`)
- `docker-compose.yml` — orquestração 3 services
- `docker-compose.override.yml.example` — Quick Tunnel mode (sem `TUNNEL_TOKEN`)
- `scripts/docker_setup.py` — wizard interativo (provider + megaAPI + tunnel)
- `.env.example` — template provider-agnostic
- `.dockerignore`
- `docs/DOCKER.md` — runbook (build/up/logs/troubleshoot/switch provider/multi-sessão)
- `tests/test_docker_compose.py` — lint compose, valida services + healthchecks
- `tests/test_dockerfile_webhook.py` — smoke test build (skip se Docker indisponível)
- `tests/test_agent_loop.py` — bash syntax + presença de flags chave

**Modificados (mínimo):**
- `src/whatsapp_agent/webhook_server.py` — `do_GET /healthz` (já planejado em Task 1 da Trilha 2 — reaproveitar se ainda não implementado, ou se Trilha 2 implementou, pular)
- `.gitignore` — adicionar `.env`, `cf-tunnel/`, `.docker/`
- `README.md` — nova seção "Quick Start (Docker)" antes da seção VPS atual
- `CLAUDE_PROMPT.md` — adicionar nota: "se rodando em Docker, paths são `/app/...`"

**Não tocados:**
- `monitor.py`, `send_message.py`, `media_handler.py`, `transcribe.py`, `add_session.py`, `discover_lid.py`, `setup_config.py`, `bootstrap.py`
- `docs/plans/2026-04-28-trilha-2-vps-deploy.md` — preservado intocado
- `C:\Users\GEOVANE\Desktop\DEPLOY_24_7_LINUX.md` — preservado, vira referência cross-link
- `install/`, `systemd/` (se já criados pela Trilha 2)

---

## Task 1 — Healthcheck `/healthz` no webhook

**Files:**
- Modify: `src/whatsapp_agent/webhook_server.py`
- Create/extend: `tests/test_healthz.py`

> **Nota:** se Trilha 2 já implementou Task 1 (healthcheck), pule este passo. Caso contrário, copie tasks 1-5 do plano `2026-04-28-trilha-2-vps-deploy.md`.

- [ ] Verificar se `do_GET` existe em `webhook_server.py`. Se sim, pular task. Se não, implementar conforme Trilha 2 Task 1.

---

## Task 2 — `docker/Dockerfile.webhook`

**Files:**
- Create: `docker/Dockerfile.webhook`
- Create: `tests/test_dockerfile_webhook.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for docker/Dockerfile.webhook."""
import os
import re
import subprocess
import shutil


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


def test_no_secrets_baked_in():
    """Dockerfile não deve ter MEGA_TOKEN / OPENAI / ANTHROPIC tokens."""
    c = _content().lower()
    for forbidden in ("mega_token", "openai_api_key", "anthropic_auth_token"):
        assert forbidden not in c, f"secret {forbidden} hardcoded"


def test_docker_build_succeeds():
    """Smoke test build. Skip if Docker indisponível."""
    if not shutil.which("docker"):
        return  # skip
    result = subprocess.run(
        ["docker", "build", "-f", DOCKERFILE, "-t", "allos-webhook-test:ci", ROOT],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, f"build failed: {result.stderr[-500:]}"
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_dockerfile_webhook.py -v
```

- [ ] **Step 3: Create `docker/Dockerfile.webhook`**

```dockerfile
FROM python:3.11-slim

# OS deps mínimas (curl pro healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Source code
COPY src/whatsapp_agent /app/whatsapp_agent
COPY config.example.py /app/config.example.py

# Webhook precisa de stdlib-only — nada pra instalar
EXPOSE 3020

# config.py virá via volume bind-mount
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3020/healthz || exit 1

CMD ["python", "-m", "whatsapp_agent.webhook_server"]
```

- [ ] **Step 4: Run tests, verify PASS** (skip docker build se ambiente sem Docker)

```bash
python -m pytest tests/test_dockerfile_webhook.py -v
```

- [ ] **Step 5: Commit**

```bash
git add docker/Dockerfile.webhook tests/test_dockerfile_webhook.py
git commit -m "feat(docker): Dockerfile.webhook com healthcheck embutido"
```

---

## Task 3 — `docker/agent_loop.sh`

**Files:**
- Create: `docker/agent_loop.sh`
- Create: `tests/test_agent_loop.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for docker/agent_loop.sh."""
import os
import subprocess


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "docker", "agent_loop.sh")


def _content():
    with open(SCRIPT, encoding="utf-8") as f:
        return f.read()


def test_script_exists():
    assert os.path.exists(SCRIPT)


def test_has_shebang():
    with open(SCRIPT, encoding="utf-8") as f:
        first = f.readline().strip()
    assert first.startswith("#!/usr/bin/env bash") or first.startswith("#!/bin/bash")


def test_uses_continue_loop():
    """Loop deve usar claude --continue (do Trilha 2 real)."""
    c = _content()
    assert "--continue" in c
    assert "while true" in c


def test_dangerously_skip_permissions():
    """Headless mode obrigatório."""
    assert "--dangerously-skip-permissions" in _content()


def test_first_run_flag():
    """Primeira execução deve plantar prompt fresh, depois usa --continue."""
    c = _content()
    assert "FIRST_RUN_FLAG" in c or "first_run" in c.lower()


def test_heartbeat_touch():
    """Healthcheck depende de /tmp/agent-alive."""
    assert "/tmp/agent-alive" in _content()


def test_supports_session_num_env():
    assert "SESSION_NUM" in _content()


def test_supports_model_env():
    """Provider switch via env."""
    c = _content()
    assert "CLAUDE_MODEL" in c or "ANTHROPIC_MODEL" in c


def test_bash_syntax_valid():
    result = subprocess.run(["bash", "-n", SCRIPT], capture_output=True, text=True)
    assert result.returncode == 0, f"syntax: {result.stderr}"
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Create `docker/agent_loop.sh`** (adaptado do `claude_monitor_loop.sh` real)

```bash
#!/usr/bin/env bash
# ============================================================
# agent_loop.sh
# ----------------------------------------------------------
# Mantém Claude Code rodando em loop dentro do container.
# Adaptado de DEPLOY_24_7_LINUX.md / claude_monitor_loop.sh.
#
# Primeira run: planta prompt fresh (CLAUDE_PROMPT.md).
# Runs subsequentes: --continue retoma sessão.
# Crash do claude → restart 5s.
# Heartbeat /tmp/agent-alive pra healthcheck Docker.
# ============================================================
set -u

: "${SESSION_NUM:=1}"
: "${CLAUDE_MODEL:=}"
: "${CLAUDE_EFFORT:=medium}"

cd /app

PROMPT="Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: ${SESSION_NUM}"
FIRST_RUN_FLAG=/app/.claude_started_session${SESSION_NUM}

# Build flags array
CLAUDE_FLAGS=("--dangerously-skip-permissions")
[ -n "$CLAUDE_MODEL" ] && CLAUDE_FLAGS+=("--model" "$CLAUDE_MODEL")
[ -n "$CLAUDE_EFFORT" ] && CLAUDE_FLAGS+=("--effort" "$CLAUDE_EFFORT")

# Heartbeat background updater
(while true; do
    touch /tmp/agent-alive
    sleep 30
done) &

# Validate auth: env-based OR ~/.claude/ has session
if [ -z "${ANTHROPIC_AUTH_TOKEN:-}" ] && [ ! -d "$HOME/.claude/projects" ]; then
    echo "[agent_loop] WARN: nem ANTHROPIC_AUTH_TOKEN nem ~/.claude/ login. Esperando login manual via 'docker exec -it allos-agent claude /login'..."
fi

# First run plants the prompt
if [ ! -f "$FIRST_RUN_FLAG" ]; then
    echo "[agent_loop] first run: starting fresh session ${SESSION_NUM}"
    touch "$FIRST_RUN_FLAG"
    claude "${CLAUDE_FLAGS[@]}" "$PROMPT" || true
fi

# Resume loop
while true; do
    echo "[agent_loop] resuming session"
    claude "${CLAUDE_FLAGS[@]}" --continue "continue monitorando" || true
    echo "[agent_loop] claude exited; restart in 5s"
    sleep 5
done
```

- [ ] **Step 4: chmod + tests pass**

```bash
chmod +x docker/agent_loop.sh
python -m pytest tests/test_agent_loop.py -v
```

- [ ] **Step 5: Commit**

```bash
git add docker/agent_loop.sh tests/test_agent_loop.py
git commit -m "feat(docker): agent_loop.sh reusa --continue do Trilha 2"
```

---

## Task 4 — `docker/Dockerfile.agent`

**Files:**
- Create: `docker/Dockerfile.agent`

- [ ] **Step 1: Create file**

```dockerfile
FROM node:20-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# User não-root pra rodar claude
RUN useradd -m -s /bin/bash -u 1000 allos

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

USER allos
WORKDIR /app

# Loop script
COPY --chown=allos:allos docker/agent_loop.sh /usr/local/bin/agent_loop.sh

# Healthcheck: /tmp/agent-alive < 180s
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD test -f /tmp/agent-alive && \
        test $(($(date +%s) - $(stat -c %Y /tmp/agent-alive))) -lt 180

ENTRYPOINT ["/usr/local/bin/agent_loop.sh"]
```

- [ ] **Step 2: Smoke build local**

```bash
docker build -f docker/Dockerfile.agent -t allos-agent:test .
docker run --rm allos-agent:test claude --version
```

- [ ] **Step 3: Commit**

```bash
git add docker/Dockerfile.agent
git commit -m "feat(docker): Dockerfile.agent com claude CLI + bash loop"
```

---

## Task 5 — `docker-compose.yml`

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.override.yml.example`
- Create: `tests/test_docker_compose.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for docker-compose.yml."""
import os
import subprocess
import shutil
import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE = os.path.join(ROOT, "docker-compose.yml")


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
    """Webhook NÃO deve expor :3020 publicamente."""
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


def test_volumes_bind_jsonl():
    c = _load()
    webhook_vols = c["services"]["allos-webhook"].get("volumes", [])
    agent_vols = c["services"]["allos-agent"].get("volumes", [])
    jsonl_str = "messages_session1.jsonl"
    assert any(jsonl_str in v for v in webhook_vols)
    assert any(jsonl_str in v for v in agent_vols)


def test_compose_config_valid():
    """`docker compose config` parse OK."""
    if not shutil.which("docker"):
        return
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE, "config", "--quiet"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, f"compose invalid: {result.stderr}"
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  allos-webhook:
    build:
      context: .
      dockerfile: docker/Dockerfile.webhook
    container_name: allos-webhook
    restart: unless-stopped
    ports:
      - "127.0.0.1:3020:3020"
    volumes:
      - ./config.py:/app/config.py:ro
      - ./messages_session1.jsonl:/app/messages_session1.jsonl
      - ./processed_ids_session1.txt:/app/processed_ids_session1.txt
      - ./media:/app/media
      - ./raw_debug.jsonl:/app/raw_debug.jsonl
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3020/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  allos-tunnel:
    image: cloudflare/cloudflared:latest
    container_name: allos-tunnel
    restart: unless-stopped
    depends_on:
      allos-webhook:
        condition: service_healthy
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN}
    # Sem TUNNEL_TOKEN: use docker-compose.override.yml.example pra Quick Tunnel

  allos-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    container_name: allos-agent
    restart: unless-stopped
    depends_on:
      allos-webhook:
        condition: service_healthy
    environment:
      - SESSION_NUM=${SESSION_NUM:-1}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-}
      - ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN:-}
      - ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-}
      - ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL:-}
      - ANTHROPIC_DEFAULT_SONNET_MODEL=${ANTHROPIC_DEFAULT_SONNET_MODEL:-}
      - ANTHROPIC_DEFAULT_OPUS_MODEL=${ANTHROPIC_DEFAULT_OPUS_MODEL:-}
      - ANTHROPIC_DEFAULT_HAIKU_MODEL=${ANTHROPIC_DEFAULT_HAIKU_MODEL:-}
      - API_TIMEOUT_MS=${API_TIMEOUT_MS:-3000000}
      - CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
      - CLAUDE_MODEL=${CLAUDE_MODEL:-claude-sonnet-4-6}
      - CLAUDE_EFFORT=${CLAUDE_EFFORT:-medium}
    volumes:
      - ./config.py:/app/config.py:ro
      - ./messages_session1.jsonl:/app/messages_session1.jsonl
      - ./processed_ids_session1.txt:/app/processed_ids_session1.txt
      - ./media:/app/media
      - ./CLAUDE_PROMPT.md:/app/CLAUDE_PROMPT.md:ro
      - claude-auth:/home/allos/.claude

volumes:
  claude-auth:
```

- [ ] **Step 3: Create `docker-compose.override.yml.example`** (Quick Tunnel mode)

```yaml
# Renomeie pra docker-compose.override.yml pra ativar Quick Tunnel
# (sem precisar de Cloudflare Zero Trust account)
services:
  allos-tunnel:
    command: tunnel --no-autoupdate --url http://allos-webhook:3020
    environment:
      - TUNNEL_TOKEN=  # vazio = Quick Tunnel
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pip install pyyaml
python -m pytest tests/test_docker_compose.py -v
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.override.yml.example tests/test_docker_compose.py
git commit -m "feat(docker): compose com 3 services + healthchecks + Quick Tunnel override"
```

---

## Task 6 — `scripts/docker_setup.py` wizard

**Files:**
- Create: `scripts/docker_setup.py`
- Create: `.env.example`

- [ ] **Step 1: Create `.env.example`**

```bash
# ============================================================
# AllosAgent Docker Configuration
# ============================================================
# Preencha 1 dos perfis abaixo (LLM provider) + tunnel + sessão.
# scripts/docker_setup.py gera este arquivo automaticamente
# perguntando suas credenciais.

# === LLM Provider ===

# --- Perfil A: Anthropic oficial (assinatura Claude Code) ---
# Deixe TUDO vazio. Login feito 1x via:
#   docker exec -it allos-agent claude /login

# --- Perfil B: MiniMax ---
# ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
# ANTHROPIC_AUTH_TOKEN=sk-...
# ANTHROPIC_MODEL=MiniMax-M2.7
# ANTHROPIC_SMALL_FAST_MODEL=MiniMax-M2.7
# ANTHROPIC_DEFAULT_SONNET_MODEL=MiniMax-M2.7
# ANTHROPIC_DEFAULT_OPUS_MODEL=MiniMax-M2.7
# ANTHROPIC_DEFAULT_HAIKU_MODEL=MiniMax-M2.7
# API_TIMEOUT_MS=3000000

# --- Perfil C: Kimi K2 (Moonshot) ---
# ANTHROPIC_BASE_URL=https://api.moonshot.ai/anthropic
# ANTHROPIC_AUTH_TOKEN=sk-...
# ANTHROPIC_MODEL=kimi-k2-instruct
# ANTHROPIC_SMALL_FAST_MODEL=kimi-k2-instruct

# --- Perfil D: Z.ai GLM ---
# ANTHROPIC_BASE_URL=https://api.z.ai/anthropic
# ANTHROPIC_AUTH_TOKEN=...
# ANTHROPIC_MODEL=glm-4-plus

# === Cloudflare Tunnel ===
# Named tunnel: cole o token gerado no painel CF Zero Trust
# Vazio + use docker-compose.override.yml.example = Quick Tunnel (URL random)
TUNNEL_TOKEN=

# === Sessão ===
SESSION_NUM=1

# === Defaults Claude Code ===
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_EFFORT=medium
```

- [ ] **Step 2: Create `scripts/docker_setup.py`**

Estrutura mínima (interativo):

```python
#!/usr/bin/env python3
"""
Wizard interativo pra Trilha 3 (Docker).

Coleta:
  - Provider LLM (Anthropic/MiniMax/Kimi/Z.ai/Custom)
  - Credenciais megaAPI (instance, token, phone, lid)
  - Modo tunnel (Named c/ token, ou Quick)
  - Sessão (default 1)

Gera:
  - .env  (provider env vars + tunnel + sessão)
  - config.py  (delegando ao setup_config existente, mas pré-preenchido)
"""
import os
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROVIDERS = {
    "1": {
        "name": "Anthropic oficial (assinatura Claude Code)",
        "env": {},  # vazio, login interativo depois
        "post_setup": "Após `docker compose up -d`, faça login 1x:\n  docker exec -it allos-agent claude /login",
    },
    "2": {
        "name": "MiniMax",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
            "ANTHROPIC_MODEL": "MiniMax-M2.7",
            "ANTHROPIC_SMALL_FAST_MODEL": "MiniMax-M2.7",
            "API_TIMEOUT_MS": "3000000",
        },
        "needs_token": True,
    },
    "3": {
        "name": "Kimi K2 (Moonshot)",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.moonshot.ai/anthropic",
            "ANTHROPIC_MODEL": "kimi-k2-instruct",
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
        "name": "Custom (cole BASE_URL/MODEL/TOKEN manual)",
        "env": {},
        "custom": True,
    },
}


def _ask(prompt, default=None, secret=False):
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or (default or "")


def main():
    if not shutil.which("docker"):
        print("ERRO: docker não encontrado no PATH. Instale antes.")
        sys.exit(1)

    print("=" * 60)
    print("AllosAgent — Wizard Docker (Trilha 3)")
    print("=" * 60)
    print()

    # 1. Provider
    print("Escolha o provider LLM:")
    for k, v in PROVIDERS.items():
        print(f"  [{k}] {v['name']}")
    choice = _ask("Opção", default="1")
    if choice not in PROVIDERS:
        print("Inválido. Saindo.")
        sys.exit(1)
    provider = PROVIDERS[choice]
    env = dict(provider["env"])

    # Token / custom fields
    if provider.get("custom"):
        env["ANTHROPIC_BASE_URL"] = _ask("ANTHROPIC_BASE_URL")
        env["ANTHROPIC_MODEL"] = _ask("ANTHROPIC_MODEL")
        env["ANTHROPIC_AUTH_TOKEN"] = _ask("ANTHROPIC_AUTH_TOKEN", secret=True)
    elif provider.get("needs_token"):
        env["ANTHROPIC_AUTH_TOKEN"] = _ask("ANTHROPIC_AUTH_TOKEN (cole o token do provider)", secret=True)

    # 2. megaAPI: delega pra setup_config existente
    config_py = ROOT / "config.py"
    if not config_py.exists():
        print("\n--- megaAPI / config.py setup ---")
        print("Rodando setup_config existente...")
        os.system(f"{sys.executable} -m whatsapp_agent.setup_config")
    else:
        print(f"\nconfig.py já existe — pulando wizard megaAPI. Edite manualmente se precisar.")

    # 3. Tunnel
    print("\n--- Cloudflare Tunnel ---")
    print("  [1] Named Tunnel (URL fixa, precisa token CF Zero Trust)")
    print("  [2] Quick Tunnel (URL random a cada restart, zero config)")
    tunnel = _ask("Opção", default="2")
    if tunnel == "1":
        env["TUNNEL_TOKEN"] = _ask("TUNNEL_TOKEN (cole do painel CF Zero Trust)", secret=True)
    else:
        # Cria override
        override_src = ROOT / "docker-compose.override.yml.example"
        override_dst = ROOT / "docker-compose.override.yml"
        if override_src.exists() and not override_dst.exists():
            shutil.copy(override_src, override_dst)
            print(f"  Copiado: {override_dst.name} (Quick Tunnel ativo)")
        env["TUNNEL_TOKEN"] = ""

    # 4. Sessão
    env["SESSION_NUM"] = _ask("Número da sessão", default="1")
    env["CLAUDE_MODEL"] = _ask("Modelo Claude Code", default="claude-sonnet-4-6")
    env["CLAUDE_EFFORT"] = _ask("Effort", default="medium")

    # 5. Escreve .env
    env_path = ROOT / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# Gerado por scripts/docker_setup.py\n")
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    print(f"\nGerado: {env_path}")

    # 6. Próximos passos
    print()
    print("=" * 60)
    print("Setup concluído. Próximos passos:")
    print()
    print("  docker compose up -d --build")
    print("  docker compose logs -f")
    print()
    if provider.get("post_setup"):
        print(provider["post_setup"])
    print()
    print(f"Webhook URL pra megaAPI: <URL_DO_TUNNEL>/?session={env['SESSION_NUM']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: chmod + dry-run**

```bash
chmod +x scripts/docker_setup.py
python3 scripts/docker_setup.py < /dev/null  # dry-run validates parse
```

- [ ] **Step 4: Commit**

```bash
git add scripts/docker_setup.py .env.example
git commit -m "feat(docker): wizard interativo + .env.example multi-provider"
```

---

## Task 7 — `docs/DOCKER.md` runbook

**Files:**
- Create: `docs/DOCKER.md`

- [ ] **Step 1: Create runbook** (~300 linhas) com seções:

```markdown
# AllosAgent — Docker Operations (Trilha 3)

> Trilha 3 = caminho OSS one-command. Trilha 2 (systemd+tmux) continua válida via `docs/plans/2026-04-28-trilha-2-vps-deploy.md` + `DEPLOY_24_7_LINUX.md`.

## Quick Start

git clone, wizard, up. 3 comandos.

## Provedores LLM suportados

Tabela: nome / BASE_URL / model / link cadastro.

## Operação diária

| Ação | Comando |
|------|---------|
| Status | `docker compose ps` |
| Logs | `docker compose logs -f` |
| Restart agent | `docker compose restart allos-agent` |
| Login Anthropic 1x | `docker exec -it allos-agent claude /login` |
| Trocar modelo | edita `.env` + `docker compose restart allos-agent` |
| Healthcheck | `curl http://127.0.0.1:3020/healthz` |
| Acessar shell | `docker exec -it allos-agent bash` |

## Multi-sessão

Como rodar 2+ sessões: copia `allos-agent` no compose, muda `SESSION_NUM` + container_name + bind volumes session2.

## Backup

Volumes a preservar: `claude-auth`, `messages_session*.jsonl`, `processed_ids_session*.txt`, `config.py`, `.env`.

## Troubleshoot

- Container `allos-agent` em restart loop → `docker logs allos-agent` + verifica auth
- Webhook 502 → `docker compose ps` agent healthy?
- Quick Tunnel URL mudou → re-rodar `update_webhooks` (precisa adicionar via `docker exec`)

## Update

`git pull && docker compose pull && docker compose up -d --build`

## Rollback

`git checkout v1.x.x && docker compose up -d --build`

## Limitações conhecidas

- Auth Anthropic oficial expira → manual `claude /login` via `docker exec`
- Quick Tunnel URL muda em restart → use Named Tunnel pra produção
- Multi-sessão = N agents = N x ~200MB RAM
```

- [ ] **Step 2: Commit**

```bash
git add docs/DOCKER.md
git commit -m "docs(docker): runbook completo (setup, ops, multi-sessão, troubleshoot)"
```

---

## Task 8 — `.dockerignore` + `.gitignore`

**Files:**
- Create: `.dockerignore`
- Modify: `.gitignore`

- [ ] **Step 1: Create `.dockerignore`**

```
# VCS
.git
.gitignore

# Python
__pycache__
*.pyc
.venv
.pytest_cache

# OS
.DS_Store
Thumbs.db

# Secrets (DEVE ficar fora do build context)
config.py
.env
*.pem
.cloudflared/

# Local data
messages_session*.jsonl
processed_ids_session*.txt
raw_debug.jsonl
media/
.beads/
.claude/

# Docs/plans grandes
docs/plans/
landing/

# Build artifacts
dist/
build/
*.egg-info
```

- [ ] **Step 2: Append to `.gitignore`**

```
# Docker
.env
docker-compose.override.yml
cf-tunnel/
```

- [ ] **Step 3: Commit**

```bash
git add .dockerignore .gitignore
git commit -m "chore(docker): .dockerignore + .gitignore proteção secrets"
```

---

## Task 9 — README.md Quick Start (Docker)

**Files:**
- Modify: `README.md`

- [ ] Adicionar após seção Trilha 1 e antes de Trilha 2:

```markdown
## Quick Start (Docker — Trilha 3)

Stack containerizada one-command. Recomendado pra leigos / OSS users.

```bash
git clone https://github.com/giovani-junior-dev/Allos.git
cd Allos
python3 scripts/docker_setup.py    # wizard interativo
docker compose up -d --build
docker compose logs -f
```

Detalhes: [docs/DOCKER.md](./docs/DOCKER.md)

Provedores LLM suportados: Anthropic oficial, MiniMax, Kimi K2, Z.ai GLM, custom.

> Prefere systemd nativo? Veja **Trilha 2 (VPS systemd+tmux)** mais abaixo + tutorial passo-a-passo em `DEPLOY_24_7_LINUX.md`.
```

- [ ] Commit:

```bash
git add README.md
git commit -m "docs(readme): adicionar Quick Start Trilha 3 Docker"
```

---

## Task 10 — Validação E2E em VPS limpa

**Files:** none (validation only)

- [ ] **Pré-requisito:** VPS Ubuntu 22.04+ ou Debian 12 com Docker + compose plugin instalados

- [ ] **Step 1: Clone + wizard**

```bash
git clone https://github.com/giovani-junior-dev/Allos.git
cd Allos
python3 scripts/docker_setup.py
# escolhe MiniMax + cola token + megaAPI creds + Quick Tunnel
```

- [ ] **Step 2: Up**

```bash
docker compose up -d --build
sleep 120
docker compose ps
```

Esperado: 3 services `Up (healthy)` ou `Up (running)`.

- [ ] **Step 3: Healthcheck**

```bash
curl http://127.0.0.1:3020/healthz   # {"status":"ok",...}
docker logs allos-tunnel | grep -i "registered\|connected\|trycloudflare"
```

- [ ] **Step 4: WhatsApp ping**

Cola URL do tunnel em `<url>/?session=1` no painel megaAPI. Manda msg pro próprio número.

Esperado: resposta com `*Claude Code*` em <30s.

- [ ] **Step 5: Crash test**

```bash
docker kill allos-agent
sleep 20
docker ps | grep allos-agent   # Up novamente
```

Manda nova msg → responde.

- [ ] **Step 6: Reboot test**

```bash
sudo reboot
# após boot
docker ps                      # 3 containers Up sozinhos
```

Manda msg → responde sem touch humano.

- [ ] **Step 7: Provider switch test**

```bash
nano .env                      # troca ANTHROPIC_MODEL ou BASE_URL
docker compose restart allos-agent
sleep 30
docker logs allos-agent | tail -20
```

Manda msg → responde com novo modelo.

---

## Task 11 — Tag release

**Files:** none

- [ ] **Step 1: Atualizar README.md** com badge Trilha 3 done

- [ ] **Step 2: Tag**

```bash
git tag -a v1.2.0-trilha3 -m "Trilha 3: Docker OSS distribution (compose + wizard + multi-provider)"
git push origin trilha-1-multimodal
git push origin v1.2.0-trilha3
```

- [ ] **Step 3: bd close**

```bash
bd close teste-iac --reason "Trilha 3 done. v1.2.0-trilha3 tagged."
```

---

## Done Criteria

- [ ] `docker compose up -d --build` em VPS Ubuntu fresh: 3 services `healthy` em <2min
- [ ] Wizard cobre 5 providers (Anthropic/MiniMax/Kimi/Z.ai/Custom)
- [ ] Reboot VPS recovery automático testado
- [ ] `docker kill allos-agent` recovery testado
- [ ] Provider switch via `.env` testado
- [ ] `docs/DOCKER.md` cobre setup, troubleshoot, switch provider, multi-sessão
- [ ] README.md tem Quick Start (Docker) + cross-link Trilha 2 preservado
- [ ] **Trilha 2 docs intocados** (`docs/plans/2026-04-28-trilha-2-vps-deploy.md` + `DEPLOY_24_7_LINUX.md`)
- [ ] tag `v1.2.0-trilha3` criada e pushada
- [ ] bd ticket `teste-iac` fechado

---

## Limitações honestas

| Cenário | Recovery automático? |
|---------|---------------------|
| VPS reboot | ✅ ~95% — Docker daemon sobe + `unless-stopped` |
| `docker kill allos-agent` | ✅ ~95% — restart auto, `--continue` retoma |
| OOM kill webhook | ✅ ~99% — stateless |
| Cloudflared reconexão | ✅ ~99% — imagem oficial robusta |
| Claude CLI crash interno | ✅ ~85% — bash loop reinicia em 5s |
| Auth Anthropic oficial expira | 🔴 manual — precisa `docker exec -it allos-agent claude /login` |
| Token BYO provider expira | ⚠️ depende provider — edita `.env`, restart |
| Anthropic CLI muda UI | ✅ baixo risco — usa flags estáveis (`--continue`, `--dangerously-skip-permissions`) |

**Constraint do user assumido:** "Reboot OK, crash raro tudo bem" — Docker viável.

**Trade-off vs Trilha 2:**
- **Trilha 2** = controle fino, journalctl observabilidade, `tmux attach` direto, performance 1:1 host
- **Trilha 3** = isolamento, portabilidade, 1-comando, ideal pra OSS distribution, ~200MB extra RAM

Usuário escolhe — não há substituição forçada.

---

## Refs

- Trilha 2 (preservada): `docs/plans/2026-04-28-trilha-2-vps-deploy.md`
- Tutorial real systemd+tmux: `C:\Users\GEOVANE\Desktop\DEPLOY_24_7_LINUX.md`
- bd ticket: `teste-iac`
- Allos repo: https://github.com/giovani-junior-dev/Allos
- Claude Code CLI: https://docs.claude.com/claude-code
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
