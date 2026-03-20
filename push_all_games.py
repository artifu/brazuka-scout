#!/usr/bin/env python3
"""Push all historical game data to Supabase."""
import os
from supabase import create_client
from player_normalizer import PlayerNormalizer

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lwfbvoewpzutowasyyoz.supabase.co")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
norm = PlayerNormalizer()

# Lookup IDs
BRAZUKA_TEAM_ID = sb.table('teams').select('id').eq('name', 'Brazuka US').single().execute().data['id']
WINTER_2026_ID  = sb.table('seasons').select('id').eq('name', 'Winter 2026').single().execute().data['id']

GAMES = [
    {
        "game": {
            "game_date": "2025-12-23", "opponent": "Jus 4 Kix", "home_or_away": "away",
            "result": "win", "score_brazuka": 7, "score_opponent": 4,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["Started 1-0 with a man down", "Guest player Sebastião from Guarulhos was MVP", "Wesley also joined as guest"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "NW Magnuson Field",
        },
        "goals": [],
        "players": ["Matheus", "Ranieri Filho", "Pablo", "Arthur Koefender", "Cleiton Moura", "Cleiton Castro"],
    },
    {
        "game": {
            "game_date": "2025-12-30", "opponent": "Arsenull", "home_or_away": "home",
            "result": "loss", "score_brazuka": 6, "score_opponent": 8,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["750 shots, 30 on goal, 24 on their keeper — still lost", "Their goalkeeper (Alto) helped our team by scoring OG", "Alto later moved to Alaska"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "SODO", "field": "Main SODO Field",
        },
        "goals": [],
        "players": ["Ranieri Filho", "Lucas Claro", "Pablo", "Kuster", "Arthur Koefender"],
    },
    {
        "game": {
            "game_date": "2026-01-06", "opponent": "FC Jinro", "home_or_away": "away",
            "result": "loss", "score_brazuka": 5, "score_opponent": 6,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["OG by Alexis", "OG by Pablo", "Opponent scored a stunning Thierry Henry-style goal from a tight angle"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "SW Magnuson Field",
        },
        "goals": [],
        "players": ["Alexis", "Sergio Filho", "Kuster", "Matheus", "Arthur Mendes", "Pablo", "Daniel Tedesco", "Caio Scofield"],
    },
    {
        "game": {
            "game_date": "2026-01-13", "opponent": "Axolotls", "home_or_away": "home",
            "result": "loss", "score_brazuka": 3, "score_opponent": 6,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["Daniel tried a free kick that went nowhere — entered the Arena Sports hall of shame", "Luigi and Daniel later played for Axolotls in a follow-up game (Luigi 3 goals, Daniel 1 OG)"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "SODO", "field": "Main SODO Field",
        },
        "goals": [],
        "players": ["Caio Scofield", "Ranieri Filho", "Matheus", "Sergio Filho", "Pablo", "Adelmo", "Daniel Tedesco", "Roberto Bandarra", "Luigi Tedesco", "Alexis"],
    },
    {
        "game": {
            "game_date": "2026-01-20", "opponent": "Matcha FC", "home_or_away": "away",
            "result": "loss", "score_brazuka": 7, "score_opponent": 8,
            "scorers_known": True, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["8th consecutive loss", "Daniel Tedesco injured his ankle", "Both Tedesco brothers rule proposed: only 1 Tedesco allowed on field at a time"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "SW Magnuson Field",
        },
        "goals": [
            {"player": "Sergio Filho", "count": 4, "notes": None},
            {"player": "Kuster",       "count": 2, "notes": None},
            {"player": "Matheus",      "count": 1, "notes": None},
        ],
        "players": ["Adelmo", "Sergio Filho", "Lucas Claro", "Daniel Tedesco", "Matheus", "Luigi Tedesco", "Pablo", "Kuster", "Caio Scofield"],
    },
    {
        "game": {
            "game_date": "2026-01-27", "opponent": "Momentum", "home_or_away": "home",
            "result": "win", "score_brazuka": 6, "score_opponent": 1,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["MVP: Daniel Tedesco", "Dominant win — 'passing the tractor'"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "NW Magnuson Field",
        },
        "goals": [],
        "players": ["Arthur Mendes", "Kuster", "Alexis", "Lucas Claro", "Matheus", "Cleiton Moura", "Cleiton Castro"],
    },
    {
        "game": {
            "game_date": "2026-02-06", "opponent": "Kenny Bell FC", "home_or_away": "away",
            "result": "win", "score_brazuka": 7, "score_opponent": 3,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": [],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "SW Magnuson Field",
        },
        "goals": [],
        "players": ["Caio Scofield", "Lucas Claro", "Cleiton Castro", "Arthur Mendes", "Sergio Filho", "Alexis"],
    },
    {
        "game": {
            "game_date": "2026-02-17", "opponent": "Borscht United", "home_or_away": "home",
            "result": "win", "score_brazuka": 7, "score_opponent": 5,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["Both Tedesco brothers didn't play — Brazuka won", "Caio: 'Obrigado Tedescos, vocês fizeram toda a diferença (por não terem ido)'"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "SODO", "field": "Main SODO Field",
        },
        "goals": [],
        "players": ["Caio Scofield", "Kuster", "Sergio Filho", "Ranieri Filho", "Adelmo", "Lucas Claro", "Pablo", "Cleiton Castro", "Cleiton Moura"],
    },
    {
        "game": {
            "game_date": "2026-03-10", "opponent": "Borscht United", "home_or_away": "home",
            "result": "win", "score_brazuka": None, "score_opponent": None,
            "scorers_known": False, "yellow_cards": [], "red_cards": [],
            "notable_moments": ["Win by forfeit — Borscht United did not show up"],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "SW Magnuson Field",
        },
        "goals": [],
        "players": ["Arthur Mendes", "Lucas Claro", "Adelmo", "Luigi Tedesco"],
    },
    {
        "game": {
            "game_date": "2026-03-17", "opponent": "Newbeebee FC", "home_or_away": "home",
            "result": "win", "score_brazuka": 7, "score_opponent": 4,
            "scorers_known": True, "yellow_cards": [], "red_cards": [],
            "notable_moments": [
                "Árbitro de vôlei (terrible referee)",
                "Goalkeeper played brilliantly with his gothic girlfriend watching from the stands",
                "Sergio brought cake (bolo) to the game",
            ],
            "confidence": "high",
            "team_id": BRAZUKA_TEAM_ID, "season_id": WINTER_2026_ID,
            "venue": "Magnuson", "field": "SE Magnuson Field",
        },
        "goals": [
            {"player": "Rafael Franco",  "count": 2, "notes": None},
            {"player": "Arthur Mendes",  "count": 1, "notes": None},
            {"player": "Luigi Tedesco",  "count": 2, "notes": None},
            {"player": "Kuster",         "count": 2, "notes": None},
        ],
        "players": ["Sergio Filho", "Arthur Mendes", "Kuster", "Ranieri Filho", "Adelmo", "Alexis", "Roberto Bandarra", "Lucas Claro", "Luigi Tedesco", "Pablo"],
    },
]


def push_game(game_data, goals_data, player_names):
    # Upsert game
    resp = sb.table("games").upsert(game_data, on_conflict="game_date").execute()
    game_id = resp.data[0]["id"]

    # Clear existing
    sb.table("goals").delete().eq("game_id", game_id).execute()
    sb.table("appearances").delete().eq("game_id", game_id).execute()

    # Insert goals with player_id
    if goals_data:
        goals_rows = []
        for g in goals_data:
            player_id = norm.resolve_id(g["player"])
            canonical = norm.resolve(g["player"])
            goals_rows.append({
                "game_id": game_id,
                "player": canonical["canonical_name"] if canonical else g["player"],
                "player_id": player_id,
                "count": g["count"],
                "notes": g.get("notes"),
            })
        sb.table("goals").insert(goals_rows).execute()

    # Insert appearances with player_id
    if player_names:
        app_rows = []
        for name in player_names:
            player_id = norm.resolve_id(name)
            canonical = norm.resolve(name)
            app_rows.append({
                "game_id": game_id,
                "player": canonical["canonical_name"] if canonical else name,
                "player_id": player_id,
            })
        sb.table("appearances").upsert(app_rows, on_conflict="game_id,player").execute()

    return game_id


print("Pushing all games to Supabase...\n")
for entry in GAMES:
    game_id = push_game(entry["game"], entry["goals"], entry["players"])
    g = entry["game"]
    score = f"{g['score_brazuka']}-{g['score_opponent']}" if g["score_brazuka"] is not None else "forfeit"
    icon = "✅" if g["result"] == "win" else "❌"
    goals_str = ", ".join(f"{g['player']} x{g['count']}" for g in entry["goals"]) or "—"
    print(f"{icon} {g['game_date']} vs {g['opponent']:20} {score}  goals: {goals_str}  (id={game_id})")

print(f"\nDone! {len(GAMES)} games pushed.")
