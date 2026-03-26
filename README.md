# ⚽ Brazuka Scout

**The stats hub for BRAZUKA & RECEBA FC** — a Brazilian recreational football team playing Tuesday and Thursday nights at Magnuson Park, Seattle.

Built from scratch with Claude AI: parses 5 years of WhatsApp match history, runs a live Next.js dashboard, and predicts upcoming games using an ELO model calibrated on 873+ division games.

🔴 **Live → [brazuka-scout.vercel.app](https://brazuka-scout.vercel.app)**

---

## What it does

### 📊 Live Dashboard
A public web dashboard tracking everything about the club:

- **Overall record** — W/D/L, goals for/against, Win%, Points Rate (W=3 D=1 L=0)
- **Top scorers & assist leaders** — games played, G+A per game, and win lift stat
- **Win Lift** — statistical model showing how much each player improves the team's win probability when present
- **Current Season Standings** — full division table (MP / W / D / L / GF / GA / GD / Pts) for all teams
- **Season Projection** — Monte Carlo simulation (10 000 runs) projecting where every team finishes; hover to see top-3 and bottom-3 odds
- **Recent games** — results, scorelines, opponent, home/away
- **Season by Season** — historical table with league position (🥇🥈🥉 for podium finishes), Pts%, Win%
- **Goalkeepers** — dedicated section with MP / GC / GC per game / Win% / Pts%
- **Player profiles** — click any player to see with/without stats and personal achievement badges
- **Top opponents** — head-to-head record vs every team faced
- **Division ELO Rankings** — all-time power ranking of every team since 2021
- **Brazuka vs Receba** — separate tabs for both teams

### 🎯 Next Game Predictor
Before every game, the dashboard shows a Kalshi-style probability card:

- Auto-detects the next fixture from Arena Sports (no manual updates needed)
- **Win / Draw / Loss probabilities** using a logistic regression ELO model
- ELO comparison between Brazuka and the opponent
- **Head-to-head history** — all previous meetings and recent results
- Dropdown to browse all remaining games in the season
- Snapshots each prediction so model accuracy can be tracked over time

### 🏆 Achievement Badges
30+ custom badges awarded for memorable moments — displayed on each player's profile:

| Badge | Description |
|---|---|
| 🎩 Hat Trick / Poker / Manita | 3, 4, or 5 goals in one game |
| 🍽️ Garçom | Multiple assists in a game |
| 🏆 Champion | Title-winning season badges |
| ⚔️ Victus / Victus II | Playing through adversity |
| 🐀 Rat Trick | Scoring 3 goals that definitely weren't intentional |
| 🥿 Shoot Fofo | Shooting with the wrong foot |
| 💤 Sleepy Gus | Sleeping on the field |
| 🕺 Little Roll | Nutmeg |
| 🚀 Orbit | Ball sent to orbit |
| 🎮 Famine | Square button only, never passes |
| 💀 Glass Bones | Outstanding body resistance to impacts |
| ⚡ Chapada | Screamer free kick |
| ...and many more | |

### 🤖 AI Data Pipeline + RAG
The entire data layer is AI-powered:

**Extraction pipeline:**
- Parsed **5 years of WhatsApp group chat** (194k+ lines, bilingual PT/EN) using Claude AI
- Custom `game_detector.py` clusters messages into game windows using temporal proximity and keyword signals
- Claude extracts structured JSON (scorers, result, cards, funny moments) from freeform chat

**RAG pipeline (Retrieval-Augmented Generation):**
- Indexes all game windows as vector-embedded chunks in **Supabase pgvector**
- 3-stage pipeline: chunking → classification (Claude Haiku) → embedding (Voyage AI `voyage-3-lite`)
- Claude Haiku classifies each chunk (`result / signup / injury / banter / logistics / off_topic`) before embedding — filters ~70% of noise before it hits the vector store
- Semantic search over 5 years of match history: *"quando foi a última vez que ganhamos da Newbeebee?"*

**Player audit system:**
- `audit_player.py` — scans all 452 game windows to recover missing appearances
- Smart "last signup list" algorithm: takes the final version of each game's forwarded signup chain, extracts the confirmed player list, and cross-references with the DB
- Recovered **50+ missing appearances** across Mazza, Igor, Chico and others — correcting 4 years of incomplete tracking

---

## How the models work

### ELO ratings
Calibrated on **873+ intra-division games** (2021–2025) scraped from Arena Sports:

```
P(win) = sigmoid(−0.321 + 0.007 × ELO_diff)
Draw rate ≈ 9.6%
```

Starting ELO: 1000. No significant home advantage was detected in this division.

### Win Lift (OLS)
For each player, an OLS regression estimates how much the team's win rate changes when they play:

```
result ~ player_present + opponent_elo_diff + home_advantage
```

Confidence levels: ● high (p < 0.10) · ◑ suggestive (p < 0.25) · ○ inconclusive

### Season Projection (Monte Carlo)
For each remaining fixture in the current season, samples win/draw/loss outcomes from ELO-based probabilities. Runs 10 000 simulations and returns:
- **Projected finish** — median simulated final position (ties broken by mean)
- **Top 3 / Bottom 3 %** — shown on hover over each team's projection pill

---

## Tech stack

| Layer | Tech |
|-------|------|
| Dashboard | Next.js (App Router) + TypeScript + Tailwind CSS |
| Database | Supabase (PostgreSQL) |
| Hosting | Vercel (auto-deploy on push to `main`) |
| AI Extraction | Claude (Anthropic) — structured JSON from freeform chat |
| RAG / Embeddings | Voyage AI (`voyage-3-lite`) + Supabase pgvector |
| RAG Classifier | Claude Haiku — chunk labeling before embedding |
| Data sources | WhatsApp exports + Arena Sports API |
| Analytics | Python (statsmodels, pandas) |

---

## Project structure

```
brazuka-scout/
├── dashboard/                        # Next.js app → Vercel
│   ├── app/
│   │   ├── page.tsx                  # Main server component
│   │   ├── PlayerTable.tsx           # Sortable player rankings
│   │   ├── GoalkeeperTable.tsx       # Goalkeeper stats
│   │   ├── CurrentSeasonTable.tsx    # Division standings + projection
│   │   ├── NextGamePredictor.tsx     # Win probability widget
│   │   └── SeasonFilter.tsx          # Season/team switcher
│   ├── lib/
│   │   ├── data.ts                   # All Supabase queries + Arena API
│   │   └── supabase.ts               # Supabase client
│   └── public/badges/                # SVG badge artwork (30+)
│
├── parser.py                         # WhatsApp .txt → Message objects
├── game_detector.py                  # Identify game windows in chat history
├── extractor.py                      # Claude API → structured match JSON
├── audit_player.py                   # Recover missing appearances via signup-list analysis
│
├── rag/                              # RAG pipeline
│   ├── chunker.py                    # Split chat into game/general chunks
│   ├── classifier.py                 # Claude Haiku chunk labeling
│   ├── embedder.py                   # Voyage AI embeddings
│   ├── indexer.py                    # Supabase pgvector upsert
│   └── query.py                      # Semantic search + Claude answer generation
├── rag_cli.py                        # CLI: index / query / stats
├── migrations/create_rag_chunks.sql  # pgvector table + HNSW index
│
├── award_badges.py                   # Badge award logic (idempotent)
├── compute_player_impact.py          # Win Lift OLS regression
├── populate_division_games.py        # Backfill all division results
└── seed_players.py                   # Player roster management
```

---

## Running locally

**Dashboard:**
```bash
cd dashboard
npm install
npm run dev   # → http://localhost:3000
```

Requires `dashboard/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

**Python scripts** (data pipeline):
```bash
pip install anthropic supabase pandas statsmodels voyageai python-dotenv
export ANTHROPIC_API_KEY=...
export VOYAGE_API_KEY=...
export SUPABASE_URL=...
export SUPABASE_KEY=...

python main.py import _chat.txt        # parse + extract + save
python compute_player_impact.py        # recalculate win lift model
python award_badges.py                 # sync badges to Supabase
```

**RAG pipeline:**
```bash
python rag_cli.py index                # chunk → classify → embed → store (full pipeline)
python rag_cli.py index --game-only    # only index game chunks (faster)
python rag_cli.py stats                # show index stats

python rag_cli.py query "quem é nosso artilheiro histórico?"
python rag_cli.py query "quando ganhamos da Newbeebee?" --verbose
```

**Player audit:**
```bash
python audit_player.py "Mazza"         # find missing appearances
python audit_player.py "Igor" --add    # add confirmed appearances to DB
```

---

## Roadmap

- [x] Phase 1 — WhatsApp parser + Claude AI extractor + SQLite CLI
- [x] Phase 2 — Live web dashboard (Supabase + Next.js + Vercel)
- [x] Phase 2.5 — RAG pipeline (pgvector + Voyage AI + Claude) + player audit system
- [ ] Phase 3 — WhatsApp bot (auto-ingest results + answer stat queries in the group chat)

---

*Built by Arthur Mendes ([@artifu](https://github.com/artifu)) with [Claude Code](https://claude.ai/code)*
