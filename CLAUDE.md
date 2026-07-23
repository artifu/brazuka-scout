# Brazuka Scout — Project Context for Claude Code

## What this project is
A football stats tracker that parses WhatsApp group chat exports and uses Claude AI to automatically extract match results, goal scorers, player availability, cards, and funny moments. Built for the "BRAZUKA & RECEBA FC" group — a Brazilian recreational football team playing in a Tuesday night league at Magnuson Park, Seattle.

## Owner
- GitHub: artifu (Arthur Mendes, arthurteixeiramendes@gmail.com)
- This is a learning project — Arthur is new to Claude Code and GitHub

## Project roadmap
- [x] Phase 1: Chat parser + AI extractor + SQLite + CLI (DONE)
- [x] Phase 2: Web dashboard — Next.js + Supabase, hosted on Vercel (DONE)
- [x] Phase 3A: WhatsApp bot — Parte B (stat query answering) (DONE — running via pm2)
- [ ] Phase 3B: WhatsApp bot — Parte A (auto-ingest game results from group chat)
- [ ] Phase 3C: Convocação bot — DM players pre-game, collect availability, predict win probability

## Current state (Phase 3A — DONE)
The bot is running on Arthur's Mac Mini via pm2 with a watchdog process.

### How to start the bot
```bash
cd ~/Documents/brazuka-scout
pm2 start ecosystem.config.js   # start with watchdog
pm2 logs brazuka-bot             # view logs
pm2 restart brazuka-bot          # restart
pm2 stop brazuka-bot             # stop
```

If WhatsApp session expires (QR needed):
```bash
pm2 stop brazuka-bot
cd bot && rm -rf session
pkill -9 -f "Google Chrome for Testing" 2>/dev/null; sleep 3; node index.js
# Scan QR with WhatsApp Business, wait for [READY], then Ctrl+C
pm2 start ecosystem.config.js
```

### Bot trigger
Users say `brzk <pergunta>` or `brazuka <pergunta>` in DM (or group once added).
Example: `brzk quantos gols o kuster tem?`

### Architecture
```
bot/watchdog.js     — spawns index.js, restarts if it hangs at startup (puppeteer cosmiconfig issue)
bot/index.js        — WhatsApp client, routes messages via trigger words
bot/query_handler.js — Claude agentic loop (tool_use → Supabase → response)
bot/tools.js        — 8 Supabase tools for stats queries
ecosystem.config.js — pm2 config (runs watchdog.js)
```

### Known quirks
- puppeteer 24.x hangs intermittently at startup due to cosmiconfig filesystem scan
- Fix: `bot/patch-puppeteer.js` patches `node_modules/puppeteer/lib/cjs/puppeteer/getConfiguration.js`
  to skip cosmiconfig when `PUPPETEER_EXECUTABLE_PATH` is already set
- `postinstall` in package.json runs the patch automatically after `npm install`
- watchdog.js handles residual hangs by killing and restarting after 45s

### ⚠️ Supabase security rule — run enable_rls.sql after adding any table
Every table MUST have RLS enabled, or Supabase sends a "Table publicly
accessible" security alert. You no longer hand-maintain a per-table list:
`migrations/enable_rls.sql` is now self-healing — it loops over every table in
the public schema, enables RLS, and grants a read-only "public read" policy to
all of them except the ones listed in its `sensitive` array (service-role only).

After creating a new table, just re-run the whole `migrations/enable_rls.sql` in
the Supabase SQL Editor and the new table is covered automatically. Only edit
the script if the new table must be hidden from the anon/dashboard key — in that
case add its name to the `sensitive` array. The anon key (dashboard) gets
read-only access; writes use the service key (bypasses RLS).

### Supabase schema (key tables)
- `games`: id, game_date, opponent, opponent_id (FK→teams), home_or_away, result, score_brazuka, score_opponent, team_id, season_id
- `goals`: id, game_id, player, player_id (FK→players), count
- `appearances`: id, game_id, player, player_id (FK→players)
- `players`: id, canonical_name, aliases[]
- `teams`: id, name, aliases[], division, notes
- `elo_ratings`: team_name, rating, games_played, team_id (FK→teams)
- `player_impact`: player_id, win_lift, p_value, confidence_level

### Win probability model (from dashboard)
```js
sigmoid(-0.321 + 0.0070 × (brazukaElo - oppElo))  // base probability
// Each confirmed player adds their win_lift from player_impact table
```

## Phase 3C plan (next — Convocação bot)
- Add `phone` and `invite` columns to `players` table
- `bot/convocation.js` — sends DMs to all players where `invite=true` and `phone` is set
- Collect yes/no/maybe responses (no `brzk` trigger needed for replies)
- `get_lineup_probability` tool — base ELO probability + player_impact adjustments per confirmation
- Trigger: `brzk convoca 2026-04-08` or scheduled automatically on Sunday

## File structure
- `parser.py` — parses WhatsApp .txt export into Message objects
- `game_detector.py` — finds game windows (clusters of messages around each game)
- `extractor.py` — sends game windows to Claude API, gets back structured JSON
- `database.py` — SQLite storage + query helpers (legacy — data now in Supabase)
- `main.py` — CLI entry point
- `dashboard/` — Next.js web dashboard (Vercel)
- `bot/` — WhatsApp bot (Node.js + whatsapp-web.js)
- `migrations/` — SQL + Python scripts for Supabase schema migrations
