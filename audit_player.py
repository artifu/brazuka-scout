#!/usr/bin/env python3
"""
Brazuka Scout — Player Audit Tool

Scans the full WhatsApp chat and finds every game window where a player
is mentioned, then cross-references with the database to show what's missing.

Usage:
  python3 audit_player.py "Mazza"
  python3 audit_player.py "Igor"
  python3 audit_player.py "Chico"          # searches aliases too
  python3 audit_player.py "Mazza" --add    # add missing appearances to DB
"""
import argparse
import os
import re
import sys

from dotenv import load_dotenv
load_dotenv(override=True)

from parser import parse_chat
from game_detector import detect_game_windows


CHAT_FILE = "_chat.txt"


def get_aliases(search_name: str):
    """Fetch canonical name + all aliases from the players table."""
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        rows = sb.table("players").select("id, canonical_name, aliases, display_name").execute().data

        needle = search_name.lower()
        for row in rows:
            all_names = [row["canonical_name"]] + (row["aliases"] or []) + ([row["display_name"]] if row["display_name"] else [])
            if any(needle in n.lower() or n.lower() in needle for n in all_names):
                print(f"  Found player: {row['canonical_name']} (id={row['id']})")
                if row["display_name"]:
                    print(f"  Display name: {row['display_name']}")
                print(f"  Aliases: {row['aliases']}")
                return row["id"], [n.lower() for n in all_names if n]
    except Exception as e:
        print(f"  (Could not fetch aliases from DB: {e})")
    return None, [search_name.lower()]


def get_registered_game_ids(player_id):
    """Return set of game_ids already in the appearances table for this player."""
    if not player_id:
        return set()
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        rows = sb.table("appearances").select("game_id").eq("player_id", player_id).execute().data
        return {r["game_id"] for r in rows}
    except Exception as e:
        print(f"  (Could not fetch appearances: {e})")
        return set()


def get_game_id_for_date(game_date_str: str, opponent: str):
    """Look up the game_id in the DB by date (and optionally opponent)."""
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        rows = sb.table("games").select("id, opponent").eq("game_date", game_date_str).execute().data
        if not rows:
            return None
        if len(rows) == 1:
            return rows[0]["id"]
        # Multiple games on same date — try to match opponent
        for row in rows:
            if opponent and opponent.lower() in (row["opponent"] or "").lower():
                return row["id"]
        return rows[0]["id"]  # fallback
    except Exception:
        return None


# ── Signup list detection ─────────────────────────────────────────────────────

# A message is a "signup list" if it has at least 3 numbered entries
_LIST_ENTRY = re.compile(r'^\d+[\.\)]\s*\S', re.MULTILINE)
_MIN_ENTRIES = 3


def is_signup_list(text: str) -> bool:
    """Return True if the message looks like a numbered signup list."""
    return len(_LIST_ENTRY.findall(text)) >= _MIN_ENTRIES


def extract_names_from_list(text: str) -> list[str]:
    """
    Extract player name tokens from each numbered line of a signup list.
    Returns lowercase strings for each entry (e.g. ['joao b', 'sese', 'ratt']).
    """
    names = []
    for line in text.splitlines():
        m = re.match(r'^\d+[\.\)]\s*(.+)', line.strip())
        if m:
            raw = m.group(1).strip()
            # Strip WhatsApp @mention formatting: @⁨Name⁩ → Name
            raw = re.sub(r'@[⁨~]*(.*?)[⁩]', r'\1', raw).strip()
            # Strip zero-width / non-printable chars that WhatsApp injects
            raw = re.sub(r'[\u2060\u200b\u200c\u200d\uFEFF\u2063]', '', raw).strip()
            # Strip trailing modifiers like "(L)", "+1", "✅", "❓"
            raw = re.sub(r'\s*[\(\+✅❓🤔].*$', '', raw).strip().lower()
            if raw:
                names.append(raw)
    return names


