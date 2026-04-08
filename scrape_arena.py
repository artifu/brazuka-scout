#!/usr/bin/env python3
"""
scrape_arena.py — Import Brazuka game results from Arena Sports API into Supabase.

Fetches all Brazuka seasons from the DaySmart Recreation API and upserts
completed game results into the `games` table in Supabase.

Usage:
  SUPABASE_SERVICE_KEY=$(grep SUPABASE_SERVICE_KEY .env | cut -d= -f2) \
  SUPABASE_URL=$(grep SUPABASE_URL .env | cut -d= -f2) \
  python3 scrape_arena.py
"""

import os
import re
import sys
import time

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

# ── Brazuka team IDs per season ───────────────────────────────────────────────
# (team_id, season_label, approx_start_date)
BRAZUKA_SEASONS = [
    ("221537", "Soccer, Adult Spring 2026 (MAG)",       "2026-04-07"),
    ("219258", "Soccer, Adult Winter 2025-26 (MAG)",    "2025-12-01"),
    ("215810", "Soccer, Adult Winter I 2025 (MAG)",    "2025-09-29"),
    ("214012", "Soccer, Adult Fall 2025 (MAG)",         "2025-08-11"),
    ("213250", "Soccer, Adult Summer 2025 (MAG)",       "2025-06-30"),
    ("211302", "Soccer, Adult Spring 2025 (MAG)",       "2025-04-07"),
    ("208137", "Soccer, Adult Winter II 2025 (MAG)",    "2025-01-06"),
    ("205470", "Soccer, Adult Winter I 2024 (MAG)",     "2024-09-30"),
    ("204186", "Soccer, Adult Fall 2024 (MAG)",         "2024-08-19"),
    ("202652", "Soccer, Adult Summer 2024 (MAG)",       "2024-07-08"),
    ("200446", "Soccer, Adult Spring 2024 (MAG)",       "2024-04-08"),
    ("196948", "Soccer, Adult Winter II 2024 (MAG)",    "2024-01-08"),
    ("194228", "Soccer, Adult Winter I 2023 (MAG)",     "2023-10-09"),
    ("193131", "Soccer, Adult Fall 2023 (MAG)",         "2023-08-28"),
    ("190812", "Soccer, Adult Summer 2023 (MAG)",       "2023-07-17"),
    ("187808", "Soccer, Adult Spring 2023 (MAG)",       "2023-04-17"),
    ("184892", "Soccer, Adult Winter II 2023 (MAG)",    "2023-01-09"),
    ("181899", "Soccer, Adult Winter I 2022 (MAG)",     "2022-10-10"),
    ("181297", "Soccer, Adult Fall 2022 (MAG)",         "2022-08-25"),
    ("177686", "Soccer, Adult Spring 2022 (MAG)",       "2022-04-18"),
    ("174858", "Soccer, Adult Winter ll 2022 (MAG)",    "2022-01-17"),  # lowercase 'l'
    ("172413", "Soccer, Adult Winter I 2021 (MAG)",     "2021-10-11"),
]

# ── Season name normalisation ─────────────────────────────────────────────────
# Maps API season label → our standard short name stored in Supabase
_SEASON_NAME_MAP: dict[str, str] = {}
for _team_id, _label, _start in BRAZUKA_SEASONS:
    # Strip leading "Soccer, Adult " and trailing " (MAG)"
    short = re.sub(r'^Soccer,\s+Adult\s+', '', _label)
    short = re.sub(r'\s*\(MAG\)\s*$', '', short)
    # Fix the lowercase-L variant: "Winter ll" → "Winter II"
    short = re.sub(r'\bll\b', 'II', short)
    _SEASON_NAME_MAP[_label] = short.strip()

BRAZUKA_TEAM_ID_SUPABASE = 1  # teams.id for 'Brazuka US'


# ── Auto-discovery: follow copiedToTeams chain ────────────────────────────────

