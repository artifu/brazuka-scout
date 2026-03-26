"""
Stage 1 — Chunker

Converts the WhatsApp chat export into two types of chunks:
  - GameChunk  : one chunk per game window (detected by game_detector.py)
  - GeneralChunk: one chunk per calendar week, for non-game messages
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from parser import parse_chat, Message
from game_detector import detect_game_windows, GameWindow


@dataclass
class Chunk:
    content: str
    chunk_type: str          # "game" | "general"
    metadata: dict

    # Filled by classifier.py
    game_related: Optional[bool] = None
    category: Optional[str] = None   # result | signup | injury | banter | logistics | off_topic

    # Filled by embedder.py
    embedding: Optional[List[float]] = None


# ── Game chunks ──────────────────────────────────────────────────────────────

def _game_window_to_chunk(window: GameWindow) -> Chunk:
    """Convert a single GameWindow into a Chunk."""
    date_str = window.game_date.strftime("%Y-%m-%d")
    opponent = window.opponent or "Unknown"
    home_away = window.home_or_away or "unknown"

    lines = [f"[GAME | {date_str} | Brazuka vs {opponent} | {home_away}]", ""]

    if window.pre_game_messages:
        lines.append("--- PRÉ-JOGO ---")
        for msg in window.pre_game_messages[-40:]:   # last 40 pre-game msgs
            ts = msg.timestamp.strftime("%m/%d %H:%M")
            lines.append(f"[{ts}] {msg.sender}: {msg.text[:200]}")

    if window.post_game_messages:
        lines.append("--- PÓS-JOGO ---")
        for msg in window.post_game_messages[:60]:   # first 60 post-game msgs
            ts = msg.timestamp.strftime("%m/%d %H:%M")
            lines.append(f"[{ts}] {msg.sender}: {msg.text[:200]}")

    return Chunk(
        content="\n".join(lines),
        chunk_type="game",
        metadata={
            "type": "game",
            "date": date_str,
            "opponent": opponent,
            "home_or_away": home_away,
            "pre_msg_count": len(window.pre_game_messages),
            "post_msg_count": len(window.post_game_messages),
        },
    )


# ── General (weekly) chunks ──────────────────────────────────────────────────

def _messages_to_weekly_chunks(
    messages: List[Message],
    game_message_ids: set,
) -> List[Chunk]:
    """Chunk non-game messages into one chunk per calendar week."""
    chunks: List[Chunk] = []

    # Group by ISO week (year + week number)
    weeks: dict = {}
    for msg in messages:
        if id(msg) in game_message_ids:
            continue
        if not msg.timestamp:
            continue
        # Monday of the week
        week_start = (msg.timestamp - timedelta(days=msg.timestamp.weekday())).strftime("%Y-%m-%d")
        weeks.setdefault(week_start, []).append(msg)

    for week_start, msgs in sorted(weeks.items()):
        if len(msgs) < 5:          # skip nearly-empty weeks
            continue

        lines = [f"[GERAL | semana de {week_start}]", ""]
        for msg in msgs[:120]:     # cap at 120 messages per week
            ts = msg.timestamp.strftime("%m/%d %H:%M")
            lines.append(f"[{ts}] {msg.sender}: {msg.text[:150]}")

        chunks.append(Chunk(
            content="\n".join(lines),
            chunk_type="general",
            metadata={
                "type": "general",
                "week_start": week_start,
                "message_count": len(msgs),
            },
        ))

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def create_chunks(chat_file: str, game_only: bool = False) -> List[Chunk]:
    """
    Parse the WhatsApp export and return all chunks.

    Args:
        chat_file : path to the _chat.txt export
        game_only : if True, skip general weekly chunks

    Returns:
        List[Chunk] — game chunks first, then general chunks
    """
    print(f"📂 Parsing chat: {chat_file}")
    messages = parse_chat(chat_file)
    print(f"   {len(messages):,} messages parsed")

    print("🔍 Detecting game windows…")
    windows = detect_game_windows(messages)
    print(f"   {len(windows)} game windows found")

    # Build game chunks and collect which messages belong to game windows
    game_chunks: List[Chunk] = []
    game_message_ids: set = set()

    for window in windows:
        game_chunks.append(_game_window_to_chunk(window))
        for msg in window.pre_game_messages + window.post_game_messages:
            game_message_ids.add(id(msg))

    chunks = game_chunks

    if not game_only:
        print("📅 Building weekly general chunks…")
        general_chunks = _messages_to_weekly_chunks(messages, game_message_ids)
        print(f"   {len(general_chunks)} weekly chunks created")
        chunks = game_chunks + general_chunks

    print(f"✅ Total chunks: {len(chunks)} ({len(game_chunks)} game + {len(chunks) - len(game_chunks)} general)\n")
    return chunks
