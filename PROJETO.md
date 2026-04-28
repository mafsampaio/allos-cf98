# WhatsApp Agent POC — Claude Code as Brain

> Agente WhatsApp multimodal que usa a sessao Claude Code CLI ativa como LLM,
> sem API key extra. Multi-sessao, webhook unico, dedup persistente, recebimento
> de texto/imagem/audio, envio de texto/imagem.

---

## 1. Conceito

Bots WhatsApp convencionais chamam uma API LLM (OpenAI, Anthropic, etc.) a cada
mensagem recebida. Esta POC faz diferente: ela injeta as mensagens recebidas
diretamente na ferramenta Monitor do Claude Code, e a propria sessao Claude
Code interpreta a mensagem e decide a resposta. As respostas voltam ao
WhatsApp via um pequeno helper Python.

Resultado: agente WhatsApp 100% funcional, com custo zero de LLM enquanto o
operador esta numa sessao Claude Code.

---

## 2. Arquitetura

```
WhatsApp -> megaAPI -> ngrok -> webhook_server.py (porta 3020)
                                       |
                                       v
                       (decripta media via downloadMediaMessage)
                                       |
                                       v
                              messages_sessionN.jsonl
                                       |  (linhas com media_path quando aplicavel)
                                       v
                              monitor.py N (Monitor dentro do Claude Code)
                                       |
                                       v
                       Claude Code:
                         - texto       -> processa direto
                         - imagem      -> Read no media_path (visao nativa)
                         - audio       -> python transcribe.py <path> (Whisper)
                         - /comando    -> executa skill / slash command
                         - video       -> recusa
                                       |
                                       v
                              send_message.py
                                (--type text  -> /text endpoint)
                                (--type image -> /mediaBase64 endpoint)
                                       |
                                       v
                              megaAPI -> WhatsApp
```

Um unico processo `webhook_server.py` atende todas as sessoes. Cada instancia
megaAPI configura o mesmo URL ngrok com `?session=N` distinto.

---

## 3. Arquivos

```
teste/
  webhook_server.py        # HTTP :3020, multi-sessao, baixa media, escreve JSONL
  send_message.py          # Sender texto + imagem (curl + megaAPI)
  monitor.py               # Monitor target (rodado dentro do Claude Code)
  media_handler.py         # Download decriptado + sanitize de path
  transcribe.py            # OpenAI Whisper wrapper (opcional)
  add_session.py           # Wizard adiciona instancia ao config preservando existentes
  setup_config.py          # Wizard inicial gera config.py (chamado pelo install)
  discover_lid.py          # Auto-descobre LID apos primeira mensagem
  doctor.py                # Healthcheck (env, config, runtime, megaAPI, OpenAI)
  config.py                # Secrets locais (NAO commitar)
  config.example.py        # Template publico
  install.ps1 / install.sh # Bootstrap (chama setup_config.py)
  start.ps1 / start.sh     # Sobe webhook + ngrok em background
  stop.ps1 / stop.sh       # Para webhook + ngrok
  README.md                # Quickstart
  SETUP.md                 # Passo a passo do zero
  PROJETO.md               # Este arquivo
  CLAUDE_PROMPT.md         # Prompt pra colar no Claude Code
  docs/
    TRILHA_2_ROADMAP.md    # Plano da proxima fase (deploy 24/7)
  tests/                   # 26 testes pytest
  media/sessionN/          # Arquivos decriptados (jpg/ogg/mp4)
  messages_sessionN.jsonl  # Append-only message log por sessao
  processed_ids_sessionN.txt
  raw_debug.jsonl          # Dump cru de payloads pra debugging
```

### `webhook_server.py`
- Escuta em `0.0.0.0:3020`.
- Le `?session=N` da query string; default `1`.
- Faz parse do payload **flat** (sem wrapper `data`).
- Ignora: `@g.us` (grupos), `@newsletter`.
- Para midia, chama `media_handler.download(...)` que usa o endpoint
  `POST /rest/instance/downloadMediaMessage/{instance}` da megaAPI. Esse
  endpoint retorna `data:<mime>;base64,<bytes>` (data URI), que e decodificado
  e gravado em `media/sessionN/<msg_id>.<ext>`.
