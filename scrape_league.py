#!/usr/bin/env python3
"""
scrape_league.py — Full league scraper + ELO calculator for Brazuka Scout.

Fetches all teams and games from each of Brazuka's league seasons via the
DaySmart Recreation API, populates `league_teams` and `league_games` in
Supabase, then calculates ELO ratings and writes them to `elo_ratings`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEFORE RUNNING — create these tables in Supabase SQL Editor:

  CREATE TABLE IF NOT EXISTS league_teams (
      id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      arena_team_id text UNIQUE NOT NULL,
      name          text NOT NULL,
      created_at    timestamptz DEFAULT now()
  );

  CREATE TABLE IF NOT EXISTS league_games (
      id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      arena_game_id text UNIQUE NOT NULL,
      game_date     date NOT NULL,
      home_team_id  bigint REFERENCES league_teams(id),
      away_team_id  bigint REFERENCES league_teams(id),
      home_score    int NOT NULL,
      away_score    int NOT NULL,
      season_name   text,
      league_id     text,
      created_at    timestamptz DEFAULT now()
  );

  CREATE TABLE IF NOT EXISTS elo_ratings (
      id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      league_team_id  bigint REFERENCES league_teams(id),
      calculated_at   timestamptz DEFAULT now(),
      rating          float NOT NULL,
      games_played    int NOT NULL
  );

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usage:
  SUPABASE_SERVICE_KEY=$(grep SUPABASE_SERVICE_KEY .env | cut -d= -f2) \\
  SUPABASE_URL=$(grep SUPABASE_URL .env | cut -d= -f2) \\
  python3 scrape_league.py
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests
from supabase import create_client

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# ── Arena Sports API ──────────────────────────────────────────────────────────
BASE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1"
HEADERS = {
    "Accept": "application/vnd.api+json",
    "User-Agent": "Mozilla/5.0",
}

# ── Brazuka season team IDs ───────────────────────────────────────────────────
BRAZUKA_SEASONS = [
    ("215810", "Soccer, Adult Winter I 2025 (MAG)",    "Winter I 2025"),
    ("214012", "Soccer, Adult Fall 2025 (MAG)",         "Fall 2025"),
    ("213250", "Soccer, Adult Summer 2025 (MAG)",       "Summer 2025"),
    ("211302", "Soccer, Adult Spring 2025 (MAG)",       "Spring 2025"),
    ("208137", "Soccer, Adult Winter II 2025 (MAG)",    "Winter II 2025"),
    ("205470", "Soccer, Adult Winter I 2024 (MAG)",     "Winter I 2024"),
    ("204186", "Soccer, Adult Fall 2024 (MAG)",         "Fall 2024"),
    ("202652", "Soccer, Adult Summer 2024 (MAG)",       "Summer 2024"),
    ("200446", "Soccer, Adult Spring 2024 (MAG)",       "Spring 2024"),
    ("196948", "Soccer, Adult Winter II 2024 (MAG)",    "Winter II 2024"),
    ("194228", "Soccer, Adult Winter I 2023 (MAG)",     "Winter I 2023"),
    ("193131", "Soccer, Adult Fall 2023 (MAG)",         "Fall 2023"),
    ("190812", "Soccer, Adult Summer 2023 (MAG)",       "Summer 2023"),
    ("187808", "Soccer, Adult Spring 2023 (MAG)",       "Spring 2023"),
    ("184892", "Soccer, Adult Winter II 2023 (MAG)",    "Winter II 2023"),
    ("181899", "Soccer, Adult Winter I 2022 (MAG)",     "Winter I 2022"),
    ("181297", "Soccer, Adult Fall 2022 (MAG)",         "Fall 2022"),
    ("177686", "Soccer, Adult Spring 2022 (MAG)",       "Spring 2022"),
    ("174858", "Soccer, Adult Winter ll 2022 (MAG)",    "Winter II 2022"),  # lowercase 'l'
    ("172413", "Soccer, Adult Winter I 2021 (MAG)",     "Winter I 2021"),
]

ELO_START = 1000.0
ELO_K = 32


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_league_id(brazuka_team_id: str):
    """Fetch Brazuka's team record to get its league_id."""
    url = f"{BASE_URL}/teams/{brazuka_team_id}?include=league&company=arenasports"
    data = api_get(url)
    league_rel = data.get("data", {}).get("relationships", {}).get("league", {}).get("data")
    return league_rel.get("id") if league_rel else None