def alias_in_names(aliases: list[str], names: list[str]) -> bool:
    """
    Return True if any alias matches any name in the extracted list.

    Rules (in priority order):
    1. Exact match: alias == name
    2. Alias is a strict suffix of name (handles "joao b" matching "joao barros")
    3. Name is a suffix of alias (handles "mazza" matching "marcelo mazza")

    We deliberately avoid simple substring to prevent "marcelo" matching alias
    "marcelo mazza" (which would confuse Marcelo D with Mazza).
    """
    for alias in sorted(aliases, key=len, reverse=True):  # longest alias first
        for name in names:
            if alias == name:
                return True
            # name starts with alias as a whole word: "mazza bandido" matches alias "mazza"
            if name.startswith(alias) and (len(name) == len(alias) or name[len(alias)] in ' +-✅'):
                return True
            # alias starts with name as a whole word: "joao b" in list matches alias "joao barros"
            if alias.startswith(name) and (len(alias) == len(name) or alias[len(name)] in ' +-'):
                return True
    return False


def find_last_signup_list(messages) -> tuple:
    """
    Scan messages (chronological order) and return the text of the LAST
    signup list found, plus a flag indicating whether any list was found at all.
    """
    last_list = None
    for m in messages:
        if is_signup_list(m.text):
            last_list = m.text
    return last_list, last_list is not None


# ── Fallback: mention-based (for old seasons without formal lists) ─────────────

def player_in_goal_report(text: str, aliases: list[str]) -> bool:
    """Return True if the message is a post-game goal report mentioning the player."""
    text_lower = text.lower()
    for alias in aliases:
        alias_esc = re.escape(alias)
        if re.search(
            r'(?:gol\s+d[oa]\s+' + alias_esc
            + r'|\d\s*(?:gol|do|da)\s+' + alias_esc
            + r'|' + alias_esc + r'\s+marcou'
            + r'|\d\s*' + alias_esc + r')',
            text_lower,
        ):
            return True
    return False


def check_window(messages, aliases) -> tuple:
    """
    Main logic:
    1. Try to find the last signup list → check if player is in it.
    2. If no formal list exists (early seasons), fall back to goal report mentions.

    Returns: (found, method, evidence_messages)
      method: 'signup_list' | 'goal_report' | 'no_list_fallback'
    """
    last_list, has_list = find_last_signup_list(messages)

    if has_list:
        names = extract_names_from_list(last_list)
        if alias_in_names(aliases, names):
            return True, "signup_list", []
        # List found but player not in it → definitely didn't play (via this method)
        return False, "signup_list", []

    # No formal list → fall back to goal report search
    goal_msgs = [m for m in messages if player_in_goal_report(m.text, aliases)]
    if goal_msgs:
        return True, "goal_report", goal_msgs

    return False, "no_list", []


def add_appearance(player_id: int, canonical_name: str, game_id: int) -> bool:
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        sb.table("appearances").insert({
            "game_id": game_id,
            "player": canonical_name,
            "player_id": player_id,
        }).execute()
        return True
    except Exception as e:
        print(f"    ⚠️  Could not insert: {e}")
        return False


