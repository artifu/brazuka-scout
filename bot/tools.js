require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// ─── Schema reference ────────────────────────────────────────────────────────
//
// games:        id, game_date, opponent, home_or_away, result("win"/"loss"/"draw"),
//               score_brazuka, score_opponent, team_id, season_id, venue, field,
//               yellow_cards, red_cards, notable_moments, confidence
//
// goals:        id, game_id, player (text), player_id, count, notes
//
// appearances:  id, game_id, player (text), player_id
//               (unique on game_id + player)
//
// players:      id, canonical_name, aliases[]
//
// elo_ratings:  team_name, rating, games_played, league
//
// player_impact: player_id, win_lift, p_value, confidence_level
//
// ─────────────────────────────────────────────────────────────────────────────

// ─── Tool definitions for Claude function calling ────────────────────────────

const toolDefinitions = [
  {
    name: 'get_top_scorers',
    description: 'Returns the top goal scorers for Brazuka, optionally filtered by season year.',
    input_schema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'How many players to return (default 10)',
        },
        season: {
          type: 'string',
          description: 'Season year filter, e.g. "2025" or "2026". Omit for all-time.',
        },
      },
    },
  },
  {
    name: 'get_player_stats',
    description:
      'Returns goals, matches played, wins, draws, losses and win% for a specific player. By default counts only Brazuka US games (team_id=1). Pass team="receba" to get Receba FC stats, or team="all" for combined.',
    input_schema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Player name (partial match accepted, e.g. "Arthur" or "Kuster")',
        },
        team: {
          type: 'string',
          description: 'Which team to count: "brazuka" (default), "receba", or "all"',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'get_overall_record',
    description: "Returns Brazuka's overall W/D/L record, optionally filtered by season year.",
    input_schema: {
      type: 'object',
      properties: {
        season: {
          type: 'string',
          description: 'Season year filter, e.g. "2026". Omit for all-time.',
        },
      },
    },
  },
  {
    name: 'get_recent_results',
    description: 'Returns the most recent game results with scores.',
    input_schema: {
      type: 'object',
      properties: {
        n: {
          type: 'number',
          description: 'Number of recent games to return (default 5)',
        },
      },
    },
  },
  {
    name: 'get_head_to_head',
    description: "Returns Brazuka's historical record against a specific opponent.",
    input_schema: {
      type: 'object',
      properties: {
        opponent: {
          type: 'string',
          description: 'Opponent team name (partial match accepted)',
        },
      },
      required: ['opponent'],
    },
  },
  {
    name: 'get_next_game',
    description: 'Returns information about the next scheduled game from the Arena Sports calendar.',
    input_schema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_games_by_player',
    description:
      'Returns all games in which a specific player appeared, with optional result filter. ' +
      'Use this to answer questions like "losses where Arthur played" or "wins with Kuster".',
    input_schema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Player name (partial match accepted)',
        },
        result: {
          type: 'string',
          enum: ['win', 'loss', 'draw'],
          description: 'Optional: filter by game result',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'get_opponent_elo',
    description:
      'Returns ELO ratings for opponents in the Brazuka division. ' +
      'Lower rating = weaker team. Use to rank opponents by strength.',
    input_schema: {
      type: 'object',
      properties: {
        opponent: {
          type: 'string',
          description: 'Filter by team name (partial match). Omit to get all teams.',
        },
        order: {
          type: 'string',
          enum: ['asc', 'desc'],
          description: '"asc" = weakest first, "desc" = strongest first (default: desc)',
        },
      },
    },
  },
];

// ─── Tool implementations ────────────────────────────────────────────────────

