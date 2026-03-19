"""
Detects game windows in the chat.
A "game window" is a cluster of messages from ~24h before to ~12h after each scheduled game.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from parser import Message

# Patterns that signal a game announcement in the chat
GAME_ANNOUNCEMENT_PATTERNS = [
    re.compile(r'Home Team:.*vs\..*Away Team:', re.IGNORECASE),
    re.compile(r'(Magnuson|Arena Sports)', re.IGNORECASE),
]

# Patterns for post-game score / goal reports
GOAL_REPORT_PATTERNS = [
    re.compile(r'\d+\s*(?:do|de|x)\s*\w+', re.IGNORECASE),   # "2 do Kuster", "1 de Arthur"
    re.compile(r'\d+\s*gol', re.IGNORECASE),
    re.compile(r'ganhamos|perdemos|empat', re.IGNORECASE),
    re.compile(r'\d+\s*[x×]\s*\d+', re.IGNORECASE),           # "3x2", "3 x 2"
]


@dataclass
class GameWindow:
    game_date: datetime
    opponent: str
    home_or_away: str  # "home" or "away"
    pre_game_messages: list[Message] = field(default_factory=list)
    post_game_messages: list[Message] = field(default_factory=list)

    @property
    def all_messages(self):
        return self.pre_game_messages + self.post_game_messages

    def summary(self) -> str:
        return (
            f"Game on {self.game_date.strftime('%Y-%m-%d %H:%M')} "
            f"vs {self.opponent} ({self.home_or_away}) | "
            f"{len(self.pre_game_messages)} pre-game msgs, "
            f"{len(self.post_game_messages)} post-game msgs"
        )


def extract_opponent(text: str) -> tuple[str, str]:
    """
    From a game announcement message, extract opponent name and home/away.
    Returns (opponent, "home"|"away")
    """
    home_match = re.search(
        r'Home Team:\s*Brazuka[^(]*\(.*?\)\s*vs\.\s*Away Team:\s*([^\(]+)',
        text, re.IGNORECASE
    )
    away_match = re.search(
        r'Home Team:\s*([^\(]+)\(.*?\)\s*vs\.\s*Away Team:\s*Brazuka',
        text, re.IGNORECASE
    )

    if home_match:
        return home_match.group(1).strip(), "home"
    elif away_match:
        return away_match.group(1).strip(), "away"
    return "Unknown", "unknown"


def detect_game_windows(messages: list[Message]) -> list[GameWindow]:
    """
    Scan messages for game announcements and group surrounding messages
    into GameWindow objects.
    """
    windows: list[GameWindow] = []
    seen_game_dates: set = set()

    for i, msg in enumerate(messages):
        # Check if this message is a game announcement
        is_announcement = any(p.search(msg.text) for p in GAME_ANNOUNCEMENT_PATTERNS)
        if not is_announcement:
            continue

        # Extract game date/time — look for the day/time in surrounding context
        # The announcement message is often multi-line and contains the game time
        full_text = msg.text

        # Try to find a date like "Tuesday, March 17th at 8:35PM"
        date_match = re.search(
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*'
            r'(\w+ \d+(?:st|nd|rd|th)?)\s+at\s+(\d+:\d+\s*(?:AM|PM)?)',
            full_text, re.IGNORECASE
        )

        # Use the message timestamp date as fallback
        if date_match:
            try:
                day_name, month_day, time_str = date_match.groups()
                year = msg.timestamp.year
                # Parse something like "March 17th" + "8:35PM"
                month_day_clean = re.sub(r'(st|nd|rd|th)', '', month_day).strip()
                game_dt = datetime.strptime(
                    f"{month_day_clean} {year} {time_str.strip().upper()}",
                    "%B %d %Y %I:%M%p"
                )
            except ValueError:
                game_dt = msg.timestamp
        else:
            game_dt = msg.timestamp

        # Deduplicate: skip if we already have a window for this game day
        game_day_key = game_dt.date()
        if game_day_key in seen_game_dates:
            continue
        seen_game_dates.add(game_day_key)

        opponent, home_away = extract_opponent(full_text)
        window = GameWindow(
            game_date=game_dt,
            opponent=opponent,
            home_or_away=home_away
        )

        # Collect messages in -24h to +18h window around game time
        window_start = game_dt - timedelta(hours=24)
        window_end = game_dt + timedelta(hours=18)

        for m in messages:
            if m.timestamp < window_start:
                continue
            if m.timestamp > window_end:
                continue
            if m.timestamp <= game_dt:
                window.pre_game_messages.append(m)
            else:
                window.post_game_messages.append(m)

        windows.append(window)

    # Sort by game date
    windows.sort(key=lambda w: w.game_date)
    return windows


if __name__ == "__main__":
    import sys
    from parser import parse_chat, filter_recent

    if len(sys.argv) < 2:
        print("Usage: python game_detector.py <chat_file>")
        sys.exit(1)

    msgs = parse_chat(sys.argv[1])
    recent = filter_recent(msgs, days=90)
    windows = detect_game_windows(recent)

    print(f"Found {len(windows)} game windows in the last 90 days:\n")
    for w in windows:
        print(f"  {w.summary()}")
