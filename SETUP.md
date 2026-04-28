# SETUP — Passo a passo (do zero)

Guia para alunos que nunca usaram megaAPI/ngrok/Claude Code.

## 1. Pré-requisitos

### 1.1 Python
- Windows: baixe em https://python.org → marque "Add Python to PATH"
- Linux: `sudo apt install python3 python3-pip`
- macOS: `brew install python3`

Teste: `python --version` (ou `python3 --version`) deve mostrar 3.8+

### 1.2 curl
- Já vem instalado em Windows 10+, macOS, Linux
- Teste: `curl --version`

### 1.3 ngrok
1. Crie conta grátis em https://dashboard.ngrok.com/signup
2. Baixe ngrok em https://ngrok.com/download
3. Extraia o `ngrok.exe` (Windows) ou `ngrok` (Linux/Mac) e coloque no PATH
4. Pegue seu authtoken em https://dashboard.ngrok.com/get-started/your-authtoken
5. Configure: `ngrok config add-authtoken SEU_TOKEN_AQUI`

### 1.4 Claude Code CLI
- Siga https://docs.anthropic.com/claude-code
- Faça login com sua conta Anthropic
- Teste: `claude --version`

### 1.5 megaAPI
1. Crie conta em https://megaapi.com.br
2. Crie uma **instância** (anote o nome, ex: `megabusiness-meuagente`)
3. Anote o **token** da instância
4. **Conecte seu WhatsApp** escaneando o QR code da megaAPI
5. Anote seu número no formato internacional sem `+` (ex: `5511999999999`)

## 2. Instalação

```bash
git clone <repo-url> whatsapp-claude-agent
cd whatsapp-claude-agent
```

Windows:
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Linux/macOS:
```bash
chmod +x install.sh start.sh stop.sh
./install.sh
```

## 3. Configuração

Abra `config.py` (criado pelo instalador) e preencha:

```python
CMD_TOKEN = "meutoken"   # legado/opcional - hoje whitelist sozinha basta

SESSIONS = {
    "1": {
        "instance": "megabusiness-meuagente",   # nome da instancia megaAPI
        "token":    "SEU_TOKEN_MEGAAPI",        # token da instancia
        "phone":    "5511999999999",            # SEU numero (DDI+DDD+numero)
        "lid":      "00000000000000",           # deixar zerado por enquanto
    },
}
```

## 4. Subir o servidor

Windows: `.\start.ps1`
Linux/Mac: `./start.sh`

Vai mostrar algo tipo:
```
Webhook URL (paste into megaAPI):
  https://abc-123.ngrok-free.app/?session=1
```

**Copie essa URL.**

## 5. Configurar webhook na megaAPI

1. Painel megaAPI → sua instância → **Webhook**
2. Cole a URL completa (com `?session=1`)
3. Salve

## 6. Descobrir seu LID

1. Mande qualquer mensagem do seu WhatsApp para você mesmo (self-chat)
2. Abra `raw_debug.jsonl` no projeto
3. Procure o campo `key.remoteJid` ou `participant`
4. Copie o número antes de `@lid` (ex: `22540172955723@lid` → `22540172955723`)
5. Cole em `config.py` no campo `lid`
6. Reinicie: `.\stop.ps1` e `.\start.ps1` (ou `.sh`)

## 7. Subir o agente Claude Code

**Pré-requisito:** webhook + ngrok já rodando (passo 4 acima).
Confirme com `python doctor.py` antes de prosseguir.

1. Abra outro terminal, `cd` na pasta do projeto
2. Rode `claude` (inicia Claude Code CLI)
3. Cole o prompt completo do `CLAUDE_PROMPT.md` na primeira mensagem
4. Claude faz pre-flight automaticamente:
   - Roda `python doctor.py` pra confirmar webhook + ngrok
   - Inicia ferramenta Monitor com `python monitor.py 1` (PERSISTENTE)
   - Aguarda mensagens

**O Monitor fica rodando enquanto a sessão Claude Code estiver aberta.**
Se você fechar o Claude Code, monitor para — webhook + ngrok continuam
rodando em background, mas mensagens recebidas ficam em fila no JSONL
até voce reabrir Claude Code.

### Multi-sessão

Pra cada sessão extra (2, 3, ...), abra outra janela Claude Code separada
e cole o prompt trocando `monitor.py 1` por `monitor.py N`. Cada sessão
Claude Code = 1 número WhatsApp.

## 8. Testar

Mande mensagem WhatsApp pra você mesmo:
```
oi, quem é você?
```

Claude responde no WhatsApp em segundos. Resposta vem assinada `*Claude Code*`.

Para slash command:
```
/skill-creator:skill-creator
```

## 9. Multi-sessão (opcional)

Adicione segunda sessão em `config.py`:
```python
SESSIONS = {
    "1": { ... },
    "2": {
        "instance": "megabusiness-outroagente",
        "token":    "OUTRO_TOKEN",
        "phone":    "5511888888888",
        "lid":      "00000000000000",
    },
}
```

Webhook URL para sessão 2: `https://abc-123.ngrok-free.app/?session=2`

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `config.py not found` | Rode install.ps1/sh primeiro |
| ngrok URL não aparece | Verifique http://127.0.0.1:4040 |
| Mensagem não chega no JSONL | Confira webhook URL no painel megaAPI + whitelist phone |
| Claude responde mas WhatsApp não recebe | Veja log: `curl` retorna 403 → token errado |
| Loop infinito | Confirme assinatura `*Claude Code*` está em `config.py` SIGNATURE |

Mais detalhes técnicos em `PROJETO.md`.

## 10. Multimodal (opcional)

### 10.1 Receber audio com transcricao

1. Crie conta em https://platform.openai.com
2. Gere API key em https://platform.openai.com/api-keys
3. Edite `config.py`: `OPENAI_API_KEY = "sk-..."`
4. Reinicie webhook: `./stop.sh && ./start.sh`
5. Mande audio no WhatsApp. Claude roda `python transcribe.py <path>` e
   responde com base no texto transcrito.

### 10.2 Receber imagens
Funciona automaticamente. Imagem decriptada vai pra `media/sessionN/<id>.jpg`.
Claude usa `Read` no arquivo (visao nativa) e descreve.

### 10.3 Enviar imagens
```bash
python send_message.py --type image 5511999999999 ./foto.jpg "minha legenda" 1
```

## 11. Adicionar nova instancia
```bash
python add_session.py
```
Configure webhook da nova: `<URL_NGROK>/?session=N`. Em outra sessao
Claude Code: `python monitor.py N`.
