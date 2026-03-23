# ⚽ Brazuka Scout

**The stats hub for BRAZUKA & RECEBA FC** — a Brazilian recreational football team playing Tuesday nights at Magnuson Park, Seattle.

Built from scratch with Claude AI: parses 5 years of WhatsApp match history, runs a live Next.js dashboard, and predicts upcoming games using an ELO model calibrated on 873 division games.

---

## What it does

### 📊 Live Dashboard
A public web dashboard tracking everything about the club:

- **Overall record** — W/D/L, goals for/against, Win %, Points Rate (W=3 D=1 L=0)
- **Top scorers & assist leaders** — with games played, contribution rate, and win lift stat
- **Win Lift** — statistical model showing how much each player improves (or hurts) the team's win probability when they play
- **Recent games** — results, scorelines, opponent, home/away
- **Season by Season** — historical table with league position (🥇🥈🥉 medals for podium finishes), Pts%, Win%
- **Goalkeepers** — dedicated section for Alexis, Marcelo D, Darley, and Victor Ozorio with MP / GC / GC per game / Win% / Pts%
- **Top opponents** — head-to-head record vs every team we've faced
- **Division ELO Rankings** — all-time power ranking of every team in our Tuesday Men's division since 2021
- **Brazuka vs Receba** — separate tabs for both teams

### 🎯 Next Game Predictor
Before every game, the dashboard shows a Kalshi-style probability card:

- Auto-detects the next game from Arena Sports (no manual updates needed)
- Shows **Win / Draw / Loss probabilities** using a logistic regression model
- ELO comparison between Brazuka and the opponent
- **Head-to-head history** — all previous meetings, goals, recent results
- Dropdown to browse **all remaining games** in the season
- Snapshots each prediction to a database so we can track model accuracy over time

### 🤖 AI Data Pipeline
- Parsed **5 years of WhatsApp group chat** (194k+ lines) using Claude AI
- Extracted match results, goal scorers, assists, cards, and player availability from freeform Portuguese messages
- Backfilled all 20 seasons (2021–2025) including historical data not in Arena Sports

---

## Tech stack

| Layer | Tech |
|-------|------|
| Dashboard | Next.js 16 + React 19 + Tailwind CSS 4 |
| Database | Supabase (PostgreSQL) |
| Hosting | Vercel |
| AI Extraction | Claude (Anthropic) |
| Data source | WhatsApp exports + Arena Sports API |
| ELO model | Python (scikit-learn / statsmodels) |

---

## How the ELO model works

Calibrated on **873 intra-division games** (2021–2025) scraped from Arena Sports:

```
P(win) = sigmoid(-0.321 + 0.007 × ELO_diff)
Draw rate ≈ 9.6% (roughly constant in this division)
```

Starting ELO: 1000. Updated after each game using standard K-factor decay. No significant home advantage was found in this division, so it's not included.

---

## How the Win Lift stat works

For each player, an OLS linear regression estimates how much the team's win rate changes when that player is in the squad vs. absent:

```
result ~ player_present + [other covariates]
```

Confidence shown as ● (high, p<0.1) / ◑ (medium, p<0.2) / ○ (low). Green = positive lift ≥ +2%, red = negative < -1%, grey = neutral.

---

## Project structure

```
brazuka-scout/
├── dashboard/          # Next.js app (deployed to Vercel)
│   ├── app/            # Pages and components
│   └── lib/data.ts     # All Supabase queries + Arena Sports API calls
├── migrations/         # SQL schema files (run in Supabase SQL editor)
├── compute_player_impact.py   # Win Lift regression
├── populate_division_games.py # Backfill all division game scores
├── fill_league_positions.py   # Reconstruct historical league standings
└── *.py                # Season import scripts (one per season)
```

---

## Running locally

**Dashboard:**
```bash
cd dashboard
npm install
npm run dev   # runs on localhost:3000
```

**Python scripts** (data pipeline / backfill):
```bash
pip install -r requirements.txt
# Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
python compute_player_impact.py
```

---

*Built by Arthur Mendes ([@artifu](https://github.com/artifu)) with Claude Code*