- Whitelist: comparacao **exata** de telefone por sessao
  (`SESSIONS[session]["phone"]`).
- Aceita self-chat (`fromMe=true` do proprio numero).
- Anexa em `messages_sessionN.jsonl` com campos `media_type` e `media_path`
  quando midia presente. `text` recebe a caption ou placeholder
  (`[image]`, `[audio]`, `[midia]`) quando ausente.
- Sempre escreve o evento cru em `raw_debug.jsonl`.

### `send_message.py`
- Usa `subprocess.run(["curl", ...])` — `urllib` e bloqueado por Cloudflare.
- Texto: `POST {MEGA_HOST}/rest/sendMessage/{instance}/text`
  Body: `{"messageData":{"to":"...","text":"...","linkPreview":false}}`.
- Imagem: `POST {MEGA_HOST}/rest/sendMessage/{instance}/mediaBase64`
  Body: `{"messageData":{"to":"...","base64":"<base64>","fileName":"...",
  "type":"image","caption":"...","gifPlayback":false,"mimeType":"image/jpeg",
  "viewOnce":false}}`.
- CLI: `python send_message.py [--type text|image] <to> <conteudo> [caption] <session>`.
- Cap de 16MB no envio de imagem (mediaBase64 estoura em arquivos maiores).
- Auto-anexa assinatura `*Claude Code*` em texto.
- Forca `encoding="utf-8"` (cp1252 do Windows quebra com emoji).

### `monitor.py`
- Le `messages_sessionN.jsonl` desde o inicio (NAO `seek(0,2)` — perderia
  primeira mensagem caso o arquivo seja criado ja com ela dentro).
- Pula: IDs vazios, IDs ja processados, linhas com assinatura `*Claude Code*`.
- Persiste IDs em `processed_ids_sessionN.txt` para sobreviver a restart.
- Cada linha emitida = uma notificacao Monitor para o Claude Code.

### `media_handler.py`
- `download(session, message_id, instance, token)` -> `{path, type}` ou `None`.
- POST para `downloadMediaMessage/{instance}` enviando o payload da mensagem.
- Decodifica data URI base64; protege `binascii.Error` em base64 corrompido.
- Sanitiza `session` (rejeita `..`, separadores) antes de compor o path.
- Detecta extensao via mime type (image/jpeg -> .jpg, audio/ogg -> .ogg, etc.).

### `transcribe.py`
- CLI: `python transcribe.py <path>`.
- Le `OPENAI_API_KEY` de `config.py`. Se ausente: imprime
  `[audio - transcricao desativada - configure OPENAI_API_KEY em config.py]`.
- Usa endpoint `https://api.openai.com/v1/audio/transcriptions` (Whisper).
- Distingue erro de rede (mensagem `[audio - falha de rede...]`) de erro de
  API (status code + body).

### `add_session.py`
- Wizard interativo. Le `config.py` atual, atribui o **proximo ID livre**
  (`max(int(k) for k in SESSIONS) + 1`), pergunta instance/token/phone, e
  reescreve `config.py` preservando sessoes existentes e ordem do dict.

### `setup_config.py`
- Chamado pelo install. Gera `config.py` da primeira vez:
  CMD_TOKEN, SIGNATURE, MEGA_HOST, OPENAI_API_KEY (opcional), uma SESSAO 1.

### `discover_lid.py`
- Le ultimas linhas de `raw_debug.jsonl`, encontra eventos da sessao N,
  extrai LID do payload e atualiza `config.py` automaticamente.

### `doctor.py`
- Verifica env (Python, curl, ngrok no PATH).
- Valida `config.py` (sintaxe + campos obrigatorios).
- Confere runtime: porta 3020 ouvindo, URL publica do ngrok respondendo.
- Testa cada sessao megaAPI via GET de status na instancia.
- Se `OPENAI_API_KEY` configurada, testa um GET na API OpenAI.
- Verifica existencia de `messages_sessionN.jsonl`, `media/sessionN/`.

### `config.py`
- `MEGA_HOST = "https://apibusiness1.megaapi.com.br"`
- `CMD_TOKEN` — legado, hoje opcional. Whitelist de telefone basta.
- `SIGNATURE = "*Claude Code*"` — auto-anexada em todo outbound texto, usada
  para quebrar loop de resposta no inbound.
