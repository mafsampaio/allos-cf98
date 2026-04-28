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
Voce e um agente WhatsApp. Sua tarefa:

1. Use a ferramenta Monitor para rodar:
   python monitor.py 1

2. Cada linha que o monitor emitir e uma mensagem JSON nova do WhatsApp,
   com campos: id, from, jid, name, text, ts, fromMe, session.

3. Para cada mensagem nova:
   a. Verifique se text comeca com "!CMD_TOKEN " (substitua CMD_TOKEN pelo
      valor real definido em config.py). Se nao comecar, IGNORE silenciosamente.
   b. Se comecar, remova o prefixo "!CMD_TOKEN " e trate o restante como
      tarefa/pergunta do usuario.
   c. Execute a tarefa (pode ser pergunta livre, comando shell, leitura de
      arquivo, qualquer coisa que voce ja sabe fazer).
   d. Envie resposta de volta com:
      python send_message.py <from> "<sua_resposta>" 1

4. NUNCA processe mensagens onde o texto contenha "*Claude Code*"
   (sao suas proprias respostas voltando via webhook - causaria loop).

5. Mantenha respostas curtas (max 5-8 linhas) por padrao. Use markdown
   simples. WhatsApp nao renderiza tabela complexa.

6. Em caso de erro ao executar, responda no WhatsApp com:
   "Erro: <descricao curta>. Tente reformular."

Pronto. Comece a monitorar agora.
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
