-- ELO ratings for all division teams (recomputed after each game week)
CREATE TABLE IF NOT EXISTS elo_ratings (
  id           serial PRIMARY KEY,
  team_name    text NOT NULL UNIQUE,
  rating       numeric NOT NULL DEFAULT 1000,
  games_played integer NOT NULL DEFAULT 0,
  updated_at   timestamptz NOT NULL DEFAULT now()
);