def fetch_league_teams(league_id: str) -> list[dict]:
    """Return list of {arena_team_id, name} for all active teams in the league."""
    url = (
        f"{BASE_URL}/teams"
        f"?filter[league_id]={league_id}"
        "&filter[status]=active"
        "&company=arenasports"
        "&page[size]=100"
    )
    data = api_get(url)
    teams = []
    for item in data.get("data", []):
        teams.append({
            "arena_team_id": item["id"],
            "name": item.get("attributes", {}).get("name", "Unknown"),
        })
    return teams


def fetch_team_games(arena_team_id: str) -> list[dict]:
    """
    Fetch all completed games for a team.
    Scores are inline in event.attributes (home_score / visiting_score).
    Team IDs are in event.attributes (hteam_id / vteam_id as ints).
    """
    url = (
        f"{BASE_URL}/teams/{arena_team_id}"
        "?cache[save]=false"
        "&include=events.homeTeam,events.visitingTeam"
        "&company=arenasports"
    )
    data = api_get(url)

    included = data.get("included", [])
    events_by_id: dict[str, dict] = {}
    for item in included:
        if item.get("type") == "events":
            events_by_id[item["id"]] = item

    main_data = data.get("data", {})
    events_refs = main_data.get("relationships", {}).get("events", {}).get("data", [])

    games = []
    for ev_ref in events_refs:
        ev_id = ev_ref.get("id")
        ev = events_by_id.get(ev_id)
        if not ev:
            continue

        attrs = ev.get("attributes", {})
        rels = ev.get("relationships", {})

        start_date = attrs.get("start_date", "")
        game_date = start_date[:10] if start_date else None
        if not game_date:
            continue

        # Scores are directly on event attributes
        home_score = attrs.get("home_score")
        away_score = attrs.get("visiting_score")

        if home_score is None or away_score is None:
            continue
        try:
            home_score = int(home_score)
            away_score = int(away_score)
        except (TypeError, ValueError):
            continue

        # Team IDs from attributes (hteam_id/vteam_id are ints, convert to str)
        home_arena_id = str(attrs.get("hteam_id")) if attrs.get("hteam_id") else None
        away_arena_id = str(attrs.get("vteam_id")) if attrs.get("vteam_id") else None

        if not home_arena_id or not away_arena_id:
            # Fall back to relationships
            home_ref = rels.get("homeTeam", {}).get("data")
            away_ref = rels.get("visitingTeam", {}).get("data")
            home_arena_id = home_ref.get("id") if home_ref else None
            away_arena_id = away_ref.get("id") if away_ref else None

        games.append({
            "arena_game_id": ev_id,
            "game_date": game_date,
            "home_arena_id": home_arena_id,
            "away_arena_id": away_arena_id,
            "home_score": home_score,
            "away_score": away_score,
        })

    return games


# ── Supabase helpers ──────────────────────────────────────────────────────────

def upsert_league_team(sb, arena_team_id: str, name: str) -> int:
    """Upsert team by arena_team_id. Returns Supabase row id."""
    resp = (
        sb.table("league_teams")
        .upsert({"arena_team_id": arena_team_id, "name": name}, on_conflict="arena_team_id")
        .execute()
    )
    return resp.data[0]["id"]


def upsert_league_game(
    sb,
    arena_game_id: str,
    game_date: str,
    home_team_id: int,
    away_team_id: int,
    home_score: int,
    away_score: int,
    season_name: str,
    league_id: str,
) -> bool:
    """Upsert game. Returns True if new, False if already existed."""
    existing = (
        sb.table("league_games")
        .select("id")
        .eq("arena_game_id", arena_game_id)
        .execute()
    )
    if existing.data:
        return False

    sb.table("league_games").insert({
        "arena_game_id": arena_game_id,
        "game_date": game_date,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_score": home_score,
        "away_score": away_score,
        "season_name": season_name,
        "league_id": league_id,
    }).execute()
    return True


