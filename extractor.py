"""
AI-powered extractor: uses Claude to parse game windows into structured data.
"""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
import anthropic
from game_detector import GameWindow

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

EXTRACTION_PROMPT = """You are analyzing a WhatsApp group chat from a recreational football (soccer) team called "Brazuka" or "Brazuka US".

The team plays in a weekly league at Magnuson Park in Seattle. The group is Brazilian/multilingual, so messages may be in Portuguese, English, or a mix.

I will give you all the messages from a window around ONE specific match. Your job is to extract structured data from this conversation.

GAME INFO:
- Date: {game_date}
- Opponent: {opponent}
- Home/Away: {home_away}

MESSAGES (format: [timestamp] Sender: text):
{messages}

Extract the following and return as JSON only (no extra text):

{{
  "result": "win" | "loss" | "draw" | "unknown",
  "score_brazuka": <integer or null>,
  "score_opponent": <integer or null>,
  "goals": [
    {{"player": "name", "count": 1, "notes": "optional context"}}
  ],
  "players_confirmed": ["list of player names who confirmed availability pre-game"],
  "yellow_cards": ["player names"],
  "red_cards": ["player names"],
  "notable_moments": [
    "short description of funny/notable things that happened"
  ],
  "confidence": "high" | "medium" | "low"
}}

Rules:
- Be conservative: only include data explicitly mentioned in the messages
- For goals, look for phrases like "2 do Kuster", "1 Arthur", "fez gol", "marcou", "scored"
- For result, look for "ganhamos" (we won), "perdemos" (we lost), "empate" (draw), or score mentions
- For confirmed players, look for numbered availability lists (where people add their name)
- Use the LAST version of the availability list (people keep updating it)
- Notable moments: funny injuries, great saves, referee disputes, crazy plays — keep it short and fun
- If something is unclear, set it to null rather than guessing
"""


@dataclass
class GameResult:
    game_date: str
    opponent: str
    home_or_away: str
    result: str = "unknown"
    score_brazuka: Optional[int] = None
    score_opponent: Optional[int] = None
    goals: list[dict] = field(default_factory=list)
    players_confirmed: list[str] = field(default_factory=list)
    yellow_cards: list[str] = field(default_factory=list)
    red_cards: list[str] = field(default_factory=list)
    notable_moments: list[str] = field(default_factory=list)
    confidence: str = "low"
    raw_window_size: int = 0


def format_messages_for_prompt(window: GameWindow, max_messages: int = 150) -> str:
    """Convert messages to a compact string for the prompt."""
    msgs = window.all_messages

    # Prioritize post-game messages (they have the results) + last version of signup list
    # Take up to max_messages, biased toward post-game
    pre = window.pre_game_messages
    post = window.post_game_messages

    # Get the last 30 pre-game messages (signup list final state) + all post-game up to limit
    selected = pre[-30:] + post[:max_messages - 30]

    lines = []
    for m in selected:
        ts = m.timestamp.strftime("%m/%d %H:%M")
        text = m.text.replace("\n", " | ")  # flatten multiline
        if len(text) > 300:
            text = text[:300] + "..."
        lines.append(f"[{ts}] {m.sender}: {text}")

    return "\n".join(lines)


def extract_game_data(window: GameWindow) -> GameResult:
    """Use Claude to extract structured game data from a game window."""
    messages_text = format_messages_for_prompt(window)

    prompt = EXTRACTION_PROMPT.format(
        game_date=window.game_date.strftime("%Y-%m-%d %H:%M"),
        opponent=window.opponent,
        home_away=window.home_or_away,
        messages=messages_text
    )

    result = GameResult(
        game_date=window.game_date.strftime("%Y-%m-%d"),
        opponent=window.opponent,
        home_or_away=window.home_or_away,
        raw_window_size=len(window.all_messages)
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Fast and cheap for extraction
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        # Extract JSON from response (handle if wrapped in markdown)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            result.result = data.get("result", "unknown")
            result.score_brazuka = data.get("score_brazuka")
            result.score_opponent = data.get("score_opponent")
            result.goals = data.get("goals", [])
            result.players_confirmed = data.get("players_confirmed", [])
            result.yellow_cards = data.get("yellow_cards", [])
            result.red_cards = data.get("red_cards", [])
            result.notable_moments = data.get("notable_moments", [])
            result.confidence = data.get("confidence", "low")

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"  Warning: could not parse AI response for {result.game_date}: {e}")

    return result


def extract_all_games(windows: list[GameWindow], verbose: bool = True) -> list[GameResult]:
    """Extract data from all game windows."""
    results = []
    for i, window in enumerate(windows):
        if verbose:
            print(f"  [{i+1}/{len(windows)}] Extracting {window.game_date.strftime('%Y-%m-%d')} vs {window.opponent}...")
        game_result = extract_game_data(window)
        results.append(game_result)
        if verbose:
            score_str = f"{game_result.score_brazuka}-{game_result.score_opponent}" \
                        if game_result.score_brazuka is not None else "?"
            goals_str = [f"{g['player']} ({g['count']})" for g in game_result.goals]
            print(f"         → {game_result.result.upper()} {score_str} | "
                  f"Goals: {goals_str} | "
                  f"Confidence: {game_result.confidence}")
    return results


if __name__ == "__main__":
    import sys
    from parser import parse_chat, filter_recent
    from game_detector import detect_game_windows

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <chat_file>")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    print("Parsing chat...")
    msgs = parse_chat(sys.argv[1])
    recent = filter_recent(msgs, days=90)
    print(f"Loaded {len(recent)} messages from the last 90 days")

    print("\nDetecting game windows...")
    windows = detect_game_windows(recent)
    print(f"Found {len(windows)} games\n")

    print("Extracting game data with AI...")
    results = extract_all_games(windows)

    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    for r in results:
        print(f"\n{r.game_date} vs {r.opponent} ({r.home_or_away})")
        print(f"  Result: {r.result} | Score: {r.score_brazuka}-{r.score_opponent}")
        if r.goals:
            goals_str = ', '.join(f"{g['player']} x{g['count']}" for g in r.goals)
            print(f"  Goals: {goals_str}")
        if r.players_confirmed:
            print(f"  Players: {', '.join(r.players_confirmed)}")
        if r.notable_moments:
            for note in r.notable_moments:
                print(f"  📝 {note}")
