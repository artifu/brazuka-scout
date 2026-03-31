#!/usr/bin/env python3
"""
Migration 002 — Populate opponent_id in games + team_id in elo_ratings.

Run AFTER executing migrations/001_opponent_ids.sql in the Supabase SQL Editor.

Steps:
  1. Upsert all known opponent teams into the `teams` table (with aliases)
  2. Build alias → team_id lookup map
  3. Patch games.opponent_id for every game row
  4. Patch elo_ratings.team_id for every elo_ratings row

Usage:
  python migrations/002_populate_opponent_ids.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load .env from the project root (one level up from migrations/)
load_dotenv(Path(__file__).parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Canonical team registry ──────────────────────────────────────────────────
#
# Format: { "canonical_name": { "aliases": [...], "division": "...", "notes": "..." } }
#
# Rules:
#   - canonical_name = the "best" / most complete version of the name
#   - aliases = every other spelling/version seen in games.opponent or elo_ratings.team_name
#   - division = their home division (if known)
#   - notes = anything worth remembering (name history, rivalry, etc.)
#
# HOW TO ADD A MERGE LATER:
#   Find the team entry, add the old name to its aliases list, re-run this script.
#   The script is fully idempotent — safe to run multiple times.

TEAMS = [
    # ── Teams with confirmed aliases ──────────────────────────────────────────
    {
        "name": "Advil United",
        "aliases": ["Advil"],
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Axolotls",
        "aliases": ["Axolots"],          # typo seen in early data
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Jäger FC",
        "aliases": ["Jager FC"],          # umlaut missing in some entries
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Kernel FC",
        "aliases": ["Kernel F.C."],
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Slower than we look",
        "aliases": ["Slower Than We Look"],  # capitalisation variant
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Manchest-hair United FC",
        "aliases": ["Man Chest Hair United"],  # same pun, different spelling
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Do it again!",
        "aliases": ["Do it again! (RED) Thur Men's D1"],  # cross-div game
        "division": "Tuesday Men's D1",
        "notes": "Sometimes played as cross-division fixture (Thursday Men's D1 slot)",
    },
    {
        "name": "Husar",
        "aliases": ["Husar (Tues Men's C2)"],
        "division": "Tuesday Men's C2",
    },
    {
        "name": "The Great Indoors",
        "aliases": ["The Great Indoors (Thurs Men's D2)"],
        "division": "Thursday Men's D2",
    },
    {
        "name": "Un Réal 2",
        "aliases": [
            "Un Real",
            "Un Réal 2 - Boys are back in town",
            "Un Réal 2 - Boys are back",
        ],
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Chaos",
        "aliases": ["Chaos!"],
        "division": "Tuesday Men's D1",
    },
    {
        "name": "Cookie",
        "aliases": ["Team Cookie"],
        "division": "Tuesday Men's D1",
    },

    # ── Teams kept separate pending confirmation ───────────────────────────────
    # BB 2.0 and Blackfoot Ballers might be the same team — left separate until confirmed.
    # To merge: add "BB 2.0" to Blackfoot's aliases (or vice-versa) and re-run.
    {
        "name": "BB 2.0",
        "aliases": [],
        "notes": "Possible former name of Blackfoot Ballers — confirm before merging",
    },
    {
        "name": "Blackfoot Ballers",
        "aliases": [],
        "division": "Tuesday Men's D1",
        "notes": "Rivals. Changed name at some point — possibly to BB 2.0 or another name",
    },

    # ── Cross-division opponents (brought in by league to fill fixture slots) ──
    {
        "name": "Desipack",
        "aliases": ["Desipack (RED) Thur's Mens D1"],
        "division": "Thursday Men's D1",
        "notes": "Cross-division fixture (Thu D1 team playing in our Tue D1 slot)",
    },
    {
        "name": "Liquer Pool FC",
        "aliases": ["Liquer Pool FC (RED) Thurs C2"],
        "division": "Thursday Men's C2",
        "notes": "Cross-division fixture",
    },
    {
        "name": "Kernkraft 450",
        "aliases": ["Kernkraft 450 Thurs Men's C2 (RED)"],
        "division": "Thursday Men's C2",
        "notes": "Cross-division fixture",
    },

    # ── All other opponents (no known aliases) ────────────────────────────────
    {"name": "404 FC"},
    {"name": "Foden's Army", "division": "Tuesday Men's D1"},
    {"name": "Good Vibes"},
    {"name": "Tech Support"},
    {"name": "Troncos FC", "division": "Tuesday Men's D1"},
    {"name": "The Nelk Boys", "division": "Tuesday Men's D1"},
    {"name": "AO Let's Grow", "aliases": ["AO Let\u2019s Grow"]},  # curly apostrophe variant
    {"name": "Amazon Chime FC"},
    {"name": "Arsenull", "division": "Tuesday Men's D1"},
    {"name": "Bad Vibes"},
    {"name": "Barracudas", "division": "Tuesday Men's D1"},
    {"name": "Biblioteca Boiz", "division": "Tuesday Men's D1"},
    {"name": "Blue Horseshoes"},
    {"name": "Boomers", "division": "Tuesday Men's D1"},
    {"name": "Borscht United", "division": "Tuesday Men's D1"},
    {"name": "Casa Real HT"},
    {"name": "Chavorrucos FC"},
    {"name": "Crouch Potatoes", "division": "Tuesday Men's D1"},
    {"name": "Defiant FC"},
    {"name": "Diesel Daddies", "division": "Tuesday Men's D1"},
    {"name": "Dirty Dozen"},
    {"name": "Dirty Highlanders"},
    {"name": "Dribblers FC"},
    {"name": "EC Soccer Team", "division": "Tuesday Men's D1"},
    {"name": "Edge Delta", "division": "Tuesday Men's D1"},
    {"name": "FC #!bash", "division": "Tuesday Men's D1"},
    {"name": "FC Allegro"},
    {"name": "FC Jinro", "division": "Tuesday Men's D1"},
    {"name": "FC Twente One"},
    {"name": "FC Unathlético"},
    {"name": "Faceball", "division": "Tuesday Men's D1"},
    {"name": "Flaccid Dad Bods"},
    {"name": "Forcados F.C.", "aliases": ["Forçados F.C."]},  # cedilla variant in elo_ratings
    {"name": "Forever DA"},
    {"name": "Frappe FC"},
    {"name": "Fresh Start FC", "division": "Tuesday Men's D1"},
    {"name": "Fuchester United", "division": "Tuesday Men's D1"},
    {"name": "Goal Diggers", "division": "Tuesday Men's D1"},
    {"name": "Golazo"},
    {"name": "Got One Good Sub", "division": "Tuesday Men's D1"},
    {"name": "Green Cheetah Dads", "division": "Tuesday Men's D1"},
    {"name": "Half Boiled Eggs"},
    {
        "name": "Half Boiled Eggs / Pipe Dream (double header)",
        "notes": "Special double-header entry — treat as a single game record",
    },
    {"name": "Immune to Defense"},
    {"name": "Initech"},
    {"name": "Injury Reserve", "division": "Tuesday Men's D1"},
    {"name": "Ivanhoe Thursdays FC", "division": "Thursday"},
    {"name": "Jus 4 Kix", "division": "Tuesday Men's D1"},
    {"name": "KOMPAS", "division": "Tuesday Men's D1"},
    {"name": "Kenny Bell FC", "division": "Tuesday Men's D1"},
    {"name": "Kharkiv Football Club"},
    {"name": "Kroos Control", "division": "Tuesday Men's D1"},
    {
        "name": "Latin Heat",
        "notes": "Moved to Division C",
    },
    {"name": "LivePerson"},
    {"name": "Magma", "division": "Tuesday Men's D1"},
    {"name": "Matcha FC", "division": "Tuesday Men's D1"},
    {"name": "Mid Field Crisis", "division": "Tuesday Men's D1"},
    {"name": "Mocha FC", "division": "Tuesday Men's D1"},
    {"name": "Mochinut"},
    {"name": "Momentum", "division": "Tuesday Men's D1"},
    {"name": "My Chemical Bromance"},
    {"name": "Name That Strikes Sphere"},
    {"name": "Net Flicks", "division": "Tuesday Men's D1"},
    {"name": "Newbeebee FC", "division": "Tuesday Men's D1"},
    {"name": "Niupi"},
    {"name": "No Tactics, Just Vibes", "division": "Tuesday Men's D1"},
    {"name": "Pipe Dream"},
    {"name": "Real Mandrink"},
    {"name": "Real SoSoBad", "division": "Tuesday Men's D1"},
    {"name": "Rocket Shots II"},
    {"name": "SanBar"},
    {"name": "Schedule Chickens"},
    {"name": "Seattle Americans"},
    {"name": "Seattle Gents", "division": "Tuesday Men's D1"},
    {"name": "Seattle Sperm Bank"},
    {"name": "Seattle Techs United", "division": "Tuesday Men's D1"},
    {"name": "Semi-Pro Conductors", "division": "Tuesday Men's D1"},
    {"name": "Show me da Mane"},
    {"name": "Sitting Ducks", "division": "Tuesday Men's D1"},
    {"name": "Stone"},
    {"name": "Strangers United"},
    {"name": "Suburban Ninjas"},
    {"name": "Supermokh FC", "division": "Tuesday Men's D1"},
    {"name": "The Kwisatz Headerach", "division": "Tuesday Men's D1"},
    {"name": "The Mighty Molars"},
    {"name": "The Roaring Eagles"},
    {"name": "The Usual Suspects", "division": "Tuesday Men's D1"},
    {"name": "Tuesday Gold", "division": "Tuesday Men's D1"},
    {"name": "Tuesday Men's D1 House Team", "division": "Tuesday Men's D1"},
    {"name": "VR Mafia", "division": "Tuesday Men's D1"},
    {"name": "Wolves"},
    {"name": "magniFC", "division": "Tuesday Men's D1"},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def build_alias_map(teams_in_db: list[dict]) -> dict[str, int]:
    """
    Returns { any_name_or_alias_lowercase: team_id }
    for every team currently in the DB.
    """
    mapping = {}
    for t in teams_in_db:
        mapping[t["name"].lower()] = t["id"]
        for alias in t.get("aliases") or []:
            mapping[alias.lower()] = t["id"]
    return mapping


def upsert_teams() -> dict[str, int]:
    """Insert/update all teams in TEAMS registry. Returns alias → id map."""
    print("── Upserting teams ───────────────────────────────────────────")

    # Keep Brazuka (id=1) and Receba (id=2) — only add opponents
    existing = {t["name"]: t for t in sb.table("teams").select("*").execute().data}

    inserted = updated = skipped = 0
    for entry in TEAMS:
        name     = entry["name"]
        aliases  = entry.get("aliases", [])
        division = entry.get("division")
        notes    = entry.get("notes")

        if name in existing:
            # Update aliases/division/notes if changed
            row = existing[name]
            patch = {}
            current_aliases = set(row.get("aliases") or [])
            new_aliases = current_aliases | set(aliases)
            if new_aliases != current_aliases:
                patch["aliases"] = sorted(new_aliases)
            if division and row.get("division") != division:
                patch["division"] = division
            if notes and row.get("notes") != notes:
                patch["notes"] = notes

            if patch:
                sb.table("teams").update(patch).eq("id", row["id"]).execute()
                updated += 1
                print(f"  UPDATED  {name}")
            else:
                skipped += 1
        else:
            sb.table("teams").insert({
                "name": name,
                "aliases": aliases,
                "division": division,
                "notes": notes,
                "active": True,
            }).execute()
            inserted += 1
            print(f"  INSERTED {name}")

    print(f"\n  → {inserted} inserted, {updated} updated, {skipped} unchanged")

    # Reload and build alias map
    all_teams = sb.table("teams").select("*").execute().data
    return build_alias_map(all_teams)


def patch_games(alias_map: dict[str, int]):
    """Set games.opponent_id based on games.opponent text."""
    print("\n── Patching games.opponent_id ───────────────────────────────")

    games = sb.table("games").select("id, opponent, opponent_id").limit(5000).execute().data
    ok = missing = already_set = 0

    for g in games:
        opp = (g["opponent"] or "").strip()
        team_id = alias_map.get(opp.lower())

        if team_id is None:
            print(f"  ⚠️  NO MATCH  game_id={g['id']:4d}  opponent={opp!r}")
            missing += 1
            continue

        if g["opponent_id"] == team_id:
            already_set += 1
            continue

        sb.table("games").update({"opponent_id": team_id}).eq("id", g["id"]).execute()
        ok += 1

    print(f"\n  → {ok} patched, {already_set} already correct, {missing} unmatched")
    if missing:
        print("  ↳ Add missing names to TEAMS registry and re-run this script.")


def patch_elo_ratings(alias_map: dict[str, int]):
    """Set elo_ratings.team_id based on elo_ratings.team_name."""
    print("\n── Patching elo_ratings.team_id ─────────────────────────────")

    rows = sb.table("elo_ratings").select("id, team_name, team_id").limit(500).execute().data
    ok = missing = already_set = 0

    for r in rows:
        team_name = (r["team_name"] or "").strip()
        team_id   = alias_map.get(team_name.lower())

        if team_id is None:
            # elo_ratings includes teams from all leagues — only warn if it looks
            # like a Brazuka opponent (i.e. league = 'brazuka')
            print(f"  ⚠️  NO MATCH  elo_id={r['id']:4d}  team={team_name!r}")
            missing += 1
            continue

        if r["team_id"] == team_id:
            already_set += 1
            continue

        sb.table("elo_ratings").update({"team_id": team_id}).eq("id", r["id"]).execute()
        ok += 1

    print(f"\n  → {ok} patched, {already_set} already correct, {missing} unmatched")


def verify(alias_map: dict[str, int]):
    """Quick sanity check after migration."""
    print("\n── Verification ──────────────────────────────────────────────")
    games = sb.table("games").select("id, opponent, opponent_id").limit(5000).execute().data
    no_id = [g for g in games if g["opponent_id"] is None]
    pct   = 100 * (1 - len(no_id) / len(games)) if games else 0
    print(f"  games with opponent_id set: {len(games)-len(no_id)}/{len(games)} ({pct:.1f}%)")

    elo = sb.table("elo_ratings").select("id, team_name, team_id").limit(500).execute().data
    no_eid = [r for r in elo if r["team_id"] is None]
    pct2  = 100 * (1 - len(no_eid) / len(elo)) if elo else 0
    print(f"  elo_ratings with team_id set: {len(elo)-len(no_eid)}/{len(elo)} ({pct2:.1f}%)")

    if no_id:
        print(f"\n  Games still missing opponent_id ({len(no_id)}):")
        for g in no_id[:20]:
            print(f"    game_id={g['id']}  opponent={g['opponent']!r}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Migration 002 — Populate opponent_id + team_id\n")

    alias_map = upsert_teams()
    patch_games(alias_map)
    patch_elo_ratings(alias_map)
    verify(alias_map)

    print("\nDone! Re-run at any time — script is fully idempotent.")
