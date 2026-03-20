#!/usr/bin/env python3
"""
Migrate Brazuka Scout data to Supabase.

Parses _chat.txt, extracts game data via Claude AI, and pushes to Supabase.

Usage:
  python migrate_to_supabase.py
"""
import json
import os
import sys
from supabase import create_client

from parser import parse_chat, filter_recent
from game_detector import detect_game_windows
from extractor import extract_all_games, GameResult

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_FILE = "_chat.txt"


def save_game_to_supabase(client, result: GameResult) -> int:
    """Upsert a game and its goals/appearances. Returns game id."""
    # Upsert game (conflict on game_date)
    game_data = {
        "game_date": result.game_date,
        "opponent": result.opponent,
        "home_or_away": result.home_or_away,
        "result": result.result,
        "score_brazuka": result.score_brazuka,
        "score_opponent": result.score_opponent,
        "yellow_cards": result.yellow_cards,
        "red_cards": result.red_cards,
        "notable_moments": result.notable_moments,
        "confidence": result.confidence,
    }
    resp = client.table("games").upsert(game_data, on_conflict="game_date").execute()
    game_id = resp.data[0]["id"]

    # Delete existing goals + appearances for this game (full replace)
    client.table("goals").delete().eq("game_id", game_id).execute()
    client.table("appearances").delete().eq("game_id", game_id).execute()

    # Insert goals
    if result.goals:
        goals_data = [
            {
                "game_id": game_id,
                "player": g.get("player", ""),
                "count": g.get("count", 1),
                "notes": g.get("notes"),
            }
            for g in result.goals
        ]
        client.table("goals").insert(goals_data).execute()

    # Insert appearances
    if result.players_confirmed:
        appearances_data = [
            {"game_id": game_id, "player": p}
            for p in result.players_confirmed
        ]
        client.table("appearances").upsert(appearances_data, on_conflict="game_id,player").execute()

    return game_id


def main():
    # Validate env
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    if not os.path.exists(CHAT_FILE):
        print(f"Chat file not found: {CHAT_FILE}")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Parsing {CHAT_FILE}...")
    msgs = parse_chat(CHAT_FILE)
    recent = filter_recent(msgs, days=90)
    print(f"  Total messages: {len(msgs):,} | Last 90 days: {len(recent):,}")

    print("\nDetecting game windows...")
    windows = detect_game_windows(recent)
    print(f"  Found {len(windows)} games")

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if limit:
        windows = windows[-limit:]
        print(f"  (limiting to last {limit} game(s))")

    print("\nExtracting game data with AI...")
    results = extract_all_games(windows)

    print(f"\nPushing {len(results)} games to Supabase...")
    for i, result in enumerate(results, 1):
        game_id = save_game_to_supabase(sb, result)
        score = f"{result.score_brazuka}-{result.score_opponent}" if result.score_brazuka is not None else "?"
        print(f"  [{i}/{len(results)}] {result.game_date} vs {result.opponent} — {result.result.upper()} {score} (id={game_id})")

    print(f"\nDone! {len(results)} games saved to Supabase.")


if __name__ == "__main__":
    main()
