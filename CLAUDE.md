# Brazuka Scout — Project Context for Claude Code

## What this project is
A football stats tracker that parses WhatsApp group chat exports and uses Claude AI to automatically extract match results, goal scorers, player availability, cards, and funny moments. Built for the "BRAZUKA & RECEBA FC" group — a Brazilian recreational football team playing in a Tuesday night league at Magnuson Park, Seattle.

## Owner
- GitHub: artifu (Arthur Mendes, arthurteixeiramendes@gmail.com)
- This is a learning project — Arthur is new to Claude Code and GitHub

## Project roadmap
- [x] Phase 1: Chat parser + AI extractor + SQLite database + CLI (DONE)
- [ ] Phase 2: Web dashboard (simple HTML/JS frontend reading from the DB)
- [ ] Phase 3: WhatsApp bot (whatsapp-web.js) that listens to the group, auto-ingests new game data, and answers stat queries

## How to run it
```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
python main.py import _chat.txt   # parse + extract + save (run once)
python main.py stats              # player goal rankings
python main.py games              # list all games
python main.py h2h "Newbeebee"   # head-to-head vs opponent
python main.py record            # overall W/L/D
```

## File structure
- `parser.py` — parses WhatsApp .txt export into Message objects
- `game_detector.py` — finds game windows (clusters of messages around each game)
- `extractor.py` — sends game windows to Claude API, gets back structured JSON
- `database.py` — SQLite storage + query helpers
- `main.py` — CLI entry point

## Key data patterns in the WhatsApp chat
- Game announcements: contain "Home Team: ... vs. Away Team: ..." and "Magnuson Field"
- Player signup: numbered lists that people add their name to pre-game
- Post-game results: phrases like "ganhamos" (won), "perdemos" (lost), "2 do Kuster", "1 Arthur"
- Chat format: `[MM/DD/YY, HH:MM:SS AM/PM] Sender: message`
- Chat has 194k+ lines going back to June 2021, ~17 games detected in last 90 days

## Team & opponents seen so far
- Our team: Brazuka US (also called "Brazuka", "BRAZUKA & RECEBA FC")
- Recent opponents: Newbeebee FC, Borscht United, Foden's Army, Matcha FC, Momentum, Kenny Bell FC, Arsenull, Jus 4 Kix

## Next task to work on
Build the **web dashboard** (Phase 2):
- Simple single-page app that reads from brazuka.db
- Shows: overall record, player goal rankings, recent games table, head-to-head lookup
- Should be shareable with the group (consider hosting on GitHub Pages or similar)
- Tech: plain HTML + JS + fetch API, or a lightweight Python server (Flask/FastAPI)
