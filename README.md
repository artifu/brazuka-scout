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

### 🤖 AI Data Pipeline
- Parsed **5 years of WhatsApp group chat** (194k+ lines) using Claude AI
- Extracted match results, goal scorers, assists, cards, and player availability from freeform Portuguese messages
- Backfilled all seasons (2021–2025) including data not available in Arena Sports

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
| AI Extraction | Claude (Anthropic) |
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
pip install anthropic supabase pandas statsmodels
export ANTHROPIC_API_KEY=...
export SUPABASE_URL=...
export SUPABASE_KEY=...

python main.py import _chat.txt   # parse + extract + save
python compute_player_impact.py   # recalculate win lift model
python award_badges.py            # sync badges to Supabase
```

---

## Roadmap

- [x] Phase 1 — WhatsApp parser + Claude AI extractor + SQLite CLI
- [x] Phase 2 — Live web dashboard (Supabase + Next.js + Vercel)
- [ ] Phase 3 — WhatsApp bot (auto-ingest results + answer stat queries in the group chat)

---

*Built by Arthur Mendes ([@artifu](https://github.com/artifu)) with [Claude Code](https://claude.ai/code)*
