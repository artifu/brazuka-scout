-- player_impact: stores OLS regression results for Win Lift stat
-- Run compute_player_impact.py after each weekly DB update to refresh.

CREATE TABLE IF NOT EXISTS player_impact (
  player_id        integer PRIMARY KEY,
  player_name      text NOT NULL,
  win_lift         float,          -- OLS coefficient: e.g. 0.08 = +8% win prob when present
  p_value          float,          -- two-sided p-value from OLS
  games_played     integer,        -- number of appearances used in model
  confidence_level text,           -- 'high' (p<0.10), 'suggestive' (p<0.25), 'low' (p>=0.25)
  computed_at      timestamptz DEFAULT now()
);
