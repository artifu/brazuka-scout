#!/usr/bin/env python3
"""
Auto-award badges based on scoring/assist records and season participation.
Run this after each game or whenever you want to refresh auto badges.

Game badges (accumulate per game):
  hattrick — 3+ goals in a single game
  poker    — exactly 4 goals in a single game
  manita   — 5+ goals in a single game
  garcom   — 3+ assists in a single game

Season badges (one per player per season, stored with season_id):
  champ_winter1_2024  — Winter I 2024 title (World Cup style)
  champ_winter2_2024  — Winter II 2024 title (Champions League style)
  champ_spring_2025   — Spring 2025 title (Copa style)
  champ_summer_2025   — Summer 2025 title (Ballon d'Or style)
  victus              — Summer 2024 shame season (0 wins)
"""
import os
from pathlib import Path

for line in (Path(__file__).parent / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# ── Ensure badge definitions exist ────────────────────────────────────────────
BADGE_DEFS = [
    # slug, name, description, icon (SVG filename slug), auto_rule
    ("hattrick",         "Hat Trick",            "Scored 3 or more goals in a single game",           "hattrick",         "hattrick"),
    ("poker",            "Poker",                "Scored exactly 4 goals in a single game",           "poker",            "poker"),
    ("manita",           "Manita",               "Scored 5 or more goals in a single game",           "manita",           "manita"),
    ("garcom",           "Garçom",               "Provided 3 or more assists in a single game",       "garcom",           "garcom"),
    ("champ_winter1_2024", "Winter I 2024 Champion",  "Division champion — Winter I 2024",           "champ_winter1_2024",  "season"),
    ("champ_winter2_2024", "Winter II 2024 Champion", "Division champion — Winter II 2024",          "champ_winter2_2024",  "season"),
    ("champ_spring_2025",  "Spring 2025 Champion",    "Division champion — Spring 2025",             "champ_spring_2025",   "season"),
    ("champ_summer_2025",  "Summer 2025 Champion",    "Division champion — Summer 2025 (perfect season)", "champ_summer_2025", "season"),
    ("victus",      "Victus",       "Survived Summer 2022 — the original 0-win shame season",    "victus",      "season"),
    ("victus_ii",   "Victus II",    "Survived Summer 2024 — 0 wins, they came back for more",   "victus_ii",   "season"),
    ("yellow_card", "Yellow Card",  "Received a yellow card",                                    "yellow_card", "manual"),
    ("blue_card",   "Blue Card",    "Received a blue card (2-minute suspension)",                "blue_card",   "manual"),
    ("injury",      "Tipo Ronaldo", "Suffered a significant injury mid-season",                  "injury",      "manual"),
    ("love_doping",    "Love Doping",    "Performs substantially better when loved ones are watching",    "love_doping",    "manual"),
    ("rat_trick",      "Rat Trick",      "Hattrick scored by Rat Franco — far harder than a regular one", "rat_trick",      "manual"),
    ("sitter_misser",  "Sitter Misser",  "Missed an unbelievable open goal",                              "sitter_misser",  "manual"),
    ("shoot_fofo",     "Shoot Fofo",     "Shoots with the force of a fluffy bedroom slipper",             "shoot_fofo",     "manual"),
    ("stylish_shorts", "Stylish Shorts", "Awarded for wearing the most fashionable shorts on the pitch",  "stylish_shorts", "manual"),
    ("sleepy_gus",     "Sleepy Gus",     "Consistently found napping on the pitch mid-game",              "sleepy_gus",     "manual"),
    ("cordiality",     "Cordiality",     "Never complains — the most civil player on the pitch",          "cordiality",     "manual"),
    ("little_roll",    "Little Roll",    "Attempted a nutmeg in their own defensive area",                "little_roll",    "manual"),
    ("tip_toe",        "Tip Toe",        "Master of the biquinho — delicate toe-poke technique",          "tip_toe",        "manual"),
    ("friend",         "Friend",         "O que importa são os amigos que fazemos no caminho",            "friend",         "manual"),
    ("orbit",          "Orbit",          "Kicked the ball so far NASA scientists cannot explain the physics", "orbit",       "manual"),
    ("hunger",         "Hunger",         "The idiot never passes the ball. Ever.",                           "hunger",         "manual"),
    ("famine",         "Famine",          "Seriously man, pass the ball. You dont need to shoot every single ball.", "famine",    "manual"),
    ("saci",           "Saci",           "Excellence in using both legs — the mischievous ambipedal trickster", "saci",       "manual"),
    ("glass_bones",    "Glass Bones",    "Showing great body resistance to impacts",                          "glass_bones", "manual"),
    ("chapada",        "Chapada",        "Scored a goal directly from a free kick",                           "chapada",     "manual"),
    ("midas_heel",  "Midas Heel",   "Calcanhar de Midas — whenever he uses his heel, the play turns into shit", "midas_heel", "manual"),
    ("levanta",     "Levanta",      "Chora não! Levanta Pai — immortalised by a son on the sidelines",           "levanta",    "manual"),
    ("sbqe",        "SBQE",         "Só Bate Quem Erra",                                                         "sbqe",       "manual"),
    ("punch_up",    "Punch Up",     "Steamrolled a higher-division team — punched above our weight",              "punch_up",   "manual"),
]
for slug, name, description, icon, auto_rule in BADGE_DEFS:
    sb.table("badges").upsert({
        "slug": slug, "name": name, "description": description,
        "icon": icon, "auto_rule": auto_rule,
    }, on_conflict="slug").execute()

# ── Season ID map (from seasons table) ────────────────────────────────────────
# These IDs are stable — confirmed from the database.
CHAMPION_SEASONS = [
    (15, "champ_winter1_2024", "Winter I 2024 Champion"),
    (26, "champ_winter2_2024", "Winter II 2024 Champion"),
    (24, "champ_spring_2025",  "Spring 2025 Champion"),
    (23, "champ_summer_2025",  "Summer 2025 Champion"),
]
VICTUS_SEASON_ID    =  9  # Summer 2022 — original 0-win shame season
VICTUS_II_SEASON_ID = 17  # Summer 2024 — victus return

# Manual awards: players confirmed present but with no recorded goals/assists
# Format: (player_id, badge_slug, game_id, season_id, notes)
MANUAL_AWARDS = [
    (41, "victus",      None,  9,    "Confirmed present Summer 2022"),            # Mazza
    (31, "victus_ii",   None, 17,    "Played last game of Summer 2024 after injury"),  # Arthur
    (61, "injury",      None, None,  "Lucas Guilherme — serious knee injury"),
    (55, "love_doping", None, None,  "Alexis (keeper) — performs better when loved ones watch"),
    # Rat Trick — Rafa Franco hattricks (game_ids confirmed from goals table)
    (33, "rat_trick",   143,  None,  "Rat Franco hattrick"),
    (33, "rat_trick",   178,  None,  "Rat Franco hattrick"),
    (33, "rat_trick",   198,  None,  "Rat Franco hattrick"),
    # Sitter Misser — Rafa Franco x6
    (33, "sitter_misser",   2, None,  "Classic sitter miss"),
    (33, "sitter_misser", 135, None,  "Classic sitter miss"),
    (33, "sitter_misser", 136, None,  "Classic sitter miss"),
    (33, "sitter_misser", 137, None,  "Classic sitter miss"),
    (33, "sitter_misser", 122, None,  "Classic sitter miss"),
    (33, "sitter_misser", 138, None,  "Classic sitter miss"),
    # Sitter Misser — Mazza x6
    (41, "sitter_misser", 136, None,  "Classic Mazza sitter"),
    (41, "sitter_misser", 137, None,  "Classic Mazza sitter"),
    (41, "sitter_misser", 138, None,  "Classic Mazza sitter"),
    (41, "sitter_misser", 177, None,  "Classic Mazza sitter"),
    (41, "sitter_misser", 242, None,  "Classic Mazza sitter"),
    (41, "sitter_misser", 254, None,  "Classic Mazza sitter"),
    # Shoot Fofo
    (36, "shoot_fofo",  None, None,  "Daniel Tedesco — fluffy shots"),
    (80, "shoot_fofo",  None, None,  "Axel — fluffy shots"),
    # Stylish Shorts
    (37, "stylish_shorts", None, None,  "Pablo — most stylish fashion shorts"),
    # Sleepy Gus
    (62, "sleepy_gus",  None, None,  "Gustavo Bittencourt — sleeping on the pitch"),
    # Cordiality — Cleiton Castro x5
    (50, "cordiality", 204, None,  "Never complained"),
    (50, "cordiality", 205, None,  "Never complained"),
    (50, "cordiality", 207, None,  "Never complained"),
    (50, "cordiality", 195, None,  "Never complained"),
    (50, "cordiality", 197, None,  "Never complained"),
    # Little Roll
    (48, "little_roll", None, None,  "Joao Barros — nutmeg in defensive area"),
    (49, "little_roll", None, None,  "Joao Pinto — nutmeg in defensive area"),
    (50, "little_roll", None, None,  "Cleiton Castro — nutmeg in defensive area"),
    # Tip Toe
    (56, "tip_toe",    None, None,  "Rafa Mattos — master of the biquinho"),
    # Friend
    (49, "friend",     None, None,  "Joao Pinto — o que importa são os amigos que fazemos no caminho"),
    # Orbit
    (36, "orbit",      None, None,  "Daniel Tedesco — NASA-defying shot trajectory"),
    # Hunger (never passes)
    (34, "hunger",     None, None,  "Kuster — never passes"),
    (57, "hunger",     None, None,  "Matheus Waterfall — never passes"),
    (38, "hunger",     None, None,  "Sergio Filho — never passes"),
    # Famine (Kuster only)
    (34, "famine", None, None, "Kuster — the pass button exists. That one only shoots."),
    # Saci
    (42, "saci",       None, None,  "Caio Scofield — ambipedal excellence"),
    # Glass Bones
    (39, "glass_bones", None, None, "Pedro Nakamura — great body resistance to impacts"),
    # Chapada — free kick goals
    (45, "chapada",     None, None, "Roberto Bandarra — free kick goal"),
    (34, "chapada",     None, None, "Kuster — free kick goal"),
    # Midas Heel — Luigi's signature heel move that always backfires
    (35, "midas_heel",  None, None, "Luigi Tedesco — calcanhar de Midas"),
    # Levanta — Cleiton Moura got nutmegged ('capote') and his son yelled 'levanta, chora nao pai!' from sidelines
    (51, "levanta", 387, None, "Cleiton Moura — capote 2026-03-24 vs Axolotls, son on sidelines"),
    # SBQE — Só Bate Quem Erra
    (34, "sbqe",        None, None, "Kuster — só bate quem erra"),
    (41, "sbqe",        None, None, "Mazza — só bate quem erra"),
    (45, "sbqe",        None, None, "Roberto Bandarra — só bate quem erra"),
    (40, "sbqe",        None, None, "Marcelo D — só bate quem erra"),
    # Punch Up — 2026-01-27, 6-1 vs Momentum (lower-division, not in regular division table)
    (31, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Arthur Mendes"),
    (34, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Kuster"),
    (55, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Alexis"),
    (44, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Lucas Claro"),
    (57, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Matheus"),
    (51, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Cleiton Moura"),
    (50, "punch_up", 8, 1, "Steamrolled Momentum 6-1 — Cleiton Castro"),
]

# ── Name → player_id alias map for card parsing ───────────────────────────────
# Covers names that appear in yellow_cards column but differ from canonical_name
CARD_NAME_ALIASES = {
    "Guilherme Kuster": 34,   # canonical: Kuster
    "Pablo Rodrigues":  37,   # canonical: Pablo
    "Roberto Machado":  46,   # Bobby Axe
    "Guilherme Pereira": 82,  # display: Chico
}

def name_to_player_id(name, players):
    """Match a raw name from yellow_cards to a player_id."""
    name = name.strip()
    if name in CARD_NAME_ALIASES:
        return CARD_NAME_ALIASES[name]
    # Exact match on canonical_name or display_name
    for p in players:
        if p["canonical_name"] == name or p.get("display_name") == name:
            return p["id"]
    # Partial: canonical_name starts with name (handles "Kuster" matching "Guilherme Kuster" etc.)
    name_lower = name.lower()
    for p in players:
        canon = (p["canonical_name"] or "").lower()
        display = (p.get("display_name") or "").lower()
        if canon == name_lower or display == name_lower:
            return p["id"]
        # Check if any word in canonical matches a word in name
        canon_words = set(canon.split())
        name_words  = set(name_lower.split())
        if canon_words & name_words and len(canon_words & name_words) >= min(len(canon_words), len(name_words)):
            return p["id"]
    return None


def award_cards(players):
    """Parse yellow_cards column from games; award yellow_card or blue_card badges."""
    awarded = skipped = 0
    print("Checking card badges...")
    games_r = sb.table("games").select("id, yellow_cards").eq("team_id", 1).execute()
    unmatched: set[str] = set()
    for game in games_r.data:
        cards = game.get("yellow_cards") or []
        game_id = game["id"]
        for entry in cards:
            entry = entry.strip()
            if not entry:
                continue
            # Determine card type
            if "(azul)" in entry.lower():
                slug = "blue_card"
                raw_name = entry.replace("(azul)", "").replace("(Azul)", "").strip()
            elif "(vermelho)" in entry.lower():
                # Red cards — skip for now (no badge yet)
                continue
            else:
                slug = "yellow_card"
                raw_name = entry
            pid = name_to_player_id(raw_name, players)
            if pid is None:
                unmatched.add(raw_name)
                continue
            try:
                sb.table("player_badges").insert({
                    "player_id": pid,
                    "badge_slug": slug,
                    "game_id":    game_id,
                }).execute()
                awarded += 1
                print(f"  ✓ {slug} → player_id={pid} ({raw_name}) game_id={game_id}")
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    skipped += 1
                else:
                    print(f"  ERROR player_id={pid} ({raw_name}) game_id={game_id}: {e}")
    if unmatched:
        print(f"  ⚠ Unmatched names (no player_id found): {sorted(unmatched)}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped


def award_game(badge_slug, rows, label):
    """Award a game-specific badge (deduped by player+badge+game)."""
    awarded = skipped = 0
    print(f"Checking {label}...")
    for row in rows:
        try:
            sb.table("player_badges").insert({
                "player_id": row["player_id"],
                "badge_slug": badge_slug,
                "game_id":    row["game_id"],
            }).execute()
            awarded += 1
            print(f"  ✓ player_id={row['player_id']} game_id={row['game_id']} ({row['count']})")
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR player_id={row['player_id']} game_id={row['game_id']}: {e}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped


def award_season(badge_slug, season_id, label):
    """Award a season badge to all players who appeared in that season.
    Uses game_players if available, falls back to goals+assists scorers."""
    awarded = skipped = 0
    print(f"Checking {label} (season_id={season_id})...")
    games_r = sb.table("games").select("id").eq("season_id", season_id).eq("team_id", 1).execute()
    game_ids = [g["id"] for g in games_r.data]
    if not game_ids:
        print(f"  No games found for season {season_id}")
        return 0, 0
    players_r = sb.table("game_players").select("player_id").in_("game_id", game_ids).execute()
    player_ids = list({row["player_id"] for row in players_r.data if row["player_id"]})
    if not player_ids:
        # Fallback: use anyone who scored or assisted that season
        goals_r   = sb.table("goals").select("player_id").in_("game_id", game_ids).not_.is_("player_id", "null").execute()
        assists_r  = sb.table("assists").select("player_id").in_("game_id", game_ids).not_.is_("player_id", "null").execute()
        player_ids = list({r["player_id"] for r in goals_r.data} | {r["player_id"] for r in assists_r.data})
        print(f"  (no game_players — falling back to {len(player_ids)} scorers/assisters)")
    for pid in player_ids:
        try:
            sb.table("player_badges").insert({
                "player_id": pid,
                "badge_slug": badge_slug,
                "game_id":    None,
                "season_id":  season_id,
            }).execute()
            awarded += 1
            print(f"  ✓ player_id={pid}")
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR player_id={pid}: {e}")
    print(f"  → {awarded} new, {skipped} already existed.")
    return awarded, skipped


total_awarded = total_skipped = 0

# Load all players once for name matching
all_players = sb.table("players").select("id, canonical_name, display_name").execute().data

# ── Game badges ───────────────────────────────────────────────────────────────
r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 3).not_.is_("player_id", "null").execute()
a, s = award_game("hattrick", r.data, "Hat Trick (3+ goals)")
total_awarded += a; total_skipped += s

r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).eq("count", 4).not_.is_("player_id", "null").execute()
a, s = award_game("poker", r.data, "Poker (4 goals)")
total_awarded += a; total_skipped += s

r = sb.table("goals").select("player_id, game_id, count") \
    .eq("own_goal", False).gte("count", 5).not_.is_("player_id", "null").execute()
a, s = award_game("manita", r.data, "Manita (5+ goals)")
total_awarded += a; total_skipped += s

r = sb.table("assists").select("player_id, game_id, count") \
    .not_.is_("player_id", "null").gte("count", 3).execute()
a, s = award_game("garcom", r.data, "Garçom (3+ assists)")
total_awarded += a; total_skipped += s

# ── Card badges ────────────────────────────────────────────────────────────────
a, s = award_cards(all_players)
total_awarded += a; total_skipped += s

# ── Season badges ─────────────────────────────────────────────────────────────
for season_id, slug, label in CHAMPION_SEASONS:
    a, s = award_season(slug, season_id, label)
    total_awarded += a; total_skipped += s

# Clean up wrongly-assigned victus records (were Summer 2024, should be victus_ii)
sb.table("player_badges").delete().eq("badge_slug", "victus").eq("season_id", VICTUS_II_SEASON_ID).execute()
print("Cleaned up mis-assigned victus records (season_id=17 → now victus_ii)")

a, s = award_season("victus",    VICTUS_SEASON_ID,    "Victus (Summer 2022 — original shame season)")
total_awarded += a; total_skipped += s

a, s = award_season("victus_ii", VICTUS_II_SEASON_ID, "Victus II (Summer 2024 — they came back for more)")
total_awarded += a; total_skipped += s

# ── Manual awards ─────────────────────────────────────────────────────────────
print("Applying manual awards...")
for player_id, badge_slug, game_id, season_id, notes in MANUAL_AWARDS:
    try:
        sb.table("player_badges").insert({
            "player_id": player_id, "badge_slug": badge_slug,
            "game_id": game_id, "season_id": season_id, "notes": notes,
        }).execute()
        total_awarded += 1
        print(f"  ✓ Manual: player_id={player_id} badge={badge_slug} ({notes})")
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            total_skipped += 1
        else:
            print(f"  ERROR player_id={player_id}: {e}")

print(f"\nAll done — {total_awarded} new badges awarded, {total_skipped} already existed.")
