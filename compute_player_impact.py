#!/usr/bin/env python3
"""
Compute player Win Lift via OLS linear probability model.

Model: win_score ~ player_1_present + ... + player_N_present + opponent_elo + home
  - win_score: 1.0 (win), 0.33 (draw), 0.0 (loss)
  - Only Brazuka US (team_id=1) games with a result
  - Only players with >= 15 appearances in the model

Run after updating the DB with new games:
  python3 compute_player_impact.py

Results are written to the player_impact table in Supabase.
"""

import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

# ── Load env ──────────────────────────────────────────────────────────────────
for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

MIN_APPEARANCES = 10
DRAW_SCORE = 0.33
TEAM_ID = 1  # Brazuka US

print("── Fetching data from Supabase ──")

# Games
games_raw = sb.table("games") \
    .select("id, result, home_or_away, opponent") \
    .eq("team_id", TEAM_ID) \
    .in_("result", ["win", "draw", "loss"]) \
    .execute().data
print(f"  {len(games_raw)} games with results")

# Appearances — merge appearances + game_players tables (same logic as dashboard)
def fetch_all(table, columns):
    rows, offset, page = [], 0, 1000
    while True:
        batch = sb.table(table).select(columns).range(offset, offset + page - 1).execute().data
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    return rows

appearances_raw = fetch_all("appearances", "game_id, player_id, player")
game_players_raw = fetch_all("game_players", "game_id, player_id, player")

# Deduplicate: use (game_id, player_id) as key, prefer game_players when both exist
seen: dict[tuple, dict] = {}
for row in appearances_raw + game_players_raw:
    if row["player_id"] is None:
        continue
    k = (row["game_id"], row["player_id"])
    if k not in seen:
        seen[k] = row
appearances_raw = list(seen.values())
print(f"  {len(appearances_raw)} appearance records (appearances + game_players, deduped)")

# ELO ratings (current, used as proxy for opponent strength)
elo_raw = sb.table("elo_ratings") \
    .select("team_name, rating") \
    .execute().data
elo_map = {r["team_name"].lower().strip(): r["rating"] for r in elo_raw}
print(f"  {len(elo_map)} ELO ratings loaded")

# ── Build game-level dataframe ────────────────────────────────────────────────
RESULT_SCORE = {"win": 1.0, "draw": DRAW_SCORE, "loss": 0.0}

game_ids = {g["id"] for g in games_raw}
games_df = pd.DataFrame([{
    "game_id":      g["id"],
    "win_score":    RESULT_SCORE[g["result"]],
    "home":         1 if g["home_or_away"] == "home" else 0,
    "opponent_elo": elo_map.get(g["opponent"].lower().strip(), 1000.0),
} for g in games_raw])

# ── Build appearance matrix ───────────────────────────────────────────────────
# Only appearances in games we have results for
app_df = pd.DataFrame([
    {"game_id": a["game_id"], "player_id": a["player_id"], "player": a["player"]}
    for a in appearances_raw
    if a["game_id"] in game_ids and a["player_id"] is not None
])

if app_df.empty:
    print("ERROR: no appearances found — check that appearances table has player_id set")
    sys.exit(1)

# Player lookup: player_id → canonical name (from players table, not appearances)
players_raw = sb.table("players").select("id, canonical_name").execute().data
player_names = {p["id"]: p["canonical_name"] for p in players_raw}
# Fallback: any name seen in appearances for unmapped ids
for pid, name in app_df.groupby("player_id")["player"].first().items():
    if pid not in player_names:
        player_names[pid] = name

# Appearance counts per player
appearance_counts = app_df.groupby("player_id").size()
eligible_players = sorted(appearance_counts[appearance_counts >= MIN_APPEARANCES].index.tolist())
print(f"  {len(eligible_players)} players with >= {MIN_APPEARANCES} appearances (eligible for model)")

# Pivot: one row per game, one column per eligible player (1/0)
app_eligible = app_df[app_df["player_id"].isin(eligible_players)]
pivot = app_eligible.pivot_table(index="game_id", columns="player_id", values="player", aggfunc="count", fill_value=0)
pivot = pivot.clip(upper=1)  # binary

# Merge with game features
merged = games_df.set_index("game_id").join(pivot, how="left").fillna(0)
y = merged["win_score"].values
X_base = merged[["home", "opponent_elo"]].values

# ── OLS regression ────────────────────────────────────────────────────────────
print("\n── Running OLS regression ──")
player_cols = [int(c) for c in pivot.columns]
X_players = merged[[c for c in pivot.columns]].values
X = np.hstack([X_players, X_base])
X = sm.add_constant(X, has_constant="add")

col_names = ["const"] + [str(p) for p in player_cols] + ["home", "opponent_elo"]
X_df = pd.DataFrame(X, columns=col_names)

model = sm.OLS(y, X_df).fit()
print(f"  N={len(y)} observations, R²={model.rsquared:.3f}")

# ── Confidence level ──────────────────────────────────────────────────────────
def confidence_level(p_value: float) -> str:
    if p_value < 0.10: return "high"
    if p_value < 0.25: return "suggestive"
    return "low"

# ── Assemble results ──────────────────────────────────────────────────────────
results = []
for pid in player_cols:
    col = str(pid)
    coef = model.params[col]
    pval = model.pvalues[col]
    n_games = int(appearance_counts[pid])
    results.append({
        "player_id":        pid,
        "player_name":      player_names[pid],
        "win_lift":         round(float(coef), 4),
        "p_value":          round(float(pval), 4),
        "games_played":     n_games,
        "confidence_level": confidence_level(float(pval)),
    })
    sign = "+" if coef >= 0 else ""
    print(f"  {player_names[pid]:25s}  lift={sign}{coef*100:.1f}%  p={pval:.3f}  [{confidence_level(float(pval))}]  (n={n_games})")

# ── Write to Supabase ─────────────────────────────────────────────────────────
print("\n── Writing to player_impact table ──")
for row in results:
    existing = sb.table("player_impact").select("player_id").eq("player_id", row["player_id"]).execute()
    if existing.data:
        sb.table("player_impact").update(row).eq("player_id", row["player_id"]).execute()
        print(f"  ~ updated: {row['player_name']}")
    else:
        sb.table("player_impact").insert(row).execute()
        print(f"  + inserted: {row['player_name']}")

print(f"\n✅ player_impact updated for {len(results)} players.")
print(f"   Controls: opponent_elo coef={model.params['opponent_elo']*100:.3f}%/ELO-point  home coef={model.params['home']*100:.1f}%")