def audit(search_name: str, add_missing: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"  PLAYER AUDIT: {search_name}")
    print(f"{'='*60}\n")

    # ── 1. Resolve aliases ────────────────────────────────────────
    print("Looking up player in DB…")
    player_id, aliases = get_aliases(search_name)
    print()

    # ── 2. Load chat and game windows ─────────────────────────────
    print("Parsing chat…")
    messages = parse_chat(CHAT_FILE)
    windows = detect_game_windows(messages)
    print(f"  {len(messages):,} messages | {len(windows)} game windows\n")

    # ── 3. Get already-registered appearances ─────────────────────
    registered_ids = get_registered_game_ids(player_id)

    # ── 4. Scan each window using last-signup-list logic ─────────────
    raw_found = []
    for w in windows:
        all_msgs = w.pre_game_messages + w.post_game_messages
        found, method, evidence = check_window(all_msgs, aliases)
        if found:
            raw_found.append((w, method, evidence))

    # ── 4b. Deduplicate: same game_id = same game ─────────────────
    # Windows without a game_id are deduplicated by 7-day proximity
    from datetime import timedelta
    seen_game_ids: set = set()
    seen_dates: list = []
    found_windows = []
    for w, method, evidence in sorted(raw_found, key=lambda x: x[0].game_date):
        date_str = w.game_date.strftime("%Y-%m-%d")
        game_id = get_game_id_for_date(date_str, w.opponent)

        if game_id is not None:
            if game_id in seen_game_ids:
                continue
            seen_game_ids.add(game_id)
        else:
            # No game_id: skip if we saw a close date already (within 7 days)
            too_close = any(abs((w.game_date - d).days) <= 7 for d in seen_dates)
            if too_close:
                continue
            seen_dates.append(w.game_date)

        found_windows.append((w, method, evidence, game_id))

    # ── 5. Report ─────────────────────────────────────────────────
    print(f"Found {len(found_windows)} game windows where '{search_name}' played:\n")

    in_db = 0
    missing = []
    method_counts: dict[str, int] = {}

    for w, method, evidence, game_id in sorted(found_windows, key=lambda x: x[0].game_date):
        date_str = w.game_date.strftime("%Y-%m-%d")
        is_registered = game_id in registered_ids if game_id else False

        method_counts[method] = method_counts.get(method, 0) + 1
        status = "✅ in DB" if is_registered else "❌ MISSING"
        label = {"signup_list": "📋", "goal_report": "⚽", "no_list": "🔍"}.get(method, "")
        if is_registered:
            in_db += 1
        else:
            missing.append((w, game_id))

        opp = w.opponent if w.opponent and w.opponent != "Unknown" else "?"
        print(f"  {date_str}  vs {opp:<22} [{status}] {label} (game_id={game_id})")

        # Show evidence for goal reports (signup list is self-explanatory)
        if evidence:
            for m in evidence[:2]:
                snippet = m.text[:120].replace("\n", " ")
                print(f"    → [{m.sender}] {snippet}")
        print()

    print(f"{'─'*60}")
    print(f"  In DB    : {in_db}")
    print(f"  Missing  : {len(missing)}")
    print(f"  Total    : {len(found_windows)}")
    print(f"\n  Detection method breakdown:")
    for m, c in method_counts.items():
        label = {"signup_list": "📋 Last signup list", "goal_report": "⚽ Goal report", "no_list": "🔍 Fallback"}.get(m, m)
        print(f"    {label:<28} {c}")
    print(f"{'─'*60}\n")

    # ── 6. Optionally add missing appearances ─────────────────────
    if missing and add_missing:
        if not player_id:
            print("⚠️  Can't add appearances — player not found in DB (no player_id).")
            return

        # Get canonical name
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        row = sb.table("players").select("canonical_name").eq("id", player_id).single().execute()
        canonical_name = row.data["canonical_name"]

        added = 0
        skipped = 0
        for w, game_id in missing:  # type: ignore[assignment]
            if not game_id:
                print(f"  ⚠️  {w.game_date.strftime('%Y-%m-%d')} vs {w.opponent} — game not in DB, skipping")
                skipped += 1
                continue
            ok = add_appearance(player_id, canonical_name, game_id)
            if ok:
                print(f"  ✅ Added: {w.game_date.strftime('%Y-%m-%d')} vs {w.opponent}")
                added += 1

        print(f"\n  Added {added} appearances ({skipped} skipped — game not in DB)\n")
    elif missing and not add_missing:
        print("  Run with --add to insert missing appearances into the DB.\n")


def main():
    parser = argparse.ArgumentParser(description="Audit player appearances from WhatsApp chat")
    parser.add_argument("player", help="Player name or nickname to search for")
    parser.add_argument("--add", action="store_true", help="Add missing appearances to the DB")
    args = parser.parse_args()
    audit(args.player, add_missing=args.add)


if __name__ == "__main__":
    main()