def _date_to_season_label(start_date: str) -> str:
    """Convert a start date to a season label, e.g. '2026-04-07' → 'Spring 2026'."""
    from datetime import date
    d = date.fromisoformat(start_date[:10])
    m, y = d.month, d.year
    if m in (4, 5):
        name = f"Spring {y}"
    elif m in (6, 7, 8):
        name = f"Summer {y}"
    elif m in (9, 10):
        name = f"Fall {y}"
    elif m == 11:
        name = f"Winter I {y}"
    else:                          # Dec or Jan-Mar
        base = y if m == 12 else y - 1
        name = f"Winter {base}-{str(base + 1)[-2:]}"
    return f"Soccer, Adult {name} (MAG)"


def discover_newer_seasons(known_ids: set[str]) -> list[tuple[str, str, str]]:
    """
    Follow the copiedToTeams chain from the most recent known team ID and
    return any new (team_id, season_label, start_date) tuples not yet in the list.
    Safe to call every run — no-ops if nothing new.
    """
    # Start from the most recent known season (first entry in BRAZUKA_SEASONS)
    frontier = [BRAZUKA_SEASONS[0][0]]
    new_entries: list[tuple[str, str, str]] = []

    while frontier:
        team_id = frontier.pop()
        url = (
            f"{BASE_URL}/teams/{team_id}"
            "?cache[save]=false&include=copiedToTeams&company=arenasports"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        copies = (
            data.get("data", {})
            .get("relationships", {})
            .get("copiedToTeams", {})
            .get("data", []) or []
        )
        included = {i["id"]: i for i in data.get("included", [])}

        for ref in copies:
            new_id = ref["id"]
            if new_id in known_ids:
                continue

            # Get start_date for the new team
            team_info = included.get(new_id, {}).get("attributes", {})
            start_raw = team_info.get("start_date", "")
            start_date = start_raw[:10] if start_raw else ""
            if not start_date:
                # Fetch full team data to get start_date
                try:
                    r2 = requests.get(
                        f"{BASE_URL}/teams/{new_id}?company=arenasports",
                        headers=HEADERS, timeout=15,
                    )
                    start_date = r2.json().get("data", {}).get("attributes", {}).get("start_date", "")[:10]
                except Exception:
                    start_date = ""

            label = _date_to_season_label(start_date) if start_date else f"Soccer, Adult Season {new_id} (MAG)"
            new_entries.append((new_id, label, start_date))
            known_ids.add(new_id)
            frontier.append(new_id)  # keep following the chain

    return new_entries


# Extend BRAZUKA_SEASONS with any newly discovered seasons at import time
_known_ids = {tid for tid, _, _ in BRAZUKA_SEASONS}
_discovered = discover_newer_seasons(_known_ids)
if _discovered:
    print(f"[auto-discover] Found {len(_discovered)} new season(s): {[d[0] for d in _discovered]}")
    BRAZUKA_SEASONS = _discovered + BRAZUKA_SEASONS
    # Rebuild name map with new entries
    for _team_id, _label, _start in _discovered:
        short = re.sub(r'^Soccer,\s+Adult\s+', '', _label)
        short = re.sub(r'\s*\(MAG\)\s*$', '', short)
        short = re.sub(r'\bll\b', 'II', short)
        _SEASON_NAME_MAP[_label] = short.strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_opponent(name: str) -> str:
    """
    Strip Arena Sports division/status suffixes from opponent names.
    Handles patterns like:
      - "(Tues Men's D)"  "(Tue Men's D1)"  "(Tues Men's D2)"  "(Tues Men's D3)"
      - "(M)"  "(S)"
      - Trailing junk like " NPGK", " N1P", " NP 2" after the paren
    """
    # First remove trailing tokens that are NOT parenthesised (e.g. "NPGK", "N1P", "NP 2")
    name = re.sub(r"\s+(?:NP(?:GK)?\s*\d*|N\dP)\s*$", "", name, flags=re.IGNORECASE).strip()
    # Then remove division paren suffix (possibly followed by status suffix like " (S)")
    name = re.sub(
        r"\s*\((?:Tues?\.?\s+Men'?s?\s+D\d*|M|S)\)\s*(?:\([MS]\)\s*)?$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    # Final pass: remove lone (S) or (M) suffix if still present
    name = re.sub(r"\s*\([MS]\)\s*$", "", name, flags=re.IGNORECASE).strip()
    return name


def map_venue(facility_name) -> str:
    """Map facility name to 'Magnuson' or 'SODO'."""
    if not facility_name:
        return "Magnuson"
    name_lower = facility_name.lower()
    if "sodo" in name_lower:
        return "SODO"
    return "Magnuson"


def fetch_team_events(team_id: str) -> dict:
    """Fetch team data including events with home/away teams, facility, and summary."""
    url = (
        f"{BASE_URL}/teams/{team_id}"
        "?cache[save]=false"
        "&include=events.homeTeam,events.visitingTeam,"
        "events.resource.facility,events.resourceArea,events.summary"
        "&company=arenasports"
    )
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_events(data: dict, brazuka_team_id: str) -> list[dict]:
    """
    Parse the JSON:API response into a list of game dicts.
    Returns only completed games (both scores present).

    API notes (from inspection):
    - Scores are directly in event.attributes (home_score / visiting_score)
    - Field name is in the related resource's attributes.name
    - resourceArea relationship is always null; resource_area_id attr is 0
    - hteam_id / vteam_id in attributes match the relationship ids (strings in rels, ints in attrs)
    """
    included = data.get("included", [])

    # Build lookup maps
    teams_by_id: dict[str, dict] = {}
    resources_by_id: dict[str, dict] = {}  # resource_id → {name, facility_name}

    for item in included:
        t = item.get("type", "")
        iid = item.get("id", "")
        attrs = item.get("attributes", {})
        rels = item.get("relationships", {})

        if t == "teams":
            teams_by_id[iid] = {"name": attrs.get("name", "")}
        elif t == "resources":
            # Facility name comes from facility relationship or can be inferred from resource name
            facility_rel = rels.get("facility", {}).get("data")
            facility_included = None
            if facility_rel:
                fid = facility_rel.get("id")
                for inc in included:
                    if inc.get("type") == "facilities" and inc.get("id") == fid:
                        facility_included = inc.get("attributes", {}).get("name", "")
                        break
            resources_by_id[iid] = {
                "name": attrs.get("name", "").strip(),
                "facility_name": facility_included,
            }

    # Build event lookup from included
    events_by_id: dict[str, dict] = {}
    for item in included:
        if item.get("type") == "events":
            events_by_id[item["id"]] = item

    # Events list from main team's relationships
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

        # Game date: use the 'start' attribute (local time) to get date
        # 'start_date' attr is "2025-09-30T00:00:00" — take first 10 chars
        start_date_str = attrs.get("start_date") or attrs.get("start", "")
        game_date = start_date_str[:10] if start_date_str else None
        if not game_date:
            continue

        # Scores are directly in attributes (not in a separate summary)
        home_score = attrs.get("home_score")
        visiting_score = attrs.get("visiting_score")

        # Skip unplayed games
        if home_score is None or visiting_score is None:
            continue
        try:
            home_score = int(home_score)
            visiting_score = int(visiting_score)
        except (TypeError, ValueError):
            continue

        # Team IDs — hteam_id / vteam_id in attributes (integers)
        # Also available as string IDs in relationships
        hteam_id_int = attrs.get("hteam_id")
        vteam_id_int = attrs.get("vteam_id")
        hteam_str = str(hteam_id_int) if hteam_id_int is not None else None
        vteam_str = str(vteam_id_int) if vteam_id_int is not None else None

        is_home = (hteam_str == brazuka_team_id)
        opp_id = vteam_str if is_home else hteam_str

        # Get opponent name from included teams
        opp_info = teams_by_id.get(opp_id, {})
        opp_name = clean_opponent(opp_info.get("name", "Unknown"))

        score_brazuka = home_score if is_home else visiting_score
        score_opponent = visiting_score if is_home else home_score

        if score_brazuka > score_opponent:
            result = "win"
        elif score_brazuka < score_opponent:
            result = "loss"
        else:
            result = "draw"

        # Resource → field name and venue
        resource_ref = rels.get("resource", {}).get("data")
        resource_id = resource_ref.get("id") if resource_ref else None
        # Fall back to resource_id from attributes (int → str)
        if not resource_id and attrs.get("resource_id"):
            resource_id = str(attrs["resource_id"])

        resource_info = resources_by_id.get(resource_id, {}) if resource_id else {}
        field = resource_info.get("name", "")
        venue = map_venue(resource_info.get("facility_name") or field)

        games.append({
            "game_date": game_date,
            "opponent": opp_name,
            "home_or_away": "home" if is_home else "away",
            "score_brazuka": score_brazuka,
            "score_opponent": score_opponent,
            "result": result,
            "venue": venue,
            "field": field,
            "scorers_known": False,
        })

    return games


def get_or_create_season(sb, season_label: str, start_date: str) -> int:
    """Find or create a season in Supabase. Returns the season id."""
    short_name = _SEASON_NAME_MAP.get(season_label, season_label)

    existing = (
        sb.table("seasons")
        .select("id")
        .eq("name", short_name)
        .eq("team_id", BRAZUKA_TEAM_ID_SUPABASE)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    # Create new season
    resp = (
        sb.table("seasons")
        .insert({
            "name": short_name,
            "team_id": BRAZUKA_TEAM_ID_SUPABASE,
            "start_date": start_date,
        })
        .execute()
    )
    return resp.data[0]["id"]


def upsert_game(sb, game: dict, season_id: int):
    """
    Insert game if not present. Returns (is_new, display_str).
    Skips (does not overwrite) if game_date + opponent already exists.
    Uses both fields to handle double-headers (two games on the same date).
    """
    # Check for existing by date AND opponent (handles double-headers)
    existing = (
        sb.table("games")
        .select("id,opponent,result,score_brazuka,score_opponent")
        .eq("game_date", game["game_date"])
        .eq("team_id", BRAZUKA_TEAM_ID_SUPABASE)
        .ilike("opponent", f"%{game['opponent'].split()[0]}%")
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        return False, f"{game['game_date']} vs {row['opponent']}"

    # Insert
    sb.table("games").insert({
        "game_date": game["game_date"],
        "opponent": game["opponent"],
        "home_or_away": game["home_or_away"],
        "result": game["result"],
        "score_brazuka": game["score_brazuka"],
        "score_opponent": game["score_opponent"],
        "scorers_known": game["scorers_known"],
        "venue": game["venue"],
        "field": game["field"],
        "team_id": BRAZUKA_TEAM_ID_SUPABASE,
        "season_id": season_id,
    }).execute()

    result_icon = {"win": "W", "loss": "L", "draw": "D"}.get(game["result"], "?")
    score_str = f"{game['score_brazuka']}-{game['score_opponent']}"
    return True, f"{game['game_date']} vs {game['opponent']} — {result_icon} {score_str}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    total_new = 0
    total_skipped = 0

    for team_id, season_label, start_date in BRAZUKA_SEASONS:
        short_name = _SEASON_NAME_MAP.get(season_label, season_label)
        print(f"\n{'─'*60}")
        print(f"Season: {short_name}  (team_id={team_id})")

        # Fetch events from API
        try:
            data = fetch_team_events(team_id)
        except requests.HTTPError as e:
            print(f"  [ERROR] HTTP {e.response.status_code} — skipping season")
            time.sleep(0.5)
            continue
        except Exception as e:
            print(f"  [ERROR] {e} — skipping season")
            time.sleep(0.5)
            continue

        games = parse_events(data, team_id)
        print(f"  Completed games from API: {len(games)}")

        if not games:
            time.sleep(0.5)
            continue

        # Ensure season exists in Supabase
        season_id = get_or_create_season(sb, season_label, start_date)

        # Sort chronologically
        games.sort(key=lambda g: g["game_date"])

        season_new = 0
        season_skipped = 0
        for game in games:
            is_new, display = upsert_game(sb, game, season_id)
            if is_new:
                print(f"  [NEW]   {display}")
                season_new += 1
                total_new += 1
            else:
                print(f"  [SKIP]  {display}")
                season_skipped += 1
                total_skipped += 1

        print(f"  → {season_new} new, {season_skipped} skipped")
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"DONE — {total_new} new games inserted, {total_skipped} skipped (already existed).")


if __name__ == "__main__":
    main()
