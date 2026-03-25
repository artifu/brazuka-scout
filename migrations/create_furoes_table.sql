-- Track no-shows / late arrivals per game ("furoes")
-- A "furao" is someone who signed up but didn't show or showed very late.

CREATE TABLE IF NOT EXISTS furoes (
  id          serial PRIMARY KEY,
  game_id     integer NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  player      text NOT NULL,
  player_id   integer REFERENCES players(id),
  type        text NOT NULL DEFAULT 'no-show'
                CHECK (type IN ('no-show', 'late', 'last-second')),
  reason      text,
  created_at  timestamptz DEFAULT now(),
  UNIQUE (game_id, player)
);

COMMENT ON TABLE furoes IS 'Players who registered but failed to show (or showed very late) for a game.';
COMMENT ON COLUMN furoes.type IS 'no-show | late | last-second';