- `OPENAI_API_KEY` — opcional, habilita transcricao de audio.
- `SESSIONS` — dict `"1"`, `"2"`, ... mapeando para
  `{instance, token, phone, lid}`.

---

## 4. Sessoes

| Sessao | Telefone | Instancia megaAPI | LID |
|--------|----------|-------------------|-----|
| 1 | 556195562618 | megabusiness-desenvolivimentoProjeto2 | 22540172955723 |
| 2 | 556182796341 | megabusiness-desenvolivimentoProjeto3 | 90997556006924 |

Adicionar nova: `python add_session.py` (wizard); depois configurar webhook
megaAPI da nova instancia com `?session=N` correspondente.

---

## 5. Setup & Execucao

### Pre-requisitos
- Python 3.8+ no PATH
- `curl` no PATH
- `ngrok` (ou tunel publico equivalente)
- Conta megaAPI com instancia configurada
- (opcional) `OPENAI_API_KEY` para transcricao de audio

### Boot — Opcao A (script automatico)
```bash
# Windows
.\start.ps1
# Linux / macOS
./start.sh
```
Sobe webhook + ngrok em background, imprime URL publica.

### Boot — Opcao B (manual, 2 terminais)
```bash
# Terminal 1
python webhook_server.py
# Terminal 2
ngrok http 3020
```

### Boot — Opcao C (VPS 24/7)
Em desenvolvimento na **Trilha 2**. Ver `docs/TRILHA_2_ROADMAP.md`.

### Verificacao
```bash
python doctor.py
```

### Configurar webhook na megaAPI
```
https://<ngrok-id>.ngrok-free.app/?session=<N>
```

### Loop por sessao dentro do Claude Code
- Cole `CLAUDE_PROMPT.md` na primeira mensagem.
- Pre-flight executa `doctor.py` e inicia `python monitor.py 1` (PERSISTENTE).
- Multi-sessao: uma janela Claude Code por sessao, um Monitor por sessao.

---

## 6. Protocolo de Mensagens

### Inbound

| Conteudo | Tratamento |
|----------|-----------|
| Texto puro | Claude responde conversacionalmente |
| Texto comecando com `/` | Claude executa como slash command (skill, comando) |
| Imagem com caption | Claude le imagem via Read, usa caption como pergunta |
| Imagem sem caption | Caption fica `[image]`, Claude le imagem e descreve |
| Audio | `transcribe.py` -> texto -> Claude responde |
| Video | "Videos nao sao suportados ainda" |

### Outbound

| Tipo | Comando |
|------|---------|
| Texto | `python send_message.py <to> "<msg>" <session>` |
| Imagem | `python send_message.py --type image <to> <path> "<caption>" <session>` |

Toda resposta de texto recebe a assinatura `*Claude Code*` automaticamente.
Isso quebra o loop de eco do webhook.

---

## 7. Bugs Corrigidos

| # | Sintoma | Causa raiz | Correcao |
|---|---------|------------|----------|
| 1 | Parse retornava vazio | Esperava wrapper `data` | Parse a partir da raiz |
| 2 | `403 Forbidden` no envio | Cloudflare bloqueia UA do urllib | Subprocess `curl` |
| 3 | `UnicodeDecodeError` (emoji) | Windows cp1252 default | `encoding="utf-8"` em todo lugar |
| 4 | Primeira mensagem nao emitida | `seek(0,2)` pulava linha pre-existente | Ler do inicio + dedup persistente |
| 5 | Whitelist aceitava remetente errado | Substring + fallback LID-ou-phone | Comparacao exata de telefone |
| 6 | Bot respondia a si mesmo | Webhook capturava eco do outbound | Filtrar assinatura `*Claude Code*` |
| 7 | `binascii.Error` em base64 corrompido | Nao tratava erro de decode | Guard explicito em `media_handler.download` |
| 8 | Path traversal via `?session=` | Concatenacao crua de `session` no path | Sanitize: rejeita `..`, separadores |
| 9 | Audio chegava como `[unknown]` | Fallback errado quando media_type ausente | Reverter para `[midia]` + assercao em teste |
| 10 | Tests vazavam imports entre runs | `sys.path` modificado em fixture | `monkeypatch.syspath_prepend` + evict de `setup_config` |
| 11 | `send_image` enviava arquivos > 16MB e estourava | Sem cap | Guard de tamanho com mensagem amigavel |
| 12 | Tests do `setup_config` retornavam URL OpenAI vazia | Modulo cacheado entre testes | Evict do modulo entre testes |
| 13 | Setup nao perguntava OpenAI key | Wizard antigo | Prompt opcional com URL `platform.openai.com/api-keys` |

