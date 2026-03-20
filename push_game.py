#!/usr/bin/env python3
"""Push a single extracted game directly to Supabase (no AI needed)."""
import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lwfbvoewpzutowasyyoz.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx3ZmJ2b2V3cHp1dG93YXN5eW96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzk1ODA0MCwiZXhwIjoyMDg5NTM0MDQwfQ.YJDp0wQYczXqfH1inJ3gIl3_4wqay8XzIdgKQKt8cU4")

game = {
    "game_date": "2026-03-17",
    "opponent": "Newbeebee FC",
    "home_or_away": "home",
    "result": "win",
    "score_brazuka": 7,
    "score_opponent": None,
    "yellow_cards": [],
    "red_cards": [],
    "notable_moments": [
        "Árbitro de vôlei (terrible referee)",
        "Goleiro playing great with girlfriend watching from stands",
        "Sergio brought cake (bolo) to the game",
    ],
    "confidence": "high",
}

goals = [
    {"player": "Rato", "count": 2, "notes": None},
    {"player": "Arthur", "count": 1, "notes": None},
    {"player": "Luigi", "count": 2, "notes": None},
    {"player": "Kuster", "count": 2, "notes": None},
]

players = ["Sergio", "Arthur", "Kuster", "Ranieri", "Adelmo", "Alexis", "Roberto", "Lucas", "Luigi", "Pablo"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

resp = sb.table("games").upsert(game, on_conflict="game_date").execute()
game_id = resp.data[0]["id"]
print(f"Game saved: id={game_id}")

sb.table("goals").delete().eq("game_id", game_id).execute()
sb.table("goals").insert([{"game_id": game_id, **g} for g in goals]).execute()
print(f"Goals saved: {[g['player'] for g in goals]}")

sb.table("appearances").delete().eq("game_id", game_id).execute()
sb.table("appearances").upsert([{"game_id": game_id, "player": p} for p in players], on_conflict="game_id,player").execute()
print(f"Appearances saved: {players}")

print("\nDone! Check Supabase table editor to verify.")
