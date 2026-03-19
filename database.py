"""
SQLite database for Brazuka Scout.
Stores game results, player stats, and allows historical queries.
"""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from extractor import GameResult

DEFAULT_DB = Path(__file__).parent / "brazuka.db"


@contextmanager
def get_conn(db_path: Path = DEFAULT_DB):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB):
    """Create tables if they don't exist."""
    with get_conn(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date   TEXT NOT NULL UNIQUE,
            opponent    TEXT NOT NULL,
            home_or_away TEXT NOT NULL,
            result      TEXT NOT NULL DEFAULT 'unknown',
            score_brazuka   INTEGER,
            score_opponent  INTEGER,
            yellow_cards    TEXT DEFAULT '[]',
            red_cards       TEXT DEFAULT '[]',
            notable_moments TEXT DEFAULT '[]',
            confidence  TEXT DEFAULT 'low',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS goals (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id   INTEGER NOT NULL REFERENCES games(id),
            player    TEXT NOT NULL,
            count     INTEGER NOT NULL DEFAULT 1,
            notes     TEXT
        );

        CREATE TABLE IF NOT EXISTS appearances (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id   INTEGER NOT NULL REFERENCES games(id),
            player    TEXT NOT NULL,
            UNIQUE(game_id, player)
        );
        """)
    print(f"Database initialized at {db_path}")


def save_game(result: GameResult, db_path: Path = DEFAULT_DB) -> int:
    """Insert or replace a game result. Returns the game id."""
    with get_conn(db_path) as conn:
        # Upsert game
        conn.execute("""
            INSERT INTO games
                (game_date, opponent, home_or_away, result, score_brazuka, score_opponent,
                 yellow_cards, red_cards, notable_moments, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_date) DO UPDATE SET
                opponent       = excluded.opponent,
                home_or_away   = excluded.home_or_away,
                result         = excluded.result,
                score_brazuka  = excluded.score_brazuka,
                score_opponent = excluded.score_opponent,
                yellow_cards   = excluded.yellow_cards,
                red_cards      = excluded.red_cards,
                notable_moments = excluded.notable_moments,
                confidence     = excluded.confidence
        """, (
            result.game_date,
            result.opponent,
            result.home_or_away,
            result.result,
            result.score_brazuka,
            result.score_opponent,
            json.dumps(result.yellow_cards),
            json.dumps(result.red_cards),
            json.dumps(result.notable_moments),
            result.confidence,
        ))

        game_id = conn.execute(
            "SELECT id FROM games WHERE game_date = ?", (result.game_date,)
        ).fetchone()["id"]

        # Clear existing goals & appearances for this game (full replace)
        conn.execute("DELETE FROM goals WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM appearances WHERE game_id = ?", (game_id,))

        # Insert goals
        for g in result.goals:
            conn.execute(
                "INSERT INTO goals (game_id, player, count, notes) VALUES (?, ?, ?, ?)",
                (game_id, g.get("player", ""), g.get("count", 1), g.get("notes"))
            )

        # Insert appearances
        for player in result.players_confirmed:
            conn.execute(
                "INSERT OR IGNORE INTO appearances (game_id, player) VALUES (?, ?)",
                (game_id, player)
            )

        return game_id


def save_all_games(results: list[GameResult], db_path: Path = DEFAULT_DB):
    """Save a list of game results to the database."""
    for r in results:
        game_id = save_game(r, db_path)
    print(f"Saved {len(results)} games to database.")


# ─── Query helpers ────────────────────────────────────────────────────────────

def get_all_games(db_path: Path = DEFAULT_DB) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM games ORDER BY game_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_player_stats(db_path: Path = DEFAULT_DB) -> list[dict]:
    """Return goal totals and appearance counts per player."""
    with get_conn(db_path) as conn:
        rows = conn.execute("""
            SELECT
                p.player,
                COALESCE(SUM(g.count), 0) AS goals,
                COUNT(DISTINCT a.game_id)  AS appearances
            FROM (
                SELECT DISTINCT player FROM goals
                UNION
                SELECT DISTINCT player FROM appearances
            ) p
            LEFT JOIN goals       g ON g.player = p.player
            LEFT JOIN appearances a ON a.player  = p.player
            GROUP BY p.player
            ORDER BY goals DESC, appearances DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_head_to_head(opponent: str, db_path: Path = DEFAULT_DB) -> dict:
    """Return W/L/D record against a specific opponent."""
    with get_conn(db_path) as conn:
        rows = conn.execute("""
            SELECT result, COUNT(*) AS cnt
            FROM games
            WHERE LOWER(opponent) LIKE LOWER(?)
            GROUP BY result
        """, (f"%{opponent}%",)).fetchall()
        record = {"wins": 0, "losses": 0, "draws": 0, "unknown": 0}
        for r in rows:
            result = r["result"]
            if result == "win":
                record["wins"] = r["cnt"]
            elif result == "loss":
                record["losses"] = r["cnt"]
            elif result == "draw":
                record["draws"] = r["cnt"]
            else:
                record["unknown"] = r["cnt"]
        return record


def get_overall_record(db_path: Path = DEFAULT_DB) -> dict:
    """Return overall W/L/D record."""
    with get_conn(db_path) as conn:
        rows = conn.execute("""
            SELECT result, COUNT(*) AS cnt FROM games
            WHERE result != 'unknown'
            GROUP BY result
        """).fetchall()
        record = {"wins": 0, "losses": 0, "draws": 0}
        for r in rows:
            if r["result"] == "win":
                record["wins"] = r["cnt"]
            elif r["result"] == "loss":
                record["losses"] = r["cnt"]
            elif r["result"] == "draw":
                record["draws"] = r["cnt"]
        total = sum(record.values())
        record["total"] = total
        return record


if __name__ == "__main__":
    init_db()
    print("\nOverall record:", get_overall_record())
    print("\nPlayer stats:")
    for p in get_player_stats():
        print(f"  {p['player']}: {p['goals']} goals in {p['appearances']} games")