---

## 8. Quirks da megaAPI

- Host correto: `https://apibusiness1.megaapi.com.br` (NAO `api.megaapi.com.br`).
- Inbound payload e flat (sem wrapper `data`).
- `@lid` na raiz do payload e o LID da **instancia**, nao do remetente.
- `fromMe: true` self-chat realmente chega — opt-in ou filtro explicito.
- Cloudflare na frente — `curl` funciona, `urllib` nao.
- Outbound texto: `{"messageData":{"to":"<phone>","text":"...","linkPreview":false}}`.
- Outbound imagem: endpoint **separado** `/mediaBase64` com payload contendo
  `base64`, `fileName`, `type`, `caption`, `gifPlayback`, `mimeType`,
  `viewOnce`. NAO usar `mediaUrl` — alguns fluxos megaAPI rejeitam.
- Midia inbound chega criptografada (`.enc`). Para decriptar usar
  `POST /rest/instance/downloadMediaMessage/{instance}` enviando o payload
  da mensagem completo. Resposta vem como **data URI** base64
  (`data:<mime>;base64,<bytes>`).
- Sem dedup automatica. O mesmo `id` pode reaparecer em reconexoes —
  persistir IDs processados.

Referencia completa:
`~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/reference_megaapi.md`.

---

## 9. Estado atual

- Branch: `trilha-1-multimodal`
- Tag: `v1.0-trilha1`
- Sessoes 1 e 2 rodando em producao localhost.
- 26 testes pytest passando (TDD-driven).
- Multimodal completo no recebimento (texto, imagem, audio); envio (texto,
  imagem). TTS / video gerar fora de escopo.

### Tests E2E reais (Trilha 1)

| # | Teste | Status |
|---|-------|--------|
| 1 | Texto puro -> resposta texto | OK |
| 2 | `/caveman-help` -> skill executada -> card no WhatsApp | OK |
| 3 | Imagem ficha "REPE KIDS 2026" + caption -> analise detalhada | OK |
| 4 | Imagem livro "Cafe com Deus Pai" sem caption -> descrita | OK |
| 5a | Audio com `OPENAI_API_KEY` ausente -> marker apropriado | OK |
| 5b | Audio com Whisper -> transcricao correta | OK |
| 6 | Video -> "Videos nao sao suportados ainda" | OK |

---

## 10. Roadmap

### Trilha 1 — CONCLUIDA (2026-04-28)
Multi-sessao dinamica, recebimento multimodal, envio multimodal (sem TTS),
slash commands, boot checklist explicito, healthcheck, 26 unit tests +
suite E2E real. Tag `v1.0-trilha1` em `trilha-1-multimodal`.

### Trilha 2 — PROXIMA (nao iniciada)
Deploy 24/7 em VPS sem depender da maquina do dev:
1. Cloudflare Tunnel substitui ngrok (URL estavel, TLS automatico).
2. systemd units para `webhook_server.py` e `cloudflared`.
3. Script `deploy_vps.sh` automatiza instalacao no Linux.
4. Decisao arquitetural pendente: como manter Claude Code Monitor 24/7
   sem sessao tty interativa.

Detalhes: `docs/TRILHA_2_ROADMAP.md`.

### Nao-objetivos
- TTS (audio sintetizado de saida).
- Processamento de video.
- Multi-tenancy (cada deploy = 1 dev/aluno).

---

## 11. Memory Pointers

- Project memory: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/project_whatsapp_agent.md`
- megaAPI reference: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/reference_megaapi.md`
- Memory index: `~/.claude/projects/C--Users-GEOVANE-Desktop-teste/memory/MEMORY.md`
