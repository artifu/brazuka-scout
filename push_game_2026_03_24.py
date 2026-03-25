#!/usr/bin/env python3
"""
Push game data for 2026-03-24 vs Axolotls to Supabase.

Also seeds:
  - furoes (no-shows): Rafael Franco, Alexis
  - opponent_players / opponent_player_nicknames:
      'nervosinho' (Axolotls, today)
      'careca cabeludo' (Do It Again, Receba — retroactive)

Run AFTER the two new migrations:
  migrations/create_furoes_table.sql
  migrations/create_opponent_players.sql

Usage:
  python3 push_game_2026_03_24.py
"""

import os
from pathlib import Path

# Load .env
for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── 1. Game record ───────────────────────────────────────────────────────────
print("\n── 1. Pushing game record ──")

game = {
    "game_date":      "2026-03-24",
    "opponent":       "Axolotls",
    "home_or_away":   "away",
    "result":         "win",
    "score_brazuka":  6,
    "score_opponent": 3,
    "scorers_known":  True,
    "venue":          "SODO",
    "field":          "50 minutes",
    "team_id":        1,
    "season_id":      1,
    "notable_moments": [
        "'Nervosinho' from Axolotls told Arthur to shut up and got into an altercation with Lucas",
        "Luigi's signature heel touch ('calcanhar') — another 'Midas reverso' moment",
        "Cleiton got nutmegged ('capote') and his son yelled from the sidelines: 'levanta, chora nao pai!'",
    ],
}

existing = sb.table("games").select("id").eq("game_date", game["game_date"]).eq("team_id", 1).execute()
if existing.data:
    game_id = existing.data[0]["id"]
    sb.table("games").update(game).eq("id", game_id).execute()
    print(f"  ✓ Game updated: id={game_id}")
else:
    resp = sb.table("games").insert(game).execute()
    game_id = resp.data[0]["id"]
    print(f"  ✓ Game inserted: id={game_id}")
print(f"    {game['game_date']} vs {game['opponent']} {game['score_brazuka']}-{game['score_opponent']}")

# ─── 2. Goals ─────────────────────────────────────────────────────────────────
print("\n── 2. Pushing goals ──")

goals = [
    {"player": "Cleiton", "count": 4, "notes": None},
    {"player": "Luigi",   "count": 2, "notes": "1 from Pablo assist, 1 from Cleiton assist"},
]

sb.table("goals").delete().eq("game_id", game_id).execute()
sb.table("goals").insert([{"game_id": game_id, **g} for g in goals]).execute()
goals_str = ', '.join(g['player'] + ' x' + str(g['count']) for g in goals)
print(f"  ✓ Goals: {goals_str}")

# ─── 3. Assists ───────────────────────────────────────────────────────────────
print("\n── 3. Pushing assists ──")

assists = [
    {"player": "Pablo",   "count": 1},  # assisted Luigi goal 1
    {"player": "Cleiton", "count": 1},  # assisted Luigi goal 2
]

sb.table("assists").delete().eq("game_id", game_id).execute()
sb.table("assists").insert([{"game_id": game_id, **a} for a in assists]).execute()
assists_str = ', '.join(a['player'] + ' x' + str(a['count']) for a in assists)
print(f"  ✓ Assists: {assists_str}")

# ─── 4. Appearances (confirmed roster) ────────────────────────────────────────
print("\n── 4. Pushing appearances ──")

players = ["Arthur", "Pablo", "Luigi", "Cleiton", "Roberto M", "Adelmo", "Lucas", "Sergio"]

sb.table("appearances").delete().eq("game_id", game_id).execute()
sb.table("appearances").upsert(
    [{"game_id": game_id, "player": p} for p in players],
    on_conflict="game_id,player",
).execute()
print(f"  ✓ Appearances: {players}")

# ─── 5. Furoes (no-shows) ─────────────────────────────────────────────────────
print("\n── 5. Pushing furoes (no-shows) ──")

furoes = [
    {
        "game_id": game_id,
        "player":  "Rafael Franco",
        "type":    "last-second",
        "reason":  "Had to take care of his daughter",
    },
    {
        "game_id": game_id,
        "player":  "Alexis",
        "type":    "late",
        "reason":  None,
    },
]

sb.table("furoes").upsert(furoes, on_conflict="game_id,player").execute()
print(f"  ✓ Furoes: {[f['player'] for f in furoes]}")

# ─── 6. Notable opponent players ─────────────────────────────────────────────
print("\n── 6. Pushing notable opponent players ──")

# Entry 1: 'nervosinho' from Axolotls — today's game
resp1 = sb.table("opponent_players").insert({
    "team":       "Axolotls",
    "notes":      "Temperamental player, got into altercations with Arthur and Lucas",
    "first_seen": "2026-03-24",
}).execute()
nervosinho_id = resp1.data[0]["id"]

sb.table("opponent_player_nicknames").insert({
    "opponent_player_id": nervosinho_id,
    "nickname":           "nervosinho",
    "game_id":            game_id,
    "context":            "Told Arthur to shut up and got into a physical altercation with Lucas",
}).execute()
print(f"  ✓ nervosinho (Axolotls) → opponent_player id={nervosinho_id}")

# Entry 2: 'careca cabeludo' from Do It Again (Receba) — retroactive, no game_id
resp2 = sb.table("opponent_players").insert({
    "team":       "Do It Again",
    "notes":      "Famous/notorious Receba league player",
    "first_seen": None,
}).execute()
careca_id = resp2.data[0]["id"]

sb.table("opponent_player_nicknames").insert({
    "opponent_player_id": careca_id,
    "nickname":           "careca cabeludo",
    "game_id":            None,
    "context":            "Retroactively added — well-known figure from Do It Again (Receba league)",
}).execute()
print(f"  ✓ careca cabeludo (Do It Again) → opponent_player id={careca_id}")

# ─── Done ─────────────────────────────────────────────────────────────────────
print("\n✅ Done! Now run: python3 update_after_game.py")
print("   to refresh ELO ratings, division standings, player Win Lift, and predictions.")
