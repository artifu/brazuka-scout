#!/usr/bin/env python3
"""
Fetch every intra-division game for all Brazuka seasons from the Arena Sports API
and populate the division_games table.
"""
import os, time, re
from pathlib import Path
from collections import defaultdict
import requests

for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

BASE = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1"
HEADERS = {"Accept": "application/vnd.api+json", "User-Agent": "Mozilla/5.0"}

BRAZUKA_SEASONS = [
    ("215810", "Winter I 2025"),
    ("214012", "Fall 2025"),
    ("213250", "Summer 2025"),
    ("211302", "Spring 2025"),
    ("208137", "Winter II 2025"),
    ("205470", "Winter I 2024"),
    ("204186", "Fall 2024"),
    ("202652", "Summer 2024"),
    ("200446", "Spring 2024"),
    ("196948", "Winter II 2024"),
    ("194228", "Winter I 2023"),
    ("193131", "Fall 2023"),
    ("190812", "Summer 2023"),
    ("187808", "Spring 2023"),
    ("184892", "Winter II 2023"),
    ("181899", "Winter I 2022"),
    ("181297", "Fall 2022"),
    ("177686", "Spring 2022"),
    ("174858", "Winter II 2022"),
    ("172413", "Winter I 2021"),
]

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def clean_name(name):
    """Strip Arena Sports division suffixes."""
    name = re.sub(r"\s+(?:NP(?:GK)?\s*\d*|N\dP)\s*$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\((?:Tues?\.?\s+Men'?s?\s+D\d*|Tue\s+Men'?s?\s+D\d*|M|S)\)\s*(?:\([MS]\)\s*)?$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\([MS]\)\s*$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s+NP\s*\d*$", "", name, flags=re.IGNORECASE).strip()
    return name

total_inserted = 0
total_skipped = 0

for brazuka_team_id, season_name in BRAZUKA_SEASONS:
    print(f"── {season_name}", end="  ", flush=True)

    # Get league_id from Brazuka's team record
    try:
        data = get(f"{BASE}/teams/{brazuka_team_id}?cache[save]=false&company=arenasports")
        league_id = str(data["data"]["attributes"]["league_id"])
    except Exception as e:
        print(f"ERROR getting team: {e}")
        continue

    # Get all division team IDs + names
    try:
        data2 = get(f"{BASE}/leagues/{league_id}?include=teams&company=arenasports")
    except Exception as e:
        print(f"ERROR getting league: {e}")
        continue

    teams = {
        i["id"]: clean_name(i["attributes"]["name"])
        for i in data2.get("included", []) if i.get("type") == "teams"
    }
    if not teams:
        print("no teams")
        continue

    # Fetch events for each team, deduplicate by event id
    seen_events = set()
    games = []

    for tid in teams:
        url = (f"{BASE}/teams/{tid}?cache[save]=false"
               "&include=events.homeTeam,events.visitingTeam&company=arenasports")
        try:
            d = get(url)
        except Exception as e:
            time.sleep(0.3)
            continue

        included = d.get("included", [])
        events_by_id = {i["id"]: i for i in included if i.get("type") == "events"}
        ev_refs = d["data"].get("relationships", {}).get("events", {}).get("data", [])

        for ref in ev_refs:
            eid = ref["id"]
            if eid in seen_events:
                continue
            seen_events.add(eid)
            ev = events_by_id.get(eid)
            if not ev:
                continue
            a = ev["attributes"]
            hs, vs = a.get("home_score"), a.get("visiting_score")
            if hs is None or vs is None:
                continue
            try:
                hs, vs = int(hs), int(vs)
            except:
                continue
            ht = str(a.get("hteam_id", ""))
            vt = str(a.get("vteam_id", ""))
            if ht not in teams or vt not in teams:
                continue  # skip inter-division fixtures

            game_date = (a.get("start_date") or a.get("start", ""))[:10] or None

            games.append({
                "season_name": season_name,
                "game_date":   game_date,
                "home_team":   teams[ht],
                "away_team":   teams[vt],
                "home_score":  hs,
                "away_score":  vs,
            })
        time.sleep(0.25)

    print(f"{len(games)} games", end="  ")

    # Upsert into division_games
    inserted = skipped = 0
    for g in games:
        try:
            result = sb.table("division_games").upsert(g, on_conflict="season_name,game_date,home_team,away_team").execute()
            inserted += 1
        except Exception as e:
            skipped += 1

    print(f"✓ {inserted} upserted  {skipped} errors")
    total_inserted += inserted
    total_skipped += skipped
    time.sleep(0.5)

print(f"\nDone — {total_inserted} rows upserted, {total_skipped} errors.")
