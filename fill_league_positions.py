#!/usr/bin/env python3
"""
Fetch final league standings from DaySmart/Arena Sports API for each season
and fill in league_position in the Supabase seasons table.
"""
import os, time
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

def compute_position(brazuka_team_id):
    # Get league_id
    data = get(f"{BASE}/teams/{brazuka_team_id}?cache[save]=false&company=arenasports")
    league_id = str(data["data"]["attributes"]["league_id"])

    # Get all division teams
    data2 = get(f"{BASE}/leagues/{league_id}?include=teams&company=arenasports")
    teams = {i["id"]: i["attributes"]["name"] for i in data2.get("included", []) if i.get("type") == "teams"}
    if not teams:
        return None

    # Fetch each team's events and compute intra-division standings
    standings = defaultdict(lambda: {"w":0,"d":0,"l":0,"gf":0,"ga":0})
    seen_events = set()

    for tid in teams:
        url = (f"{BASE}/teams/{tid}?cache[save]=false"
               "&include=events.homeTeam,events.visitingTeam&company=arenasports")
        try:
            d = get(url)
        except:
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
            ht, vt = str(a.get("hteam_id","")), str(a.get("vteam_id",""))
            if ht not in teams or vt not in teams:
                continue
            standings[ht]["gf"] += hs; standings[ht]["ga"] += vs
            standings[vt]["gf"] += vs; standings[vt]["ga"] += hs
            if hs > vs:
                standings[ht]["w"] += 1; standings[vt]["l"] += 1
            elif hs < vs:
                standings[vt]["w"] += 1; standings[ht]["l"] += 1
            else:
                standings[ht]["d"] += 1; standings[vt]["d"] += 1
        time.sleep(0.3)

    if not standings:
        return None

    rows = sorted(standings.items(), key=lambda kv: (kv[1]["w"]*3+kv[1]["d"], kv[1]["gf"]-kv[1]["ga"]), reverse=True)
    total = len(rows)
    for pos, (tid, s) in enumerate(rows, 1):
        if tid == brazuka_team_id:
            mp = s["w"]+s["d"]+s["l"]
            pts = s["w"]*3+s["d"]
            return {"pos": pos, "total": total, "mp": mp, "w": s["w"], "d": s["d"], "l": s["l"],
                    "gd": s["gf"]-s["ga"], "pts": pts, "teams": teams, "rows": rows}
    return None

print("Fetching standings for all seasons...\n")

for brazuka_team_id, season_name in BRAZUKA_SEASONS:
    print(f"── {season_name}", end="  ", flush=True)
    try:
        result = compute_position(brazuka_team_id)
    except Exception as e:
        print(f"ERROR: {e}")
        time.sleep(0.5)
        continue

    if not result:
        print("no data")
        continue

    pos, total = result["pos"], result["total"]
    print(f"#{pos}/{total}  W={result['w']} D={result['d']} L={result['l']} GD={result['gd']:+d} Pts={result['pts']}")

    # Print full table
    for i, (tid, s) in enumerate(result["rows"], 1):
        mp = s["w"]+s["d"]+s["l"]
        pts = s["w"]*3+s["d"]
        marker = " ←" if tid == brazuka_team_id else ""
        name = result["teams"].get(tid, tid)[:38]
        print(f"     {i:2d}. {name:38s} MP={mp} Pts={pts}{marker}")

    # Update Supabase
    existing = sb.table("seasons").select("id").eq("name", season_name).eq("team_id", 1).execute()
    if existing.data:
        sid = existing.data[0]["id"]
        sb.table("seasons").update({"league_position": pos}).eq("id", sid).execute()
        print(f"     ✓ Saved to DB (season id={sid})")
    else:
        print(f"     ✗ Season '{season_name}' not found in Supabase")
    print()
    time.sleep(0.5)

print("Done.")
