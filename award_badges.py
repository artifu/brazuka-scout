#!/usr/bin/env python3
"""
Auto-award badges based on scoring/assist records.
Run this after each game or whenever you want to refresh auto badges.

Badges handled:
  hattrick — 3+ goals in a single game
  poker    — exactly 4 goals in a single game
  manita   — 5+ goals in a single game
  garcom   — 3+ assists in a single game
"""
import os
from pathlib import Path

for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# ── Ensure badge definitions exist ────────────────────────────────────────────
BADGE_DEFS = [
    ("hattrick", "Hat Trick",   "Scored 3 or more goals in a single game",  "hattrick", "hattrick"),
    ("poker",    "Poker",       "Scored exactly 4 goals in a single game",   "poker",    "poker"),
    ("manita",   "Manita",      "Scored 5 or more goals in a single game",   "manita",   "manita"),
    ("garcom",   "Garçom",      "Provided 3 or more assists in a single game","garcom",   "garcom"),
]
for slug, name, description, icon, auto_rule in BADGE_DEFS:
    sb.table("badges").upsert({
        "slug": slug, "name": name, "description": description,
        "icon": icon, "auto_rule": auto_rule,
    }, on_conflict="slug").execute()

def award(badge_slug, rows, label):
    awarded = skipped = 0
    print(f"Checking {label}...")
    for row in rows:
        try:
            sb.table("player_badges").insert({
                "player_id": row["player_id"],
                "badge_slug": badge_slug,
                "game_id":    row["game_id"],
            }).execute()
            awarded += 1
            print(f"  ✓ {label} — player_id={row['player_id']} game_id={row['game_id']} ({row['count']})")
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR player_id={row['player_id']} game_id={row['game_id']}: {e}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped

total_awarded = total_skipped = 0

# ── Hat-trick: 3+ goals (also catches poker/manita, deduped by unique index) ──
r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 3).not_.is_("player_id", "null").execute()
a, s = award("hattrick", r.data, "Hat Trick (3+ goals)")
total_awarded += a; total_skipped += s

# ── Poker: exactly 4 goals ────────────────────────────────────────────────────
r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).eq("count", 4).not_.is_("player_id", "null").execute()
a, s = award("poker", r.data, "Poker (4 goals)")
total_awarded += a; total_skipped += s

# ── Manita: 5+ goals ──────────────────────────────────────────────────────────
r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 5).not_.is_("player_id", "null").execute()
a, s = award("manita", r.data, "Manita (5+ goals)")
total_awarded += a; total_skipped += s

# ── Garçom: 3+ assists ────────────────────────────────────────────────────────
r = sb.table("assists").select("player_id, game_id, count") \
    .not_.is_("player_id", "null").gte("count", 3).execute()
a, s = award("garcom", r.data, "Garçom (3+ assists)")
total_awarded += a; total_skipped += s

print(f"\nAll done — {total_awarded} new badges awarded, {total_skipped} already existed.")
