CREATE TABLE IF NOT EXISTS division_standings (
  id              serial PRIMARY KEY,
  season_name     text NOT NULL,          -- e.g. "Summer 2024"
  position        integer NOT NULL,
  total_teams     integer NOT NULL,
  team_name       text NOT NULL,
  mp              integer NOT NULL,
  wins            integer NOT NULL,
  draws           integer NOT NULL,
  losses          integer NOT NULL,
  gf              integer NOT NULL,
  ga              integer NOT NULL,
  gd              integer NOT NULL,
  pts             integer NOT NULL,
  is_brazuka      boolean NOT NULL DEFAULT false,

  UNIQUE (season_name, team_name)
);
