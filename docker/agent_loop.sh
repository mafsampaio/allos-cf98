#!/usr/bin/env bash
# ============================================================
# agent_loop.sh
# ----------------------------------------------------------
# Mantem Claude Code rodando em loop dentro do container.
# Adaptado de DEPLOY_24_7_LINUX.md / claude_monitor_loop.sh.
#
# Primeira run: planta prompt fresh (CLAUDE_PROMPT.md).
# Runs subsequentes: --continue retoma sessao.
# Crash do claude -> restart 5s.
# Heartbeat /tmp/agent-alive pra healthcheck Docker.
# ============================================================
set -u

: "${SESSION_NUM:=1}"
: "${CLAUDE_MODEL:=}"
: "${CLAUDE_EFFORT:=medium}"

cd /app

PROMPT="Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: ${SESSION_NUM}"
FIRST_RUN_FLAG="/app/.claude_started_session${SESSION_NUM}"

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
    echo "[agent_loop] WARN: nem ANTHROPIC_AUTH_TOKEN nem ~/.claude/ login detectados."
    echo "[agent_loop] Esperando login manual via:"
    echo "[agent_loop]   docker exec -it allos-agent claude /login"
fi

# First run plants prompt
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
