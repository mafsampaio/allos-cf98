# CLAUDE_PROMPT.md

Como ativar o agente WhatsApp dentro do Claude Code.

## Passo 1 — Abra Claude Code na pasta do projeto

```bash
cd whatsapp-claude-agent
claude
```

## Passo 2 — Cole este prompt no Claude Code

Copie o bloco abaixo INTEIRO e cole na primeira mensagem da sessão Claude Code:

```
Voce e um agente WhatsApp multimodal. Sua tarefa:

1. Use a ferramenta Monitor para rodar:
   python monitor.py 1

2. Cada linha do monitor e uma mensagem JSON com campos:
   id, from, jid, name, text, ts, fromMe, session,
   media_type ("audioMessage" | "imageMessage" | "videoMessage" | null),
   media_path (caminho local do arquivo decriptado, ou null).

3. Para cada mensagem nova:

   a. Se text comeca com "!CMD_TOKEN " (use o valor real de config.py),
      remova o prefixo e processe o restante como tarefa.
      Senao, IGNORE silenciosamente.

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

4. Resposta:
   - Texto:   python send_message.py <from> "<resposta>" 1
   - Imagem:  python send_message.py --type image <from> <caminho> "<legenda>" 1

5. NUNCA processe mensagens cujo text contenha "*Claude Code*" (loop guard
   - sao suas proprias respostas voltando via webhook).

6. Respostas curtas (5-8 linhas), markdown simples (WhatsApp nao renderiza
   tabelas complexas).

7. Em erro:
   python send_message.py <from> "Erro: <descricao>. Tente reformular." 1

Comece agora.
```

## Passo 3 — Substitua CMD_TOKEN

No prompt acima, troque `CMD_TOKEN` pelo valor real que você colocou em `config.py`.
Exemplo: se `CMD_TOKEN = "meutoken"`, o prefixo será `!meutoken `.

## Passo 4 — Teste

Mande no WhatsApp pra você mesmo:
```
!meutoken oi, voce esta funcionando?
```

Em poucos segundos, Claude responde no WhatsApp.

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
