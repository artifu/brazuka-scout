import { supabase } from './supabase'

export async function getSeasons() {
  const { data } = await supabase
    .from('seasons')
    .select('id, name, team_id, teams(name)')
    .order('start_date', { ascending: false })
  return data ?? []
}

export async function getGames(seasonId?: number) {
  let query = supabase
    .from('games')
    .select('*, seasons(name), teams(name)')
    .order('game_date', { ascending: false })
  if (seasonId) query = query.eq('season_id', seasonId)
  const { data } = await query
  return data ?? []
}

export async function getTopScorers(seasonId?: number) {
  let query = supabase.from('goals').select('player, player_id, count, game_id, games!inner(season_id)')
  if (seasonId) query = query.eq('games.season_id', seasonId)
  const { data } = await query
  if (!data) return []

  const totals: Record<string, number> = {}
  for (const row of data) {
    const key = row.player
    totals[key] = (totals[key] ?? 0) + row.count
  }
  return Object.entries(totals)
    .map(([player, goals]) => ({ player, goals }))
    .sort((a, b) => b.goals - a.goals)
}

export async function getOverallRecord(seasonId?: number) {
  let query = supabase.from('games').select('result, score_brazuka, score_opponent')
  if (seasonId) query = query.eq('season_id', seasonId)
  const { data } = await query

  const record = { wins: 0, losses: 0, draws: 0, goalsFor: 0, goalsAgainst: 0 }
  for (const g of data ?? []) {
    if (g.result === 'win') record.wins++
    else if (g.result === 'loss') record.losses++
    else if (g.result === 'draw') record.draws++
    if (g.score_brazuka != null) record.goalsFor += g.score_brazuka
    if (g.score_opponent != null) record.goalsAgainst += g.score_opponent
  }
  return record
}

export async function getGoalsByGame(gameId: number) {
  const { data } = await supabase
    .from('goals')
    .select('player, count, notes')
    .eq('game_id', gameId)
  return data ?? []
}
