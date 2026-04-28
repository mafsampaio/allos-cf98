# Trilha 2 — Deploy 24/7 em VPS

> Status: **NAO INICIADA** (planejamento). Trilha 1 (multimodal + multi-sessao)
> esta concluida e validada (tag `v1.0-trilha1`).

## Objetivo

Mover o agente de localhost (Windows do dev rodando webhook + ngrok + Claude
Code) para um VPS Linux operando 24/7, sem depender da maquina pessoal estar
ligada ou em sessao Claude Code.

---

## Escopo

### 1. Cloudflare Tunnel substitui ngrok

| Aspecto | ngrok (Trilha 1) | Cloudflare Tunnel (Trilha 2) |
|---------|------------------|-----------------------------|
| URL publica | Aleatoria, troca a cada restart | Subdominio fixo |
| TLS | Automatico | Automatico |
| Limite de tempo | Free tier desliga | Sem limite |
| Custo | Free / pago | Free com domain CF |
| Setup | `ngrok http 3020` | `cloudflared tunnel create ...` |
| Exposicao de porta | Tunel | Tunel reverso (sem abrir porta no VPS) |

Pre-requisito: conta Cloudflare + dominio (ou usar `*.trycloudflare.com`
para protótipos).

### 2. Process supervision via systemd

Duas units:

#### `webhook.service`
```
[Unit]
Description=WhatsApp Claude Agent webhook server
After=network-online.target

[Service]
Type=simple
User=whatsapp
WorkingDirectory=/opt/whatsapp-claude-agent
ExecStart=/usr/bin/python3 webhook_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### `cloudflared.service`
Provido pelo pacote `cloudflared` ou customizado:
```
[Service]
ExecStart=/usr/bin/cloudflared tunnel run <TUNNEL_ID>
Restart=always
```

Logs unificados em `journalctl -u webhook -u cloudflared -f`.

### 3. Script `deploy_vps.sh`

Automatiza setup em VPS Ubuntu/Debian limpo:
1. `apt update && apt install -y python3 python3-pip curl`
2. Baixa e instala `cloudflared`
3. `git clone` do projeto em `/opt/whatsapp-claude-agent`
4. Roda `setup_config.py` interativo
5. Cria usuario sistema `whatsapp`
6. Copia `systemd/webhook.service` e `systemd/cloudflared.service` para `/etc/systemd/system/`
7. `systemctl enable --now webhook cloudflared`
8. Registra tunnel CF e imprime URL final pra colar no painel megaAPI

### 4. Estrutura sugerida do repo

```
teste/
  install/
    install.ps1            # localhost Windows (existente, move pra ca)
    install.sh             # localhost Linux/macOS (existente, move pra ca)
    deploy_vps.sh          # NOVO: bootstrap VPS Linux
  systemd/
    webhook.service
    cloudflared.service
```

(Manter compat: simbolicos ou shims na raiz pra nao quebrar README atual.)

---

## Trade-off chave a resolver

**Claude Code CLI normalmente roda em sessao interativa.** Como manter o
Monitor 24/7 num VPS sem tty?

### Opcoes em discussao

| Opcao | Pros | Contras |
|-------|------|---------|
| **A. tmux/screen persistente** | Simples; aproveita binario Claude Code intacto | Requer `tmux attach` manual pra debugar; sessao morre se host reinicia sem reconect; auth Claude Code interativa |
| **B. systemd unit do Claude Code com auth headless** | Idiomatico Linux; auto-restart | Claude Code CLI nao foi desenhado pra headless puro; precisa investigar se aceita stdin redirecionado e auth nao-interativa |
| **C. Arquitetura diferente (worker queue)** | Desacopla Claude Code do runtime; webhook empilha em fila Redis/SQLite, worker lento puxa quando ha sessao Claude Code disponivel | Mensagens nao tem resposta em tempo real se nao houver Claude Code online; perde a graca da POC |
| **D. Trocar cerebro pra Anthropic API direto em modo VPS** | Headless de verdade; resposta instantanea | Custo de LLM por mensagem; perde o ponto principal da POC ("zero LLM cost"); mas continua sendo opcional — Trilha 1 mode permanece pra dev local |

**Decisao pendente.** Investigar viabilidade de A primeiro (custo zero,
risco menor); D fica como fallback se A/B inviaveis.

---

## Nao-objetivos da Trilha 2

- TTS (audio sintetizado de saida) — cortado do escopo total.
- Processamento de video.
- Multi-tenancy (cada deploy = 1 dev/aluno).
- Migracao do mode local — Trilha 1 (Windows + ngrok + Claude Code) continua
  100% suportado pra desenvolvimento.

---

## Verificacao de sucesso (Trilha 2)

- [ ] `deploy_vps.sh` em VPS limpo Ubuntu 22.04 termina sem erro.
- [ ] `systemctl status webhook` = active (running).
- [ ] `systemctl status cloudflared` = active (running).
- [ ] URL CF Tunnel responde a `curl https://agent.exemplo.com/healthz` -> 200.
- [ ] Mensagem WhatsApp chega no JSONL do VPS sem ngrok envolvido.
- [ ] Resposta volta em < 10s.
- [ ] Reboot do VPS: tudo sobe automatico, sem acao manual.
- [ ] 7 dias uptime ininterrupto.

---

## Refs

- Trilha 1 (concluida): `../PROJETO.md`, branch `trilha-1-multimodal`, tag `v1.0-trilha1`
- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- systemd unit reference: `man systemd.service`
