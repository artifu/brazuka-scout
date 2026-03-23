#!/usr/bin/env python3
"""
"What-if" alternate regression for Arthur.

Removes Arthur's presence from his N worst-case games:
  - game result = loss
  - opponent ELO is low (below median of opponents Arthur faced)
  - Arthur had no goal or assist in that game

Then re-runs the same OLS model and compares Arthur's coefficient.
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

ARTHUR_ID = 31
N_REMOVE = 5
MIN_APPEARANCES = 10
DRAW_SCORE = 0.33
TEAM_ID = 1

print("── Fetching data ──")

games_raw = sb.table("games") \
    .select("id, result, home_or_away, opponent") \
    .eq("team_id", TEAM_ID) \
    .in_("result", ["win", "draw", "loss"]) \
    .execute().data
print(f"  {len(games_raw)} games with results")

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

# Deduplicate
seen: dict[tuple, dict] = {}
for row in appearances_raw + game_players_raw:
    if row["player_id"] is None:
        continue
    k = (row["game_id"], row["player_id"])
    if k not in seen:
        seen[k] = row
all_apps = list(seen.values())
print(f"  {len(all_apps)} appearance records (deduped)")

elo_raw = sb.table("elo_ratings").select("team_name, rating").execute().data
elo_map = {r["team_name"].lower().strip(): r["rating"] for r in elo_raw}

# Fetch Arthur's goals and assists
arthur_goals = sb.table("goals") \
    .select("game_id, count") \
    .eq("player_id", ARTHUR_ID) \
    .eq("own_goal", False) \
    .execute().data
arthur_assists = sb.table("assists") \
    .select("game_id, count") \
    .eq("player_id", ARTHUR_ID) \
    .execute().data

arthur_contrib_games = set()
for g in arthur_goals:
    if g["count"] > 0:
        arthur_contrib_games.add(g["game_id"])
for a in arthur_assists:
    if a["count"] > 0:
        arthur_contrib_games.add(a["game_id"])

print(f"  Arthur contributed (G+A) in {len(arthur_contrib_games)} games")

# ── Build dataframes ──────────────────────────────────────────────────────────
RESULT_SCORE = {"win": 1.0, "draw": DRAW_SCORE, "loss": 0.0}
game_ids = {g["id"] for g in games_raw}

games_df = pd.DataFrame([{
    "game_id":      g["id"],
    "win_score":    RESULT_SCORE[g["result"]],
    "result":       g["result"],
    "home":         1 if g["home_or_away"] == "home" else 0,
    "opponent":     g["opponent"],
    "opponent_elo": elo_map.get(g["opponent"].lower().strip(), 1000.0),
} for g in games_raw])

# Ensure player_id is int to avoid dtype mismatch in pivot
app_df = pd.DataFrame([
    {"game_id": int(a["game_id"]), "player_id": int(a["player_id"]), "player": a["player"]}
    for a in all_apps
    if a["game_id"] in game_ids and a["player_id"] is not None
])

if app_df.empty:
    print("ERROR: no appearances found")
    sys.exit(1)

# Player lookup
players_raw = sb.table("players").select("id, canonical_name").execute().data
player_names = {p["id"]: p["canonical_name"] for p in players_raw}
for pid, name in app_df.groupby("player_id")["player"].first().items():
    if pid not in player_names:
        player_names[pid] = name

appearance_counts = app_df.groupby("player_id").size()
eligible = sorted(appearance_counts[appearance_counts >= MIN_APPEARANCES].index.tolist())
print(f"  {len(eligible)} eligible players (>= {MIN_APPEARANCES} apps)")
print(f"  Arthur in eligible: {ARTHUR_ID in eligible} | count: {appearance_counts.get(ARTHUR_ID, 0)}")

# ── Find Arthur's worst-case games to remove ─────────────────────────────────
arthur_game_ids = set(app_df[app_df["player_id"] == ARTHUR_ID]["game_id"].tolist())
arthur_games_df = games_df[games_df["game_id"].isin(arthur_game_ids)].copy()

# Only losses where Arthur had no goal/assist
candidates = arthur_games_df[
    (arthur_games_df["result"] == "loss") &
    (~arthur_games_df["game_id"].isin(arthur_contrib_games))
].copy()

if len(candidates) == 0:
    print("ERROR: No candidate games found (no losses where Arthur had no G+A)")
    sys.exit(1)

# Sort by opponent ELO ascending (worst losses vs easiest opponents first)
candidates = candidates.sort_values("opponent_elo")
remove_games = candidates.head(N_REMOVE)

print(f"\n── {N_REMOVE} games being removed from Arthur's record ──")
for _, row in remove_games.iterrows():
    print(f"  game {int(row['game_id'])}: L vs {row['opponent']} (ELO={row['opponent_elo']:.0f})")

games_to_remove = set(remove_games["game_id"].tolist())

# ── Build alternate app_df (remove Arthur from those games) ──────────────────
alt_app_df = app_df[~(
    (app_df["player_id"] == ARTHUR_ID) &
    (app_df["game_id"].isin(games_to_remove))
)].copy()

def run_ols(a_df, label):
    counts = a_df.groupby("player_id").size()
    elig = sorted(counts[counts >= MIN_APPEARANCES].index.tolist())

    app_elig = a_df[a_df["player_id"].isin(elig)]
    pivot = app_elig.pivot_table(index="game_id", columns="player_id", values="player", aggfunc="count", fill_value=0)
    pivot = pivot.clip(upper=1)

    merged = games_df.set_index("game_id")[["win_score", "home", "opponent_elo"]].join(pivot, how="left").fillna(0)
    y = merged["win_score"].values
    X_base = merged[["home", "opponent_elo"]].values
    player_cols = [int(c) for c in pivot.columns]
    X_players = merged[[c for c in pivot.columns]].values
    X = np.hstack([X_players, X_base])
    X = sm.add_constant(X, has_constant="add")
    col_names = ["const"] + [str(p) for p in player_cols] + ["home", "opponent_elo"]
    X_df = pd.DataFrame(X, columns=col_names)

    model = sm.OLS(y, X_df).fit()
    print(f"\n  [{label}] N={len(y)}, R²={model.rsquared:.3f}")

    if str(ARTHUR_ID) not in model.params:
        print(f"  Arthur not in model (not eligible under {label})")
        return None, None

    coef = model.params[str(ARTHUR_ID)]
    pval = model.pvalues[str(ARTHUR_ID)]
    n = int(counts.get(ARTHUR_ID, 0))
    sign = "+" if coef >= 0 else ""
    print(f"  Arthur: lift={sign}{coef*100:.1f}%  p={pval:.3f}  n={n}")
    return coef, pval

print("\n── Baseline (full data) ──")
base_coef, base_pval = run_ols(app_df, "baseline")

print("\n── Alternate (5 worst-case losses removed) ──")
alt_coef, alt_pval = run_ols(alt_app_df, "alternate")

if base_coef is not None and alt_coef is not None:
    delta = (alt_coef - base_coef) * 100
    print(f"\n── Summary ──")
    print(f"  Baseline:  {'+' if base_coef >= 0 else ''}{base_coef*100:.1f}%  (p={base_pval:.3f})")
    print(f"  Alternate: {'+' if alt_coef >= 0 else ''}{alt_coef*100:.1f}%  (p={alt_pval:.3f})")
    print(f"  Delta:     {'+' if delta >= 0 else ''}{delta:.1f}pp")
