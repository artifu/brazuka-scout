#!/usr/bin/env python3
"""Mark Arthur Mendes' ACL return game in the DB.

Timeline:
  - ACL surgery: ~Nov 3, 2023 (same week as Neymar's ACL operation)
  - First game back (RECEBA FC Thursday): ~Jun 27, 2024 (Arthur said Jul 11 was
    "tecnicamente o terceiro" game back, so informal return was ~Jun 27)
  - First Tuesday Brazuka league game back: game 170, Jul 23, 2024 vs Mocha FC (L 3-7)
    Confirmed by: Arthur was on waitlist and moved to confirmed on game day;
    Pablo joking after the loss: "Só uma coisa mudou, ou melhor, voltou! 😆"

This script:
  1. Adds Arthur's appearance to game 170 (idempotent)
  2. Updates game 170's notable_moments to record the ACL return
"""

import os
from pathlib import Path

for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
from player_normalizer import PlayerNormalizer
norm = PlayerNormalizer()

GAME_ID = 170  # Jul 23, 2024, Season 17 (Summer 2024), vs Mocha FC, L 3-7

# Resolve Arthur Mendes
pid, canonical = norm.resolve_or_flag("Arthur Mendes")
if pid is None:
    print("ERROR: could not resolve Arthur Mendes")
    raise SystemExit(1)

print(f"\n── Game {GAME_ID}: marking ACL return ──")

# Add appearance (idempotent)
existing = sb.table("appearances").select("id").eq("game_id", GAME_ID).eq("player_id", pid).execute()
if not existing.data:
    sb.table("appearances").insert({"game_id": GAME_ID, "player": canonical, "player_id": pid}).execute()
    print(f"  + appearance: {canonical} (game {GAME_ID})")
else:
    print(f"  = appearance already exists: {canonical} (game {GAME_ID})")

# Update notable_moments
# Fetch existing moments first to avoid overwriting
game = sb.table("games").select("notable_moments").eq("id", GAME_ID).execute()
existing_moments = game.data[0]["notable_moments"] if game.data and game.data[0].get("notable_moments") else []

acl_return_note = (
    "Arthur Mendes' first Tuesday Brazuka league game back after ACL surgery "
    "(surgery ~Nov 3, 2023, same week as Neymar's ACL; cleared to play ~Jul 2024). "
    "He had already played ~2-3 informal Thursday RECEBA FC games before this. "
    "Pablo joked after the 3-7 loss: 'Só uma coisa mudou, ou melhor, voltou!' "
    "(Only one thing changed — he returned!)"
)

# Only add if not already present
if not any("ACL" in m for m in (existing_moments or [])):
    new_moments = list(existing_moments or []) + [acl_return_note]
    sb.table("games").update({"notable_moments": new_moments}).eq("id", GAME_ID).execute()
    print(f"  ~ added ACL return note to game {GAME_ID} notable_moments")
else:
    print(f"  = ACL return note already present in game {GAME_ID}")

print("\n✅ ACL return marked.")
