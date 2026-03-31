# Phase 3 — WhatsApp Bot (Brazuka Scout)

## Contexto geral
Bot para o grupo WhatsApp "BRAZUKA & RECEBA FC" que:
- **Parte B** (fazer primeiro): responde perguntas de stats no chat
- **Parte A** (depois): auto-ingere resultados de jogos automaticamente

---

## Infraestrutura decidida
- **Roda no Mac do Arthur** (sempre ligado, tem IP fixo ou ngrok)
- **Número WhatsApp Business** dedicado e ativo — já disponível
- **Stack**: Node.js + `whatsapp-web.js` (sessão headless via Puppeteer)
- **Backend de dados**: Supabase (já existe, credenciais no .env)
- **LLM**: Claude API (já existe chave no .env)

---

## Parte B — Query Answering (FAZER PRIMEIRO)

### Objetivo
Alguém no grupo manda `@bot artilheiro?` ou `quantos gols o Arthur tem?`
O bot consulta o Supabase e responde em PT/EN.

### Arquitetura
```
Mensagem no grupo
    ↓
whatsapp-web.js listener
    ↓ (filtra mensagens que mencionam o bot ou têm palavra-chave)
query_handler.js
    ↓
Claude API (function calling) com tools que consultam Supabase
    ↓
Resposta formatada em PT no grupo
```

### Claude function calling tools a implementar
Dar ao Claude acesso às seguintes funções como tools:

| Tool | Descrição |
|------|-----------|
| `get_top_scorers(season?, limit?)` | Artilheiros da temporada ou histórico |
| `get_player_stats(name)` | Gols, assistências, MP, win% de um jogador |
| `get_overall_record(season?)` | W/D/L geral do Brazuka |
| `get_next_game()` | Próximo jogo (data, adversário, campo) |
| `get_head_to_head(opponent)` | Histórico contra um adversário |
| `get_recent_results(n?)` | Últimos N resultados |
| `get_standings()` | Tabela atual da divisão |

### Fluxo de uma query
1. Mensagem chega
2. Bot verifica se deve responder (menção, keyword, ou reply)
3. Manda para Claude com system prompt + tools
4. Claude chama as tools necessárias
5. Claude formula resposta em português
6. Bot envia no grupo

### Gatilhos para responder
- Mensagem começa com `!stats`, `!bot`, `@Brazuka Bot`
- OU é reply direto ao bot
- NÃO responder a tudo (spam)

### System prompt sugerido
```
Você é o Brazuka Bot, assistente oficial do BRAZUKA & RECEBA FC.
Responda sempre em português brasileiro, de forma direta e com bom humor.
Use emojis com moderação. Para perguntas de stats, use as tools disponíveis.
Se não souber a resposta, diga que não tem esse dado ainda.
```

---

## Parte A — Auto-ingestão (FAZER DEPOIS)

### Objetivo
Quando alguém posta o resultado no grupo (ex: "ganhamos 3x1, gols do Arthur 2 e Mazza 1"),
o bot detecta automaticamente e salva no banco sem precisar rodar scripts na mão.

### Lógica existente para reutilizar
- `extractor.py` — sistema prompt + schema JSON para extrair resultado do chat
- `game_detector.py` — detecta janelas de jogo por cluster de mensagens
- `update_after_game.py` — pipeline completo pós-jogo (ELO, Win Lift, etc.)

### Fluxo
```
Mensagem pós-jogo detectada
    ↓
Acumula janela de mensagens (30min antes/depois)
    ↓
Chama Claude API com sistema prompt do extractor.py
    ↓
JSON estruturado → upsert no Supabase
    ↓
Roda update_after_game.py
    ↓
Confirma no grupo: "✅ Resultado salvo! Brazuka 3x1 Newbeebee"
```

---

## Setup técnico do bot

### Estrutura de arquivos sugerida
```
brazuka-scout/
  bot/
    index.js          ← ponto de entrada, inicia whatsapp-web.js
    query_handler.js  ← recebe mensagem, decide se responde, chama Claude
    tools.js          ← implementação das Supabase tools para function calling
    ingestion.js      ← (Parte A) detecta resultado e salva
    session/          ← dados da sessão WhatsApp (gitignore!)
  .env                ← SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
```

### Dependências Node
```bash
npm install whatsapp-web.js @anthropic-ai/sdk @supabase/supabase-js qrcode-terminal
```

### Autenticação WhatsApp
- Na primeira execução: escanear QR code com o número Business
- Sessão persiste em `bot/session/` (não commitar!)
- Se o Mac reiniciar: bot reinicia sozinho se configurado com `pm2` ou `launchd`

### Manter rodando no Mac
```bash
npm install -g pm2
pm2 start bot/index.js --name brazuka-bot
pm2 startup   # configura auto-start no boot
pm2 save
```

---

## Estado atual (início da sessão de Phase 3)
- [ ] Criar `bot/index.js` com whatsapp-web.js básico (conectar + receber mensagens)
- [ ] Criar `bot/tools.js` com as Supabase queries
- [ ] Criar `bot/query_handler.js` com Claude function calling
- [ ] Testar localmente no Mac
- [ ] Configurar pm2 para auto-start
- [ ] (Parte A depois) `bot/ingestion.js`

## Começar por aqui na próxima sessão
**Primeiro arquivo a criar: `bot/index.js`** — conecta ao WhatsApp, loga mensagens recebidas,
filtra pelo grupo correto, e chama `query_handler.js` quando detecta gatilho.

O nome do grupo WhatsApp é: **"BRAZUKA & RECEBA FC"** (confirmar string exata com Arthur).
