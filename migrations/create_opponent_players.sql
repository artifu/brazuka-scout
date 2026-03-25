-- Track memorable / notable players from opposing teams.
-- One player can accumulate multiple nicknames over time.

CREATE TABLE IF NOT EXISTS opponent_players (
  id          serial PRIMARY KEY,
  team        text NOT NULL,   -- e.g. 'Axolotls', 'Do It Again'
  notes       text,            -- general notes about this player
  first_seen  date,            -- date of first encounter
  created_at  timestamptz DEFAULT now()
);

COMMENT ON TABLE opponent_players IS 'Notable players from opposing teams, identified by nickname(s).';

-- Each row is one nickname for one opponent player.
-- The same player can have multiple rows (different games, different nicknames).
CREATE TABLE IF NOT EXISTS opponent_player_nicknames (
  id                   serial PRIMARY KEY,
  opponent_player_id   integer NOT NULL REFERENCES opponent_players(id) ON DELETE CASCADE,
  nickname             text NOT NULL,
  game_id              integer REFERENCES games(id),  -- game where this nickname was coined/noted
  context              text,    -- free-text describing the memorable moment
  created_at           timestamptz DEFAULT now(),
  UNIQUE (opponent_player_id, nickname)
);

COMMENT ON TABLE opponent_player_nicknames IS 'Nicknames for notable opponent players, one per memorable incident.';
