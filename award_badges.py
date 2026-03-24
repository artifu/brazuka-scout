#!/usr/bin/env python3
"""
Auto-award badges based on auto_rule in the badges table.
Currently handles: hattrick (3+ goals in a single game).
Run this after each game or whenever you want to refresh auto badges.
"""
import os
from pathlib import Path

for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

awarded = 0
skipped = 0

# ── Hat-trick: goals.count >= 3, own_goal = false, player_id not null ─────────
print("Checking hat-tricks...")
r = sb.table("goals").select("player_id, game_id, count").eq("own_goal", False).gte("count", 3).not_.is_("player_id", "null").execute()

for row in r.data:
    try:
        sb.table("player_badges").insert({
            "player_id": row["player_id"],
            "badge_slug": "hattrick",
            "game_id":    row["game_id"],
        }).execute()
        awarded += 1
        print(f"  🎩 Hat-trick awarded — player_id={row['player_id']} game_id={row['game_id']} ({row['count']} goals)")
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            skipped += 1
        else:
            print(f"  ERROR player_id={row['player_id']} game_id={row['game_id']}: {e}")

print(f"\nDone — {awarded} new badges awarded, {skipped} already existed.")
