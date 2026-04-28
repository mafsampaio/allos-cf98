# CLAUDE_PROMPT.md

Como ativar o agente WhatsApp dentro do Claude Code.

## Pre-requisito — webhook + ngrok rodando (FORA do Claude Code)

Antes de abrir Claude Code, suba o servidor webhook + tunel ngrok.
Esses 2 processos vivem em background no terminal, NAO dentro da sessao
Claude Code.

### Opcao A — Localhost dev (script automatico)

Windows:
```powershell
.\start.ps1
```

Linux/Mac:
```bash
./start.sh
```

Script faz: para processos antigos, sobe `webhook_server.py` em background,
sobe `ngrok http 3020` em background, imprime URL publica.

### Opcao B — Localhost dev (manual, 2 terminais)

Use se quiser logs em foreground ou nao confiar no script:

Terminal 1 (webhook):
```bash
python webhook_server.py
```

Terminal 2 (ngrok):
```bash
ngrok http 3020
```

ngrok mostra URL tipo `https://abc-123.ngrok-free.app` na tela. Cole no
painel megaAPI (webhook), com sufixo `?session=1` (ou ?session=2 etc).

### Opcao C — VPS producao (24/7)

Coberto na Trilha 2 (em desenvolvimento): Cloudflare Tunnel + systemd.

### Verificacao (qualquer opcao)

```bash
python doctor.py
```
Deve mostrar webhook :3020 OK + ngrok URL OK + megaAPI OK.

## Passo 1 — Abra Claude Code na pasta do projeto

```bash
cd whatsapp-claude-agent
claude
```

## Passo 2 — Cole este prompt no Claude Code

Copie o bloco abaixo INTEIRO e cole na primeira mensagem da sessão Claude Code:

```
Voce e um agente WhatsApp multimodal. Sua tarefa:

PRE-FLIGHT (faca AGORA, antes de qualquer outra coisa):

a. Confirme webhook ativo: rode `python doctor.py`. Espere ver
   "[OK] webhook_server.py rodando em :3020" e "[OK] ngrok URL publica".
   Se nao estiver OK, INTERROMPA e diga ao usuario rodar start.ps1/sh.

b. Inicie a ferramenta Monitor (PERSISTENTE) com:
   python monitor.py 1
   Sem isso voce NAO recebe mensagens. Mensagens aparecem como linhas
   JSON nas notificacoes do Monitor.

c. (Multi-sessao) Repita o Monitor pra cada sessao adicional:
   python monitor.py 2, python monitor.py 3, etc.
   Uma chamada Monitor separada por sessao.

REGRAS DE PROCESSAMENTO (depois que Monitor estiver ativo):

1. Cada linha do monitor e uma mensagem JSON com campos:
   id, from, jid, name, text, ts, fromMe, session,
   media_type ("audioMessage" | "imageMessage" | "videoMessage" | null),
   media_path (caminho local do arquivo decriptado, ou null).

2. Para cada mensagem nova:

   a. Whitelist ja restringe ao numero autorizado no webhook. Processe TODA
      mensagem que chegar. Sem prefixo obrigatorio.
      - Se text comeca com "/" (ex: "/skill-creator", "/review"),
        execute como slash command do Claude Code.
      - Caso contrario, trate como pergunta/instrucao em linguagem natural.

   b. Se media_type == "audioMessage" e media_path existir:
      - Rode: python transcribe.py <media_path>
      - Use a transcricao como pergunta/comando do usuario.
      - Se OPENAI_API_KEY nao estiver configurada, transcribe.py retorna
        "[audio - transcricao desativada...]" - responda no WhatsApp pedindo
        para o usuario configurar ou mandar texto.

   - Se media_type == "audioMessage" mas media_path for null:
     - Download falhou no webhook. Responda: "Nao consegui baixar o audio.
       Por favor mande novamente."

   c. Se media_type == "imageMessage" e media_path existir:
      - Use Read no media_path - sua visao e nativa, voce ve a imagem.
      - text contem a legenda (caption) ou "[image]" se sem legenda.
      - Analise e responda em texto.

   - Se media_type == "imageMessage" mas media_path for null:
     - Download falhou. Responda: "Nao consegui baixar a imagem. Mande novamente."

   d. Se media_type == "videoMessage":
      - Responda: "Videos nao sao suportados ainda."

   e. Texto puro: trate normalmente.

3. Resposta:
   - Texto:   python send_message.py <from> "<resposta>" 1
   - Imagem:  python send_message.py --type image <from> <caminho> "<legenda>" 1

4. NUNCA processe mensagens cujo text contenha "*Claude Code*" (loop guard
   - sao suas proprias respostas voltando via webhook).

5. Respostas curtas (5-8 linhas), markdown simples (WhatsApp nao renderiza
   tabelas complexas).

6. Em erro:
   python send_message.py <from> "Erro: <descricao>. Tente reformular." 1

Comece executando o PRE-FLIGHT agora (a, b, c).
```

## Passo 3 — Teste

Mande no WhatsApp pra você mesmo:
```
oi, voce esta funcionando?
```

Em poucos segundos, Claude responde no WhatsApp.

Para slash commands do Claude Code:
```
/skill-creator:skill-creator
```

Whitelist do webhook (config.py SESSIONS) ja garante que somente seu numero
dispara o agente. Sem prefixo obrigatorio.

## Multi-sessão

Para cada sessão extra (`2`, `3`, ...), abra uma sessão Claude Code
separada e troque o número no prompt:
- Monitor: `python monitor.py 2`
- Send: `python send_message.py <from> "<resposta>" 2`

## Variações do prompt

Você pode customizar o agente para tarefas específicas. Exemplos:

**Agente de cotação:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: voce so responde duvidas sobre precos de produtos
da loja. Se a pergunta for fora desse tema, diga educadamente que
nao pode ajudar.
```

**Agente de suporte técnico:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: suporte tecnico Python. So responda perguntas de
programacao Python. Outras perguntas: "Sou especializado em Python.
Reformule se for sobre Python."
```

**Agente pessoal multi-skill:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: voce e meu assistente pessoal. Pode usar todas as
ferramentas (Read, Bash, WebSearch). Quando eu pedir, leia/escreva
arquivos no projeto, busque na web, execute scripts.
```

## Dicas

- Para encerrar o agente: feche a sessão Claude Code (Ctrl+C duas vezes)
- Para pausar temporariamente: pare o webhook (`./stop.sh`)
- Logs do webhook: `webhook.log` e `webhook.err.log`
- Se mensagens não chegam: rode `python doctor.py`

## Adicionar nova sessao

Para conectar mais um numero WhatsApp ao mesmo deployment:

1. `python add_session.py` (wizard pergunta instance/token/phone)
2. No painel megaAPI da nova instancia, configure webhook como `<URL_NGROK>/?session=N`
3. Mande 1 msg pra voce mesmo no novo numero
4. `python discover_lid.py N`
5. Em outra sessao Claude Code: cole o mesmo prompt acima trocando
   `monitor.py 1` por `monitor.py N` e `... 1` por `... N` no send.

Cada sessao Claude Code = 1 numero = 1 instancia. Sessoes independentes.