async function get_top_scorers({ limit = 10, season } = {}) {
  let gameIds = null;

  if (season) {
    const { data: games } = await supabase
      .from('games')
      .select('id')
      .ilike('game_date', `${season}%`);
    gameIds = (games || []).map((g) => g.id);
    if (gameIds.length === 0) return { scorers: [], season };
  }

  let query = supabase.from('goals').select('player, count');
  if (gameIds) query = query.in('game_id', gameIds);

  const { data, error } = await query;
  if (error) throw new Error(error.message);

  // Aggregate goals per player (goals table has one row per scorer per game,
  // with `count` being how many goals they scored that game)
  const totals = {};
  for (const row of data || []) {
    const name = row.player;
    totals[name] = (totals[name] || 0) + (row.count || 1);
  }

  const scorers = Object.entries(totals)
    .map(([name, goals]) => ({ name, goals }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);

  return { scorers, season: season || 'all-time' };
}

async function get_player_stats({ name, team = 'brazuka' }) {
  // Resolve team_id filter
  const teamFilter = team === 'receba' ? 2 : team === 'all' ? null : 1; // default: Brazuka (1)

  // Get game_ids for the relevant team(s)
  let teamGameIds = null;
  if (teamFilter !== null) {
    const { data: teamGames } = await supabase
      .from('games')
      .select('id')
      .eq('team_id', teamFilter);
    teamGameIds = new Set((teamGames || []).map((g) => g.id));
  }
  // Try to resolve player_id via players table (canonical_name or aliases)
  const { data: playerRows } = await supabase
    .from('players')
    .select('id, canonical_name, aliases')
    .ilike('canonical_name', `%${name}%`);

  let playerId = null;
  let resolvedName = name;

  if (playerRows && playerRows.length === 1) {
    playerId = playerRows[0].id;
    resolvedName = playerRows[0].canonical_name;
  } else if (playerRows && playerRows.length > 1) {
    // Multiple exact-ish matches — return disambiguation list
    return {
      found: false,
      ambiguous: true,
      matches: playerRows.map((p) => p.canonical_name),
      message: `Nome ambíguo. Jogadores encontrados: ${playerRows.map((p) => p.canonical_name).join(', ')}`,
    };
  }

  // Filter by player_id if resolved, otherwise fall back to text match
  let goalQuery = supabase.from('goals').select('game_id, count');
  let appQuery = supabase.from('appearances').select('game_id, player');

  goalQuery = playerId ? goalQuery.eq('player_id', playerId) : goalQuery.ilike('player', `%${name}%`);
  appQuery  = playerId ? appQuery.eq('player_id', playerId)  : appQuery.ilike('player', `%${name}%`);

  // Apply team filter if needed
  if (teamGameIds !== null) {
    const ids = [...teamGameIds];
    goalQuery = goalQuery.in('game_id', ids);
    appQuery  = appQuery.in('game_id', ids);
  }

  const { data: goalRows, error: gErr } = await goalQuery;
  if (gErr) throw new Error(gErr.message);

  const { data: appRows, error: aErr } = await appQuery;
  if (aErr) throw new Error(aErr.message);

  if ((!goalRows || goalRows.length === 0) && (!appRows || appRows.length === 0)) {
    return { found: false, name };
  }

  // Canonical name = most common spelling found
  const allNames = [
    ...(goalRows || []).map(() => name),
    ...(appRows || []).map((r) => r.player),
  ];
  const canonicalName = resolvedName || appRows?.[0]?.player || goalRows?.[0]?.player || name;

  const goals = (goalRows || []).reduce((s, r) => s + (r.count || 1), 0);

  // All game_ids where player appeared
  const gameIdsFromApps = new Set((appRows || []).map((r) => r.game_id));
  // Also include games where they scored but weren't in appearances (edge case)
  const allGameIds = [...new Set([
    ...gameIdsFromApps,
    ...(goalRows || []).map((r) => r.game_id),
  ])];

  const matchesPlayed = allGameIds.length;

  // Get results for those games
  let wins = 0, draws = 0, losses = 0;
  if (allGameIds.length > 0) {
    const { data: games } = await supabase
      .from('games')
      .select('result')
      .in('id', allGameIds);
    for (const g of games || []) {
      if (g.result === 'win') wins++;
      else if (g.result === 'draw') draws++;
      else if (g.result === 'loss') losses++;
    }
  }

  const winPct = matchesPlayed > 0 ? Math.round((wins / matchesPlayed) * 100) : 0;

  return {
    found: true,
    name: canonicalName,
    goals,
    matches_played: matchesPlayed,
    wins,
    draws,
    losses,
    win_pct: winPct,
  };
}

async function get_overall_record({ season } = {}) {
  let query = supabase.from('games').select('result');
  if (season) query = query.ilike('game_date', `${season}%`);

  const { data, error } = await query;
  if (error) throw new Error(error.message);

  const record = { wins: 0, draws: 0, losses: 0, total: 0 };
  for (const g of data || []) {
    if (g.result === 'win') record.wins++;
    else if (g.result === 'draw') record.draws++;
    else if (g.result === 'loss') record.losses++;
    record.total++;
  }

  return { ...record, season: season || 'all-time' };
}

async function get_recent_results({ n = 5 } = {}) {
  const { data, error } = await supabase
    .from('games')
    .select('game_date, opponent, score_brazuka, score_opponent, result, venue')
    .order('game_date', { ascending: false })
    .limit(n);

  if (error) throw new Error(error.message);
  return { games: data || [] };
}

async function get_head_to_head({ opponent }) {
  // Resolve opponent name → team_id first (avoids fuzzy text matching in game rows)
  const { data: teams, error: tErr } = await supabase
    .from('teams')
    .select('id, name, aliases')
    .ilike('name', `%${opponent}%`)
    .limit(5);
  if (tErr) throw new Error(tErr.message);

  // Also search aliases (Supabase doesn't support ilike on array elements directly,
  // so we fetch candidates by name and let the alias check below catch the rest)
  let teamId = teams?.[0]?.id;
  let canonicalName = teams?.[0]?.name || opponent;

  if (!teamId) return { found: false, opponent, games: [], record: {} };

  const { data, error } = await supabase
    .from('games')
    .select('game_date, score_brazuka, score_opponent, result, opponent')
    .eq('opponent_id', teamId)
    .order('game_date', { ascending: false });

  if (error) throw new Error(error.message);

  const games = data || [];
  const record = { wins: 0, draws: 0, losses: 0, total: games.length };
  for (const g of games) {
    if (g.result === 'win') record.wins++;
    else if (g.result === 'draw') record.draws++;
    else if (g.result === 'loss') record.losses++;
  }

  return { opponent: canonicalName, record, games };
}

async function get_next_game() {
  const today = new Date().toISOString().split('T')[0];
  const { data, error } = await supabase
    .from('games')
    .select('game_date, opponent, venue, field, home_or_away')
    .gte('game_date', today)
    .is('result', null) // scheduled games have no result yet
    .order('game_date', { ascending: true })
    .limit(1);

  if (error) throw new Error(error.message);
  if (!data || data.length === 0) return { found: false };

  return { found: true, game: data[0] };
}

async function get_games_by_player({ name, result } = {}) {
  // Find all appearances matching the player name
  const { data: apps, error: aErr } = await supabase
    .from('appearances')
    .select('game_id, player')
    .ilike('player', `%${name}%`);

  if (aErr) throw new Error(aErr.message);
  if (!apps || apps.length === 0) return { found: false, name, games: [] };

  const gameIds = [...new Set(apps.map((a) => a.game_id))];
  const canonicalName = apps[0].player;

  // Fetch those games — join teams via opponent_id for canonical opponent name
  let gQuery = supabase
    .from('games')
    .select('id, game_date, opponent, opponent_id, score_brazuka, score_opponent, result, venue, opponent_team:teams!games_opponent_id_fkey(name)')
    .in('id', gameIds)
    .order('game_date', { ascending: false });

  if (result) gQuery = gQuery.eq('result', result);

  const { data: games, error: gErr } = await gQuery;
  if (gErr) throw new Error(gErr.message);

  // Use canonical team name from join when available
  const normalised = (games || []).map((g) => ({
    id: g.id,
    game_date: g.game_date,
    opponent: g.opponent_team?.name || g.opponent,   // canonical name wins
    score_brazuka: g.score_brazuka,
    score_opponent: g.score_opponent,
    result: g.result,
    venue: g.venue,
  }));

  return {
    found: true,
    name: canonicalName,
    total: normalised.length,
    result_filter: result || 'all',
    games: normalised,
  };
}

async function get_opponent_elo({ opponent, order = 'desc' } = {}) {
  // Join with teams to get canonical name + team_id for cross-referencing
  let query = supabase
    .from('elo_ratings')
    .select('team_name, rating, games_played, team_id, teams(name)')
    .eq('league', 'brazuka')
    .order('rating', { ascending: order === 'asc' })
    .limit(50);

  if (opponent) query = query.ilike('team_name', `%${opponent}%`);

  const { data, error } = await query;
  if (error) throw new Error(error.message);

  const teams = (data || []).map((r) => ({
    team_id: r.team_id,
    name: r.teams?.name || r.team_name,   // canonical name from teams table
    rating: r.rating,
    games_played: r.games_played,
  }));

  return { teams, order };
}

// ─── Dispatcher ──────────────────────────────────────────────────────────────

const toolFunctions = {
  get_top_scorers,
  get_player_stats,
  get_overall_record,
  get_recent_results,
  get_head_to_head,
  get_next_game,
  get_games_by_player,
  get_opponent_elo,
};

async function executeTool(name, input) {
  const fn = toolFunctions[name];
  if (!fn) throw new Error(`Unknown tool: ${name}`);
  return fn(input);
}

module.exports = { toolDefinitions, executeTool };
