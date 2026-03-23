#!/usr/bin/env python3
"""
Fetch every intra-division game for all Receba seasons from the Arena Sports API
and populate the division_games table with league='receba'.
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

RECEBA_SEASONS = [
    ("185442", "Winter II 2023"),
    ("188396", "Spring 2023"),
    ("191108", "Summer 2023"),
    ("193613", "Fall 2023"),
    ("194005", "Winter I 2024"),
    ("198056", "Winter II 2024"),
    ("200182", "Spring 2024"),
    ("202425", "Summer 2024"),
    ("204470", "Fall 2024"),
    ("205255", "Winter I 2025"),
    ("208368", "Winter II 2025"),
    ("213934", "Summer 2025"),
    ("215356", "Fall 2025"),
]

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def clean_name(name):
    name = re.sub(r"\s+(?:NP(?:GK)?\s*\d*|N\dP)\s*$", "", name, flags=re.IGNORECASE).strip()
    # Strip trailing " - ..." season tags FIRST (Arena Sports appends e.g. "- Aug 2023")
    name = re.sub(r"\s+-.*$", "", name).strip()
    # "(RED) Thur Men's D1" or "(Iss) Thur's Mens D" — venue tag before division
    # Day variants: Thur / Thurs / Thur's
    name = re.sub(
        r"\s*\([A-Za-z/]{2,7}\)\s+(?:Thur(?:'?s)?\.?\s+)?Men(?:s|'s)?\s+[CD]\d*\s*(?:\([MS]\))?\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # "Thurs Men's C2 (RED)" — venue tag after division
    name = re.sub(
        r"\s+Thur(?:'?s)?\.?\s+Men(?:s|'s)?\s+[CD]\d*\s*\([A-Za-z/]{2,7}\)\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # "(RED) Thurs C2" — no "Men's", just venue + day + division letter
    name = re.sub(
        r"\s*\([A-Za-z/]{2,7}\)\s+(?:Thur(?:'?s)?\.?\s+)?[CD]\d+\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # "(RED/ISS) Thur Men's D1" — dual venue
    name = re.sub(
        r"\s*\([A-Z]{2,4}/[A-Z]{2,4}\)\s+(?:Thurs?\.?\s+)?Men(?:s|'s)?\s+[CD]\d*\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    name = re.sub(r"\s*\([MS]\)\s*$", "", name, flags=re.IGNORECASE).strip()
    # Normalize known all-caps team names so they don't produce duplicates
    if name.upper() == "RECEBA FC":
        name = "Receba FC"
    return name

total_inserted = 0
total_skipped = 0

for receba_team_id, season_name in RECEBA_SEASONS:
    print(f"── {season_name}", end="  ", flush=True)

    try:
        data = get(f"{BASE}/teams/{receba_team_id}?cache[save]=false&company=arenasports")
        league_id = str(data["data"]["attributes"]["league_id"])
    except Exception as e:
        print(f"ERROR getting team: {e}")
        continue

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

    seen_events = set()
    games = []

    for tid in teams:
        url = (f"{BASE}/teams/{tid}?cache[save]=false"
               "&include=events.homeTeam,events.visitingTeam&company=arenasports")
        try:
            d = get(url)
        except Exception:
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
                continue

            game_date = (a.get("start_date") or a.get("start", ""))[:10] or None

            games.append({
                "season_name": season_name,
                "game_date":   game_date,
                "home_team":   teams[ht],
                "away_team":   teams[vt],
                "home_score":  hs,
                "away_score":  vs,
                "league":      "receba",
            })
        time.sleep(0.25)

    print(f"{len(games)} games", end="  ")

    inserted = skipped = 0
    for g in games:
        try:
            sb.table("division_games").upsert(g, on_conflict="season_name,game_date,home_team,away_team,league").execute()
            inserted += 1
        except Exception:
            skipped += 1

    print(f"✓ {inserted} upserted  {skipped} errors")
    total_inserted += inserted
    total_skipped += skipped
    time.sleep(0.5)

print(f"\nDone — {total_inserted} rows upserted, {total_skipped} errors.")
