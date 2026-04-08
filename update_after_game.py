#!/usr/bin/env python3
"""
update_after_game.py — Run this after every Tuesday game.

Steps:
  1. Scrape Arena Sports → update `games` table with Brazuka's result
  2. Scrape ALL division games → update `division_games` table
  3. Recompute ELO for every division team → update `elo_ratings` table
  4. Update Brazuka's league position for the current season → `seasons` table
  5. Recompute player Win Lift → `player_impact` table
  6. Mark completed games in `predictions` table (actual_result)

Usage:
  python3 update_after_game.py

Requirements: SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
"""

import os, re, time, subprocess, sys
from pathlib import Path
from collections import defaultdict

_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

import requests
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
BASE = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1"
HEADERS = {"Accept": "application/vnd.api+json", "User-Agent": "Mozilla/5.0"}

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def clean_name(name):
    name = re.sub(r"\s+(?:NPGK|NP\s*\d*|N\dP)\s*$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\((?:Tues?\.?\s+Men'?s?\s+D\d*|Tue\s+Men'?s?\s+D\d*|M|S)\)\s*(?:\([MS]\)\s*)?$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\([MS]\)\s*$", "", name, flags=re.IGNORECASE).strip()
    return name

# ─── All Brazuka seasons ──────────────────────────────────────────────────────
BRAZUKA_SEASONS = [
    ("221537", "Spring 2026"),
    ("219258", "Winter 2025-26"),
    ("215810", "Winter I 2025"),
    ("214012", "Fall 2025"),
    ("213250", "Summer 2025"),
    ("211302", "Spring 2025"),
    ("208137", "Winter II 2024"),
    ("205470", "Winter I 2024"),
    ("204186", "Fall 2024"),
    ("202652", "Summer 2024"),
    ("200446", "Spring 2024"),
    ("196948", "Winter II 2023"),
    ("194228", "Winter I 2023"),
    ("193131", "Fall 2023"),
    ("190812", "Summer 2023"),
    ("187808", "Spring 2023"),
    ("184892", "Winter II 2022"),
    ("181899", "Winter I 2022"),
    ("181297", "Fall 2022"),
    ("177686", "Spring 2022"),
    ("174858", "Winter II 2021"),
    ("172413", "Winter I 2021"),
]

# ─── STEP 1: Scrape Brazuka + Receba games ────────────────────────────────────
print("\n── Step 1a: Scraping Brazuka games from Arena Sports ──")
result = subprocess.run([sys.executable, "scrape_arena.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

print("\n── Step 1b: Scraping Receba games from Arena Sports ──")
result = subprocess.run([sys.executable, "scrape_receba.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

# ─── STEP 2: Update division_games ────────────────────────────────────────────
print("\n── Step 2: Updating all division games ──")
result = subprocess.run([sys.executable, "populate_division_games.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

print("\n── Step 2b: Updating Receba division games ──")
result = subprocess.run([sys.executable, "populate_receba_division_games.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

# ─── STEP 3: Recompute ELO ────────────────────────────────────────────────────
print("\n── Step 3: Recomputing Brazuka ELO ratings ──")

games_raw = sb.table("division_games") \
    .select("game_date, home_team, away_team, home_score, away_score") \
    .eq("league", "brazuka") \
    .order("game_date", desc=False) \
    .limit(5000) \
    .execute().data

ratings: dict[str, float] = defaultdict(lambda: 1000.0)
played:  dict[str, int]   = defaultdict(int)
K = 32

for g in games_raw:
    ht, at = g["home_team"], g["away_team"]
    hs, as_ = g["home_score"], g["away_score"]
    re_h = ratings[ht]; re_a = ratings[at]
    exp_h = 1 / (1 + 10 ** ((re_a - re_h) / 400))
    exp_a = 1 - exp_h
    score_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
    score_a = 1.0 - score_h
    ratings[ht] += K * (score_h - exp_h)
    ratings[at] += K * (score_a - exp_a)
    played[ht] += 1; played[at] += 1

rows = [
    {"team_name": t, "rating": round(r, 2), "games_played": played[t], "league": "brazuka"}
    for t, r in sorted(ratings.items(), key=lambda x: -x[1])
]
sb.table("elo_ratings").delete().eq("league", "brazuka").execute()
sb.table("elo_ratings").insert(rows).execute()
print(f"  ✓ {len(rows)} Brazuka ELO ratings updated")
top5 = ', '.join('{} ({:.0f})'.format(r['team_name'], r['rating']) for r in rows[:5])
print(f"  Top 5: {top5}")

print("\n── Step 3b: Recomputing Receba ELO ratings ──")

receba_games_raw = sb.table("division_games") \
    .select("game_date, home_team, away_team, home_score, away_score") \
    .eq("league", "receba") \
    .order("game_date", desc=False) \
    .limit(5000) \
    .execute().data

receba_ratings: dict[str, float] = defaultdict(lambda: 1000.0)
receba_played: dict[str, int] = defaultdict(int)

for g in receba_games_raw:
    ht, at = g["home_team"], g["away_team"]
    hs, as_ = g["home_score"], g["away_score"]
    re_h = receba_ratings[ht]; re_a = receba_ratings[at]
    exp_h = 1 / (1 + 10 ** ((re_a - re_h) / 400))
    exp_a = 1 - exp_h
    score_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
    score_a = 1.0 - score_h
    receba_ratings[ht] += K * (score_h - exp_h)
    receba_ratings[at] += K * (score_a - exp_a)
    receba_played[ht] += 1; receba_played[at] += 1

receba_rows = [
    {"team_name": t, "rating": round(r, 2), "games_played": receba_played[t], "league": "receba"}
    for t, r in sorted(receba_ratings.items(), key=lambda x: -x[1])
]
sb.table("elo_ratings").delete().eq("league", "receba").execute()
sb.table("elo_ratings").insert(receba_rows).execute()
print(f"  ✓ {len(receba_rows)} Receba ELO ratings updated")
top5r = ', '.join('{} ({:.0f})'.format(r['team_name'], r['rating']) for r in receba_rows[:5])
print(f"  Top 5: {top5r}")

# ─── STEP 4: Update league position ───────────────────────────────────────────
print("\n── Step 4: Updating league position ──")
result = subprocess.run([sys.executable, "fill_league_positions.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

# ─── STEP 5: Recompute player Win Lift ────────────────────────────────────────
print("\n── Step 5: Recomputing player Win Lift (OLS) ──")
result = subprocess.run([sys.executable, "compute_player_impact.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "(no output)")
if result.returncode != 0:
    print("WARNING:", result.stderr[-500:])

# ─── STEP 6: Mark actual results in predictions ───────────────────────────────
print("\n── Step 6: Marking prediction outcomes ──")

# Get all predictions without an actual_result
pending = sb.table("predictions") \
    .select("id, game_date, opponent") \
    .is_("actual_result", "null") \
    .execute().data

updated = 0
for pred in pending:
    # Try to find a completed game for this prediction
    match = sb.table("games") \
        .select("result") \
        .eq("game_date", pred["game_date"]) \
        .eq("team_id", 1) \
        .not_.is_("result", "null") \
        .limit(1) \
        .execute().data
    if match:
        sb.table("predictions") \
            .update({"actual_result": match[0]["result"]}) \
            .eq("id", pred["id"]) \
            .execute()
        print(f"  ✓ {pred['game_date']} vs {pred['opponent']} → {match[0]['result']}")
        updated += 1

if updated == 0:
    print("  (no pending predictions to update)")
else:
    print(f"  ✓ {updated} predictions marked")

print("\n✅ All done! Refresh brazuka-scout.vercel.app to see updated stats.")
