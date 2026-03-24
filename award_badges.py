#!/usr/bin/env python3
"""
Auto-award badges based on scoring/assist records and season participation.
Run this after each game or whenever you want to refresh auto badges.

Game badges (accumulate per game):
  hattrick — 3+ goals in a single game
  poker    — exactly 4 goals in a single game
  manita   — 5+ goals in a single game
  garcom   — 3+ assists in a single game

Season badges (one per player per season, stored with season_id):
  champ_winter1_2024  — Winter I 2024 title (World Cup style)
  champ_winter2_2024  — Winter II 2024 title (Champions League style)
  champ_spring_2025   — Spring 2025 title (Copa style)
  champ_summer_2025   — Summer 2025 title (Ballon d'Or style)
  victus              — Summer 2024 shame season (0 wins)
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
    # slug, name, description, icon (SVG filename slug), auto_rule
    ("hattrick",         "Hat Trick",            "Scored 3 or more goals in a single game",           "hattrick",         "hattrick"),
    ("poker",            "Poker",                "Scored exactly 4 goals in a single game",           "poker",            "poker"),
    ("manita",           "Manita",               "Scored 5 or more goals in a single game",           "manita",           "manita"),
    ("garcom",           "Garçom",               "Provided 3 or more assists in a single game",       "garcom",           "garcom"),
    ("champ_winter1_2024", "Winter I 2024 Champion",  "Division champion — Winter I 2024",           "champ_winter1_2024",  "season"),
    ("champ_winter2_2024", "Winter II 2024 Champion", "Division champion — Winter II 2024",          "champ_winter2_2024",  "season"),
    ("champ_spring_2025",  "Spring 2025 Champion",    "Division champion — Spring 2025",             "champ_spring_2025",   "season"),
    ("champ_summer_2025",  "Summer 2025 Champion",    "Division champion — Summer 2025 (perfect season)", "champ_summer_2025", "season"),
    ("victus",           "Victus",               "Survived Summer 2024 — 0 wins, all heart",          "victus",           "season"),
]
for slug, name, description, icon, auto_rule in BADGE_DEFS:
    sb.table("badges").upsert({
        "slug": slug, "name": name, "description": description,
        "icon": icon, "auto_rule": auto_rule,
    }, on_conflict="slug").execute()

# ── Season ID map (from seasons table) ────────────────────────────────────────
# These IDs are stable — confirmed from the database.
CHAMPION_SEASONS = [
    (15, "champ_winter1_2024", "Winter I 2024 Champion"),
    (26, "champ_winter2_2024", "Winter II 2024 Champion"),
    (24, "champ_spring_2025",  "Spring 2025 Champion"),
    (23, "champ_summer_2025",  "Summer 2025 Champion"),
]
VICTUS_SEASON_ID = 17  # Summer 2024 — 0 wins


def award_game(badge_slug, rows, label):
    """Award a game-specific badge (deduped by player+badge+game)."""
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
            print(f"  ✓ player_id={row['player_id']} game_id={row['game_id']} ({row['count']})")
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR player_id={row['player_id']} game_id={row['game_id']}: {e}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped


def award_season(badge_slug, season_id, label):
    """Award a season badge to all players who appeared in that season."""
    awarded = skipped = 0
    print(f"Checking {label} (season_id={season_id})...")
    # Get all player_ids from game_players for games in this season
    games_r = sb.table("games").select("id").eq("season_id", season_id).eq("team_id", 1).execute()
    game_ids = [g["id"] for g in games_r.data]
    if not game_ids:
        print(f"  No games found for season {season_id}")
        return 0, 0
    players_r = sb.table("game_players").select("player_id").in_("game_id", game_ids).execute()
    player_ids = list({row["player_id"] for row in players_r.data if row["player_id"]})
    for pid in player_ids:
        try:
            sb.table("player_badges").insert({
                "player_id": pid,
                "badge_slug": badge_slug,
                "game_id":    None,
                "season_id":  season_id,
            }).execute()
            awarded += 1
            print(f"  ✓ player_id={pid}")
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR player_id={pid}: {e}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped


total_awarded = total_skipped = 0

# ── Game badges ───────────────────────────────────────────────────────────────
r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 3).not_.is_("player_id", "null").execute()
a, s = award_game("hattrick", r.data, "Hat Trick (3+ goals)")
total_awarded += a; total_skipped += s

r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).eq("count", 4).not_.is_("player_id", "null").execute()
a, s = award_game("poker", r.data, "Poker (4 goals)")
total_awarded += a; total_skipped += s

r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 5).not_.is_("player_id", "null").execute()
a, s = award_game("manita", r.data, "Manita (5+ goals)")
total_awarded += a; total_skipped += s

r = sb.table("assists").select("player_id, game_id, count") \
    .not_.is_("player_id", "null").gte("count", 3).execute()
a, s = award_game("garcom", r.data, "Garçom (3+ assists)")
total_awarded += a; total_skipped += s

# ── Season badges ─────────────────────────────────────────────────────────────
for season_id, slug, label in CHAMPION_SEASONS:
    a, s = award_season(slug, season_id, label)
    total_awarded += a; total_skipped += s

a, s = award_season("victus", VICTUS_SEASON_ID, "Victus (Summer 2024 shame season)")
total_awarded += a; total_skipped += s

print(f"\nAll done — {total_awarded} new badges awarded, {total_skipped} already existed.")
