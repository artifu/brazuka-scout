-- Migration 001: Add opponent_id to games + team_id to elo_ratings
-- Run this in the Supabase SQL Editor BEFORE running migrate_opponent_ids.py
--
-- What this does:
--   1. Adds aliases[], division, notes columns to teams
--   2. Adds opponent_id FK to games  (nullable — populated by the Python script)
--   3. Adds team_id FK to elo_ratings (nullable — populated by the Python script)

-- ── 1. Extend teams table ──────────────────────────────────────────────────
ALTER TABLE teams
  ADD COLUMN IF NOT EXISTS aliases  TEXT[]  DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS division TEXT,       -- e.g. "Tuesday Men's D1"
  ADD COLUMN IF NOT EXISTS notes    TEXT;       -- free-form notes (name changes, etc.)

-- ── 2. Add opponent_id FK to games ────────────────────────────────────────
ALTER TABLE games
  ADD COLUMN IF NOT EXISTS opponent_id INTEGER REFERENCES teams(id);

-- Index for fast join lookups
CREATE INDEX IF NOT EXISTS idx_games_opponent_id ON games(opponent_id);

-- ── 3. Add team_id FK to elo_ratings ──────────────────────────────────────
ALTER TABLE elo_ratings
  ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

CREATE INDEX IF NOT EXISTS idx_elo_ratings_team_id ON elo_ratings(team_id);
