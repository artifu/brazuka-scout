-- Pre-game win probability snapshots (for calibration tracking over time)
CREATE TABLE IF NOT EXISTS predictions (
  id            serial PRIMARY KEY,
  game_date     date NOT NULL,
  opponent      text NOT NULL,
  home_or_away  text NOT NULL,
  brazuka_elo   numeric NOT NULL,
  opp_elo       numeric NOT NULL,
  p_win         numeric NOT NULL,
  p_draw        numeric NOT NULL,
  p_loss        numeric NOT NULL,
  model_version text NOT NULL DEFAULT 'v1',
  predicted_at  timestamptz NOT NULL DEFAULT now(),
  -- Outcome filled in after the game
  actual_result text CHECK (actual_result IN ('win', 'draw', 'loss')),
  UNIQUE (game_date, opponent)
);