# ── Team name normalisation ────────────────────────────────────────────────────

def canonical_team_name(name: str) -> str:
    """Strip division/home/away suffixes so the same club tracks as one ELO entry.

    Examples:
      "Brazuka US (Tues Men's D)"   → "Brazuka US"
      "Brazuka US (Tues Men's D1)"  → "Brazuka US"
      "Newbeebee FC (Tues Men's D) (M)" → "Newbeebee FC"
      "FC Jinro (Tues Men's D2)"    → "FC Jinro"
    """
    import re
    # Strip league/day/gender qualifiers in parentheses
    name = re.sub(
        r'\s*\([^)]*(?:Men|Women|Tues|Thurs|Mon|Wed|Fri|D\d*|C\d*|SL\d*)[^)]*\)',
        '', name, flags=re.IGNORECASE
    )
    # Strip lone (M), (S), (H), (A) suffixes
    name = re.sub(r'\s*\([MSHA]\)\s*$', '', name)
    return name.strip()


# ── ELO calculation ───────────────────────────────────────────────────────────

def calculate_elo(sb):
    """
    Read all league_games chronologically, group teams by canonical name,
    carry ELO across all seasons, write final ratings to elo_ratings.
    """
    print("\n" + "="*60)
    print("Calculating ELO ratings...")

    # Load all games ordered by date
    games = (
        sb.table("league_games")
        .select("game_date,home_team_id,away_team_id,home_score,away_score")
        .order("game_date", desc=False)
        .limit(10000)
        .execute()
        .data
    )
    print(f"  Total completed games: {len(games)}")

    # Build: league_team db_id → canonical name
    teams = sb.table("league_teams").select("id,name").execute().data
    id_to_canonical: dict[int, str] = {t["id"]: canonical_team_name(t["name"]) for t in teams}

    # ELO keyed by canonical name — carries across seasons
    elo: dict[str, float] = {}
    played: dict[str, int] = {}

    for game in games:
        home_id = game["home_team_id"]
        away_id = game["away_team_id"]

        home_name = id_to_canonical.get(home_id)
        away_name = id_to_canonical.get(away_id)
        if not home_name or not away_name:
            continue

        if home_name not in elo:
            elo[home_name] = ELO_START
            played[home_name] = 0
        if away_name not in elo:
            elo[away_name] = ELO_START
            played[away_name] = 0

        r_home = elo[home_name]
        r_away = elo[away_name]

        expected_home = 1 / (1 + 10 ** ((r_away - r_home) / 400))
        expected_away = 1 - expected_home

        if game["home_score"] > game["away_score"]:
            actual_home, actual_away = 1.0, 0.0
        elif game["home_score"] < game["away_score"]:
            actual_home, actual_away = 0.0, 1.0
        else:
            actual_home, actual_away = 0.5, 0.5

        elo[home_name] = r_home + ELO_K * (actual_home - expected_home)
        elo[away_name] = r_away + ELO_K * (actual_away - expected_away)
        played[home_name] += 1
        played[away_name] += 1

    # Write final ratings (clear old, insert new)
    print("  Writing ELO ratings to Supabase...")
    sb.table("elo_ratings").delete().neq("id", 0).execute()

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for name, rating in elo.items():
        if played.get(name, 0) < 5:   # ignore teams with fewer than 5 games
            continue
        rows.append({
            "league_team_id": None,   # no longer meaningful with canonical grouping
            "team_name": name,
            "calculated_at": now,
            "rating": round(rating, 2),
            "games_played": played[name],
        })

    rows.sort(key=lambda r: r["rating"], reverse=True)

    # Insert in batches of 100
    for i in range(0, len(rows), 100):
        sb.table("elo_ratings").insert(rows[i:i+100]).execute()

    # Print top 30
    print(f"\n{'Rank':<5} {'Team':<40} {'ELO':>7}  {'GP':>4}")
    print("─" * 60)
    for rank, row in enumerate(rows[:30], 1):
        marker = " ◀ Brazuka" if row["team_name"] == "Brazuka US" else ""
        print(f"  {rank:<4} {row['team_name']:<40} {row['rating']:>7.1f}  {row['games_played']:>4}{marker}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    total_teams_new = 0
    total_games_new = 0
    total_games_skipped = 0

    for brazuka_team_id, season_label, season_name in BRAZUKA_SEASONS:
        print(f"\n{'─'*60}")
        print(f"Season: {season_name}  (Brazuka team_id={brazuka_team_id})")

        # Step 1: get league_id from Brazuka's team record
        try:
            league_id = fetch_league_id(brazuka_team_id)
        except Exception as e:
            print(f"  [ERROR] fetch_league_id: {e} — skipping")
            time.sleep(0.5)
            continue

        if not league_id:
            print("  [WARN] No league_id found — skipping")
            time.sleep(0.5)
            continue

        print(f"  League ID: {league_id}")
        time.sleep(0.5)

        # Step 2: fetch all teams in league
        try:
            league_team_list = fetch_league_teams(league_id)
        except Exception as e:
            print(f"  [ERROR] fetch_league_teams: {e} — skipping")
            time.sleep(0.5)
            continue

        print(f"  Teams in league: {len(league_team_list)}")

        # Upsert each team and build arena_id → supabase_id map
        arena_to_sb: dict[str, int] = {}
        for t in league_team_list:
            sb_id = upsert_league_team(sb, t["arena_team_id"], t["name"])
            arena_to_sb[t["arena_team_id"]] = sb_id
            total_teams_new += 1  # counts upserts (not strictly new, but fine)

        time.sleep(0.5)

        # Step 3: for each team, fetch their games
        season_games_new = 0
        season_games_skip = 0
        seen_game_ids: set[str] = set()  # deduplicate within season

        for t in league_team_list:
            try:
                games = fetch_team_games(t["arena_team_id"])
            except Exception as e:
                print(f"  [ERROR] fetch_team_games({t['arena_team_id']}): {e} — skipping team")
                time.sleep(0.5)
                continue

            for game in games:
                gid = game["arena_game_id"]
                if gid in seen_game_ids:
                    continue
                seen_game_ids.add(gid)

                home_sb = arena_to_sb.get(game["home_arena_id"])
                away_sb = arena_to_sb.get(game["away_arena_id"])

                if home_sb is None or away_sb is None:
                    # Team not in our league list — add it on the fly
                    if game["home_arena_id"] and home_sb is None:
                        home_sb = upsert_league_team(sb, game["home_arena_id"], "Unknown")
                        arena_to_sb[game["home_arena_id"]] = home_sb
                    if game["away_arena_id"] and away_sb is None:
                        away_sb = upsert_league_team(sb, game["away_arena_id"], "Unknown")
                        arena_to_sb[game["away_arena_id"]] = away_sb

                if home_sb is None or away_sb is None:
                    continue

                is_new = upsert_league_game(
                    sb,
                    arena_game_id=gid,
                    game_date=game["game_date"],
                    home_team_id=home_sb,
                    away_team_id=away_sb,
                    home_score=game["home_score"],
                    away_score=game["away_score"],
                    season_name=season_name,
                    league_id=league_id,
                )
                if is_new:
                    season_games_new += 1
                    total_games_new += 1
                else:
                    season_games_skip += 1
                    total_games_skipped += 1

            time.sleep(0.5)

        print(f"  → {season_games_new} new games, {season_games_skip} skipped")

    print(f"\n{'='*60}")
    print(f"DONE — {total_games_new} new league games, {total_games_skipped} skipped.")

    # Calculate and store ELO ratings
    calculate_elo(sb)


if __name__ == "__main__":
    main()
