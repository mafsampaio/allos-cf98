# AllosAgent — Docker Operations (Trilha 3)

> Trilha 3 = caminho OSS one-command. Trilha 2 (systemd+tmux nativo) continua valida — ver `docs/plans/2026-04-28-trilha-2-vps-deploy.md` + tutorial real `DEPLOY_24_7_LINUX.md`.

---

## Quick Start

```bash
git clone https://github.com/giovani-junior-dev/Allos.git
cd Allos
python3 scripts/docker_setup.py    # wizard interativo
docker compose up -d --build
docker compose logs -f
```

3 comandos. O wizard pergunta:
1. Provider LLM (Anthropic/MiniMax/Kimi/Z.ai/Custom)
2. Credenciais megaAPI (delega pro `whatsapp_agent.setup_config`)
3. Tunnel (Named c/ token, ou Quick)
4. Sessao + modelo padrao

---

## Pre-requisitos

- Docker Engine 24+ ou Docker Desktop com Compose plugin
- VPS Linux (Ubuntu 22.04+, Debian 12+) **OU** local
- Conta megaAPI com instance + token + numero conectado
- 1 dos seguintes:
  - Conta Anthropic com Claude Code (login manual 1x)
  - Token de provider Anthropic-compat (MiniMax, Kimi, Z.ai, etc)
- (Opcional) Conta Cloudflare Zero Trust pra Named Tunnel com URL fixa

---

## Provedores LLM suportados

| Provider | BASE_URL | Model exemplo | Cadastro |
|----------|----------|---------------|----------|
| Anthropic oficial | (vazio, login `claude /login`) | `claude-sonnet-4-6` | https://console.anthropic.com |
| MiniMax | `https://api.minimax.io/anthropic` | `MiniMax-M2.7` | https://api.minimax.io |
| Kimi K2 (Moonshot) | `https://api.moonshot.ai/anthropic` | `kimi-k2-instruct` | https://platform.moonshot.ai |
| Z.ai GLM | `https://api.z.ai/anthropic` | `glm-4-plus` | https://z.ai |
| Custom | qualquer endpoint Anthropic-compat | livre | — |

Pra trocar provider depois de instalado: edite `.env`, depois `docker compose restart allos-agent`.

---

## Tunnel: Named vs Quick

| Modo | URL | Requer | Bom pra |
|------|-----|--------|---------|
| **Named Tunnel** | `https://seu-sub.dominio.com` (fixa) | Cloudflare Zero Trust + dominio | producao 24/7 |
| **Quick Tunnel** | `https://random.trycloudflare.com` (muda em restart) | nada | testes / dev |

Quick Tunnel: o wizard copia `docker-compose.override.yml.example` -> `docker-compose.override.yml` automaticamente.

Named Tunnel: cole o token gerado no painel CF Zero Trust no campo `TUNNEL_TOKEN`. Crie tunnel via:
1. Cloudflare dashboard -> Zero Trust -> Networks -> Tunnels -> Create
2. Connector: copie `--token <XXX>` mostrado
3. Configure public hostname apontando pra `http://allos-webhook:3020`

---

## Operacao diaria

| Acao | Comando |
|------|---------|
| Status agregado | `docker compose ps` |
| Logs unificados | `docker compose logs -f` |
| Logs por service | `docker compose logs -f allos-agent` |
| Restart agent | `docker compose restart allos-agent` |
| Restart tudo | `docker compose restart` |
| Stop | `docker compose stop` |
| Start | `docker compose start` |
| Down (remove containers) | `docker compose down` |
| Login Anthropic 1x | `docker exec -it allos-agent claude /login` |
| Acompanhar Claude vivo | `docker exec -it allos-agent bash -c 'tail -f /tmp/claude.log 2>/dev/null \|\| docker compose logs -f allos-agent'` |
| Trocar modelo | edite `.env` -> `docker compose restart allos-agent` |
| Healthcheck local | `curl http://127.0.0.1:3020/healthz` |
| Healthcheck publico | `curl https://seu-tunnel/healthz` |
| Shell no agent | `docker exec -it allos-agent bash` |
| Ver mensagens | `tail -f messages_session1.jsonl` |
| Doctor diagnostico | `docker exec allos-webhook python -m whatsapp_agent.doctor` |

---

## Trocar provider sem rebuild

```bash
nano .env
# muda:
#   ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
#   ANTHROPIC_AUTH_TOKEN=sk-novo-token
#   ANTHROPIC_MODEL=MiniMax-M2.7

docker compose restart allos-agent
docker compose logs -f allos-agent
```

Loop bash dentro do container ja respeita as novas envs no proximo `claude --continue`.

---

## Multi-sessao

Cada sessao = 1 numero WhatsApp adicional = 1 container `allos-agent` extra.

Edite `docker-compose.yml` adicionando segundo agent:

