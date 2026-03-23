#!/usr/bin/env python3
"""
scrape_receba.py — Import Receba FC game results from Arena Sports API into Supabase.

Fetches all Receba seasons from the DaySmart Recreation API and upserts
completed game results into the `games` table in Supabase (team_id=2).

Fields at Redmond:
  - "Main Redmond Field"  → venue=Redmond, field=Main
  - "Side Redmond Field"  → venue=Redmond, field=Side  (4-player lines, more brutal)
  - "LAX Redmond Field"   → venue=Redmond, field=LAX   (smaller field)
  - "Issaquah Field"      → venue=Issaquah

Usage:
  python3 scrape_receba.py
"""

import os
import re
import sys
import time
from pathlib import Path

import requests
from supabase import create_client

# ── Load .env ──────────────────────────────────────────────────────────────────
for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1"
HEADERS = {"Accept": "application/vnd.api+json", "User-Agent": "Mozilla/5.0"}

RECEBA_TEAM_ID_SUPABASE = 2  # teams.id for 'Receba FC'

# ── All Receba FC seasons at Redmond (Thursday league) ────────────────────────
# Seasons with confirmed game data (0-game "Wrong" registrations excluded).
# Season labels map to our standard short names stored in Supabase.
RECEBA_SEASONS = [
    ("185442", "Winter II 2023",  "2023-01-12"),  # earliest confirmed Thursday Redmond season
    ("188396", "Spring 2023",     "2023-04-13"),
    ("191108", "Summer 2023",     "2023-07-13"),
    ("193613", "Fall 2023",       "2023-08-31"),
    ("194005", "Winter I 2024",   "2023-10-12"),
    ("198056", "Winter II 2024",  "2024-01-08"),
    ("200182", "Spring 2024",     "2024-04-08"),
    ("202425", "Summer 2024",     "2024-07-08"),
    ("204470", "Fall 2024",       "2024-08-27"),
    ("205255", "Winter I 2025",   "2024-09-30"),
    ("208368", "Winter II 2025",  "2025-01-06"),
    ("213934", "Summer 2025",     "2025-07-07"),
    ("215356", "Fall 2025",       "2025-08-18"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_opponent(name: str) -> str:
    """Strip Arena Sports division/status suffixes from opponent names."""
    name = re.sub(r"\s+(?:NP(?:GK)?\s*\d*|N\dP)\s*$", "", name, flags=re.IGNORECASE).strip()
    # Remove Redmond/Issaquah/SODO venue+division suffixes: (RED) Thur Men's D1, (ISS) Thurs C2, etc.
    name = re.sub(
        r"\s*\([A-Z]{2,4}\)\s+(?:Thurs?\.?\s+)?Men[s']?\s+[CD]\d*\s*(?:\([MS]\))?\s*(?:-\s*\S+)?\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    name = re.sub(
        r"\s*\([A-Z]{2,4}/[A-Z]{2,4}\)\s+(?:Thurs?\.?\s+)?Men[s']?\s+[CD]\d*\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # Remove Tuesday division suffixes for mixed-league games
    name = re.sub(
        r"\s*\((?:Tues?\.?\s+Men'?s?\s+D\d*|M|S)\)\s*(?:\([MS]\)\s*)?$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    name = re.sub(r"\s*\([MS]\)\s*$", "", name, flags=re.IGNORECASE).strip()
    # Remove trailing " - AugSeason" suffixes
    name = re.sub(r"\s+-\s*(?:\w+\s*\d*\s*)?$", "", name).strip()
    return name


def map_venue(facility_name) -> str:
    """Map facility name to a short venue label."""
    if not facility_name:
        return "Redmond"
    fl = facility_name.lower()
    if "issaquah" in fl:
        return "Issaquah"
    if "sodo" in fl:
        return "SODO"
    if "magnuson" in fl or "mag" in fl:
        return "Magnuson"
    return "Redmond"


def fetch_team_events(team_id: str) -> dict:
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


def parse_events(data: dict, receba_team_id: str) -> list[dict]:
    """Parse JSON:API response into list of completed game dicts."""
    included = data.get("included", [])

    teams_by_id: dict[str, dict] = {}
    resources_by_id: dict[str, dict] = {}

    for item in included:
        t = item.get("type", "")
        iid = item.get("id", "")
        attrs = item.get("attributes", {})
        rels = item.get("relationships", {})

        if t == "teams":
            teams_by_id[iid] = {"name": attrs.get("name", "")}
        elif t == "resources":
            facility_rel = rels.get("facility", {}).get("data")
            facility_name = None
            if facility_rel:
                fid = facility_rel.get("id")
                for inc in included:
                    if inc.get("type") == "facilities" and inc.get("id") == fid:
                        facility_name = inc.get("attributes", {}).get("name", "")
                        break
            resources_by_id[iid] = {
                "name": attrs.get("name", "").strip(),
                "facility_name": facility_name,
            }

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

        start_date_str = attrs.get("start_date") or attrs.get("start", "")
        game_date = start_date_str[:10] if start_date_str else None
        if not game_date:
            continue

        home_score = attrs.get("home_score")
        visiting_score = attrs.get("visiting_score")
        if home_score is None or visiting_score is None:
            continue
        try:
            home_score = int(home_score)
            visiting_score = int(visiting_score)
        except (TypeError, ValueError):
            continue

        hteam_id_int = attrs.get("hteam_id")
        vteam_id_int = attrs.get("vteam_id")
        hteam_str = str(hteam_id_int) if hteam_id_int is not None else None
        vteam_str = str(vteam_id_int) if vteam_id_int is not None else None

        is_home = (hteam_str == receba_team_id)
        opp_id = vteam_str if is_home else hteam_str

        opp_info = teams_by_id.get(opp_id, {})
        opp_name = clean_opponent(opp_info.get("name", "Unknown"))

        score_receba = home_score if is_home else visiting_score
        score_opponent = visiting_score if is_home else home_score

        if score_receba > score_opponent:
            result = "win"
        elif score_receba < score_opponent:
            result = "loss"
        else:
            result = "draw"

        resource_ref = rels.get("resource", {}).get("data")
        resource_id = resource_ref.get("id") if resource_ref else None
        if not resource_id and attrs.get("resource_id"):
            resource_id = str(attrs["resource_id"])

        resource_info = resources_by_id.get(resource_id, {}) if resource_id else {}
        field_name = resource_info.get("name", "")
        facility = resource_info.get("facility_name")
        venue = map_venue(facility or field_name)

        games.append({
            "game_date": game_date,
            "opponent": opp_name,
            "home_or_away": "home" if is_home else "away",
            "score_brazuka": score_receba,
            "score_opponent": score_opponent,
            "result": result,
            "venue": venue,
            "field": field_name,
            "scorers_known": False,
        })

    return games


def get_or_create_season(season_name: str, start_date: str) -> int:
    existing = (
        sb.table("seasons")
        .select("id")
        .eq("name", season_name)
        .eq("team_id", RECEBA_TEAM_ID_SUPABASE)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    resp = (
        sb.table("seasons")
        .insert({
            "name": season_name,
            "team_id": RECEBA_TEAM_ID_SUPABASE,
            "start_date": start_date,
        })
        .execute()
    )
    return resp.data[0]["id"]


def upsert_game(game: dict, season_id: int):
    """Insert game if not already present. Returns (is_new, display_str)."""
    existing = (
        sb.table("games")
        .select("id,opponent,result")
        .eq("game_date", game["game_date"])
        .eq("team_id", RECEBA_TEAM_ID_SUPABASE)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        return False, f"{game['game_date']} vs {row['opponent']}"

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
        "team_id": RECEBA_TEAM_ID_SUPABASE,
        "season_id": season_id,
    }).execute()

    result_icon = {"win": "W", "loss": "L", "draw": "D"}.get(game["result"], "?")
    score_str = f"{game['score_brazuka']}-{game['score_opponent']}"
    field_note = f" [{game['field']}]" if game["field"] else ""
    return True, f"{game['game_date']} vs {game['opponent']} — {result_icon} {score_str}{field_note}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    total_new = 0
    total_skipped = 0

    for team_id, season_name, start_date in RECEBA_SEASONS:
        print(f"\n{'─'*60}")
        print(f"Season: {season_name}  (team_id={team_id})")

        try:
            data = fetch_team_events(team_id)
        except requests.HTTPError as e:
            print(f"  [ERROR] HTTP {e.response.status_code} — skipping")
            time.sleep(0.5)
            continue
        except Exception as e:
            print(f"  [ERROR] {e} — skipping")
            time.sleep(0.5)
            continue

        games = parse_events(data, team_id)
        print(f"  Completed games from API: {len(games)}")

        if not games:
            time.sleep(0.5)
            continue

        season_id = get_or_create_season(season_name, start_date)

        games.sort(key=lambda g: g["game_date"])

        season_new = 0
        season_skipped = 0
        for game in games:
            is_new, display = upsert_game(game, season_id)
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
    print(f"DONE — {total_new} new games inserted, {total_skipped} skipped.")


if __name__ == "__main__":
    main()
