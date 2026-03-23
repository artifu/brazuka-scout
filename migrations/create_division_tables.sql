-- Per-season league table (one row per team per season)
CREATE TABLE IF NOT EXISTS division_standings (
  id           serial PRIMARY KEY,
  season_name  text NOT NULL,
  position     integer NOT NULL,
  total_teams  integer NOT NULL,
  team_name    text NOT NULL,
  mp           integer NOT NULL,
  wins         integer NOT NULL,
  draws        integer NOT NULL,
  losses       integer NOT NULL,
  gf           integer NOT NULL,
  ga           integer NOT NULL,
  gd           integer NOT NULL,
  pts          integer NOT NULL,
  is_brazuka   boolean NOT NULL DEFAULT false,
  UNIQUE (season_name, team_name)
);

-- Every individual division game with score (all teams, not just Brazuka)
CREATE TABLE IF NOT EXISTS division_games (
  id           serial PRIMARY KEY,
  season_name  text NOT NULL,
  game_date    date,
  home_team    text NOT NULL,
  away_team    text NOT NULL,
  home_score   integer NOT NULL,
  away_score   integer NOT NULL,
  -- convenience: result from home team's perspective
  home_result  text GENERATED ALWAYS AS (
    CASE
      WHEN home_score > away_score THEN 'win'
      WHEN home_score < away_score THEN 'loss'
      ELSE 'draw'
    END
  ) STORED,
  UNIQUE (season_name, game_date, home_team, away_team)
);