```yaml
  allos-agent-2:
    extends: allos-agent
    container_name: allos-agent-2
    environment:
      - SESSION_NUM=2
      # demais envs herdadas via .env
    volumes:
      - ./config.py:/app/config.py:ro
      - ./messages_session2.jsonl:/app/messages_session2.jsonl
      - ./processed_ids_session2.txt:/app/processed_ids_session2.txt
      - ./media:/app/media
      - ./CLAUDE_PROMPT.md:/app/CLAUDE_PROMPT.md:ro
      - claude-auth-2:/home/allos/.claude

volumes:
  claude-auth:
  claude-auth-2:
```

Webhook ja multiplexa via `?session=N` na URL — basta cadastrar 2 endpoints na megaAPI:
- `https://seu-tunnel/?session=1`
- `https://seu-tunnel/?session=2`

Cada sessao consome ~200MB RAM. Em VPS 1GB cuide.

---

## Backup

Itens criticos:

| Caminho | Conteudo | Frequencia |
|---------|----------|------------|
| `./config.py` | Tokens megaAPI + OpenAI key | Toda mudanca |
| `./.env` | Provider creds + tunnel token | Toda mudanca |
| Volume `claude-auth` | Auth Anthropic OAuth (se oficial) | 1x apos login |
| `./messages_session*.jsonl` | Historico mensagens | Diario |
| `./processed_ids_session*.txt` | IDs ja respondidos | Diario |

Script:

```bash
docker run --rm \
    -v "$(pwd)":/src:ro \
    -v allos_claude-auth:/auth:ro \
    -v "$(pwd)/backup":/backup \
    alpine tar czf /backup/allos-$(date +%Y%m%d).tar.gz \
        /src/config.py /src/.env \
        /src/messages_session*.jsonl \
        /src/processed_ids_session*.txt \
        /auth
```

---

## Update

```bash
git pull
docker compose pull         # atualiza cloudflared image
docker compose up -d --build
docker compose logs -f
```

Validacao pos-update:
```bash
curl http://127.0.0.1:3020/healthz
docker compose ps   # tudo healthy
```

---

## Rollback

```bash
git checkout v1.x.x          # tag estavel anterior
docker compose down
docker compose up -d --build
```

---

## Troubleshoot

### `allos-agent` em restart loop

```bash
docker logs allos-agent --tail 50
```

Causas comuns:
- **`[agent_loop] WARN: nem ANTHROPIC_AUTH_TOKEN nem ~/.claude/...`** → preencha `.env` ou rode `docker exec -it allos-agent claude /login`.
- **`Error: Unable to authenticate`** → token expirado/invalido. Edite `.env`, restart.
- **`claude: not found`** → rebuild a imagem (`docker compose build --no-cache allos-agent`).

### Webhook `unhealthy`

```bash
docker logs allos-webhook
docker exec allos-webhook curl -f http://localhost:3020/healthz
```

Se 502/erro: provavelmente `config.py` ausente ou malformado.

### Mensagens chegam mas Claude nao responde

```bash
# 1. JSONL recebendo?
tail -f messages_session1.jsonl

# 2. Agent vivo?
docker compose ps

# 3. Heartbeat recente?
docker exec allos-agent stat /tmp/agent-alive

# 4. Entrar e olhar
docker exec -it allos-agent bash
ps -ef | grep claude
```

### Quick Tunnel URL mudou

Quick Tunnel imprime URL nova nos logs do `allos-tunnel` a cada restart. Atualize manualmente na megaAPI ou:

```bash
# Le URL atual dos logs e atualiza webhooks
NEW_URL=$(docker logs allos-tunnel 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
echo "Cole na megaAPI: ${NEW_URL}/?session=1"
```

Producao = use Named Tunnel.

### Auth Anthropic oficial expirou

```bash
docker exec -it allos-agent claude /login
# segue fluxo OAuth no terminal
docker compose restart allos-agent
```

### `docker compose` reclama version warning

Compose v2+ ignora `version:` field. Plano atual ja omite — se ver warning, atualize Compose.

---

## Limitacoes conhecidas

- **`--dangerously-skip-permissions`**: claude tem acesso shell irrestrito. Mitigue com `CMD_TOKEN` em `config.py` se quiser auth extra por mensagem.
- **Auth Anthropic oficial expira**: precisa `docker exec ... claude /login` manual.
- **Quick Tunnel URL muda**: producao = Named Tunnel.
- **Multi-sessao**: 1 agent container por sessao = N x ~200MB RAM.
- **Crash da auth no provider BYO**: cada provider tem politica propria de TTL token.
- **Volume bind-mount de JSONL**: webhook + agent acessam mesmo arquivo. No Linux funciona bem; no Windows use WSL2 backend.

---

## Refs

- Trilha 2 (systemd+tmux): `docs/plans/2026-04-28-trilha-2-vps-deploy.md`
- Tutorial real Trilha 2: `DEPLOY_24_7_LINUX.md` (na area de trabalho do mantenedor)
- Plano Trilha 3: `docs/plans/2026-05-07-trilha-3-docker-oss.md`
- Allos repo: https://github.com/giovani-junior-dev/Allos
- Claude Code CLI: https://docs.claude.com/claude-code
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
