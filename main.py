#!/usr/bin/env python3
"""
Brazuka Scout - CLI entry point.

Usage:
  python main.py import <chat_file>     # parse chat + extract + save to DB
  python main.py games                  # list all games
  python main.py stats                  # player goal rankings
  python main.py h2h <opponent>         # head-to-head record vs opponent
  python main.py record                 # overall W/L/D
"""
import json
import os
import sys
from pathlib import Path

from database import init_db, save_all_games, get_all_games, get_player_stats, get_head_to_head, get_overall_record
from extractor import extract_all_games
from game_detector import detect_game_windows
from parser import parse_chat, filter_recent


def cmd_import(chat_file: str, days: int = 90):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set.")
        print("   Run: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    print(f"📂 Parsing {chat_file}...")
    msgs = parse_chat(chat_file)
    recent = filter_recent(msgs, days=days)
    print(f"   Total messages: {len(msgs):,} | Last {days} days: {len(recent):,}")

    print("\n🔍 Detecting game windows...")
    windows = detect_game_windows(recent)
    print(f"   Found {len(windows)} games")

    print("\n🤖 Extracting game data with AI (this may take a minute)...")
    results = extract_all_games(windows)

    print("\n💾 Saving to database...")
    init_db()
    save_all_games(results)

    print("\n✅ Done! Run 'python main.py stats' to see player rankings.")


def cmd_games():
    games = get_all_games()
    if not games:
        print("No games found. Run 'python main.py import <chat_file>' first.")
        return

    print(f"\n{'─'*70}")
    print(f"{'DATE':<12} {'OPPONENT':<25} {'H/A':<5} {'RESULT':<8} {'SCORE':<8} {'CONF'}")
    print(f"{'─'*70}")
    for g in games:
        score = f"{g['score_brazuka']}-{g['score_opponent']}" \
            if g['score_brazuka'] is not None else "?"
        result_icon = {"win": "✅", "loss": "❌", "draw": "🟡", "unknown": "❓"}.get(g["result"], "❓")
        print(
            f"{g['game_date']:<12} "
            f"{g['opponent'][:24]:<25} "
            f"{g['home_or_away'][:4]:<5} "
            f"{result_icon} {g['result']:<6} "
            f"{score:<8} "
            f"{g['confidence']}"
        )
    print(f"{'─'*70}")
    print(f"Total: {len(games)} games\n")


def cmd_stats():
    stats = get_player_stats()
    if not stats:
        print("No stats found. Run 'python main.py import <chat_file>' first.")
        return

    print(f"\n{'─'*50}")
    print(f"{'PLAYER':<25} {'GOALS':>6} {'GAMES':>6}")
    print(f"{'─'*50}")
    for i, p in enumerate(stats, 1):
        bar = "⚽" * min(p["goals"], 10)
        print(f"{i:>2}. {p['player']:<22} {p['goals']:>6} {p['appearances']:>6}  {bar}")
    print(f"{'─'*50}\n")


def cmd_h2h(opponent: str):
    record = get_head_to_head(opponent)
    total = record["wins"] + record["losses"] + record["draws"]
    if total == 0:
        print(f"No games found against '{opponent}'")
        return

    print(f"\nHead-to-head vs {opponent}:")
    print(f"  ✅ Wins:   {record['wins']}")
    print(f"  ❌ Losses: {record['losses']}")
    print(f"  🟡 Draws:  {record['draws']}")
    print(f"  Total:    {total}\n")


def cmd_record():
    record = get_overall_record()
    total = record["total"]
    if total == 0:
        print("No games found.")
        return

    win_pct = (record["wins"] / total * 100) if total else 0
    print(f"\n🏆 Brazuka Overall Record")
    print(f"   ✅ Wins:   {record['wins']}")
    print(f"   ❌ Losses: {record['losses']}")
    print(f"   🟡 Draws:  {record['draws']}")
    print(f"   Win rate: {win_pct:.0f}%\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "import":
        if len(sys.argv) < 3:
            print("Usage: python main.py import <chat_file>")
            sys.exit(1)
        cmd_import(sys.argv[2])
    elif cmd == "games":
        cmd_games()
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "h2h":
        if len(sys.argv) < 3:
            print("Usage: python main.py h2h <opponent_name>")
            sys.exit(1)
        cmd_h2h(sys.argv[2])
    elif cmd == "record":
        cmd_record()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
