import { supabase } from './supabase'
import { unstable_noStore as noStore } from 'next/cache'

// ── Arena Sports config ────────────────────────────────────────────────────
// Update BRAZUKA_TEAM_ID each new season (Arena Sports team ID for Brazuka US)
const BRAZUKA_ARENA_TEAM_ID = '219258'  // Winter II 2025-26
const RECEBA_ARENA_TEAM_ID = '215356'   // Fall 2025
const ARENA_BASE = 'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1'
const ARENA_HEADERS = { 'Accept': 'application/vnd.api+json', 'User-Agent': 'Mozilla/5.0' }

function cleanOpponentName(name: string): string {
  return name
    .replace(/\s+(?:NPGK|NP\s*\d*|N\dP)\s*$/i, '')
    .replace(/\s*\((?:Tues?\.?\s+Men'?s?\s+D\d*|Tue\s+Men'?s?\s+D\d*|M|S)\)\s*(?:\([MS]\)\s*)?$/i, '')
    .replace(/\s*\([MS]\)\s*$/i, '')
    .replace(/\s+NP\s*\d*$/i, '')
    .trim()
}

function cleanRecebaOpponentName(name: string): string {
  return name
    .replace(/\s*\([A-Z]{2,4}\)\s+(?:Thurs?\.?\s+)?Men[s']?\s+[CD]\d*\s*(?:-\s*\S+)?\s*$/i, '')
    .replace(/\s*\([MS]\)\s*$/i, '')
    .replace(/\s+-\s*(?:\w+\s*\d*\s*)?$/i, '')
    .trim()
}

export type NextGame = {
  date: string
  opponent: string
  homeOrAway: 'home' | 'away'
  field: string | null
}

export async function getUpcomingGames(): Promise<NextGame[]> {
  noStore()
  try {
    const url = `${ARENA_BASE}/teams/${BRAZUKA_ARENA_TEAM_ID}?cache[save]=false&include=events.homeTeam,events.visitingTeam,events.resource&company=arenasports`
    const res = await fetch(url, { headers: ARENA_HEADERS, next: { revalidate: 3600 } })
    if (!res.ok) return []
    const data = await res.json()

    const included: Record<string, { type: string; attributes: Record<string, unknown> }> = {}
    for (const item of data.included ?? []) included[item.id] = item

    const today = new Date().toISOString().slice(0, 10)
    const evRefs: { id: string }[] = data.data?.relationships?.events?.data ?? []

    const upcoming: NextGame[] = []
    for (const ref of evRefs) {
      const ev = included[ref.id]
      if (!ev || ev.type !== 'events') continue
      const a = ev.attributes
      if (a.home_score != null || a.visiting_score != null) continue  // already played

      const gameDate = ((a.start_date ?? a.start ?? '') as string).slice(0, 10)
      if (!gameDate || gameDate < today) continue

      const ht = String(a.hteam_id ?? '')
      const vt = String(a.vteam_id ?? '')
      const isHome = ht === BRAZUKA_ARENA_TEAM_ID
      const oppId  = isHome ? vt : ht
      const oppTeam = included[oppId]
      if (!oppTeam) continue
      const oppName = cleanOpponentName(oppTeam.attributes.name as string)

      const resourceId = (ev as { relationships?: { resource?: { data?: { id: string } } } }).relationships?.resource?.data?.id
      const field = resourceId ? (included[resourceId]?.attributes?.name as string | null ?? null) : null

      upcoming.push({ date: gameDate, opponent: oppName, homeOrAway: isHome ? 'home' : 'away', field })
    }

    upcoming.sort((a, b) => a.date.localeCompare(b.date))
    return upcoming
  } catch {
    return []
  }
}

export async function getUpcomingRecebaGames(): Promise<NextGame[]> {
  noStore()
  try {
    const url = `${ARENA_BASE}/teams/${RECEBA_ARENA_TEAM_ID}?cache[save]=false&include=events.homeTeam,events.visitingTeam,events.resource&company=arenasports`
    const res = await fetch(url, { headers: ARENA_HEADERS, next: { revalidate: 3600 } })
    if (!res.ok) return []
    const data = await res.json()

    const included: Record<string, { type: string; attributes: Record<string, unknown> }> = {}
    for (const item of data.included ?? []) included[item.id] = item

    const today = new Date().toISOString().slice(0, 10)
    const evRefs: { id: string }[] = data.data?.relationships?.events?.data ?? []

    const upcoming: NextGame[] = []
    for (const ref of evRefs) {
      const ev = included[ref.id]
      if (!ev || ev.type !== 'events') continue
      const a = ev.attributes
      if (a.home_score != null || a.visiting_score != null) continue

      const gameDate = ((a.start_date ?? a.start ?? '') as string).slice(0, 10)
      if (!gameDate || gameDate < today) continue

      const ht = String(a.hteam_id ?? '')
      const vt = String(a.vteam_id ?? '')
      const isHome = ht === RECEBA_ARENA_TEAM_ID
      const oppId  = isHome ? vt : ht
      const oppTeam = included[oppId]
      if (!oppTeam) continue
      const oppName = cleanRecebaOpponentName(oppTeam.attributes.name as string)

      const resourceId = (ev as { relationships?: { resource?: { data?: { id: string } } } }).relationships?.resource?.data?.id
      const field = resourceId ? (included[resourceId]?.attributes?.name as string | null ?? null) : null

      upcoming.push({ date: gameDate, opponent: oppName, homeOrAway: isHome ? 'home' : 'away', field })
    }

    upcoming.sort((a, b) => a.date.localeCompare(b.date))
    return upcoming
  } catch {
    return []
  }
}

// ── ELO model (mirrors NextGamePredictor.tsx constants) ──────────────────────
const MODEL_INTERCEPT = -0.321
const MODEL_SLOPE     = 0.0070
const MODEL_DRAW_RATE = 0.096

function sigmoid(x: number) { return 1 / (1 + Math.exp(-x)) }

export function predictGame(brazukaElo: number, oppElo: number, isHome: boolean) {
  const diff = isHome ? brazukaElo - oppElo : oppElo - brazukaElo
  const pHomeWin = sigmoid(MODEL_INTERCEPT + MODEL_SLOPE * diff)
  const pDraw    = MODEL_DRAW_RATE
  const pWin     = isHome ? pHomeWin : Math.max(0, 1 - pHomeWin - pDraw)
  const pLoss    = Math.max(0, 1 - pWin - pDraw)
  return { win: pWin, draw: pDraw, loss: pLoss }
}

export async function savePrediction(game: NextGame, brazukaElo: number, oppElo: number) {
  const { win, draw, loss } = predictGame(brazukaElo, oppElo, game.homeOrAway === 'home')
  await supabase.from('predictions').upsert({
    game_date:    game.date,
    opponent:     game.opponent,
    home_or_away: game.homeOrAway,
    brazuka_elo:  brazukaElo,
    opp_elo:      oppElo,
    p_win:        +win.toFixed(4),
    p_draw:       +draw.toFixed(4),
    p_loss:       +loss.toFixed(4),
    model_version: 'v1',
    predicted_at: new Date().toISOString(),
  }, { onConflict: 'game_date,opponent' })
}

export async function getHeadToHead(opponent: string) {
  // Fuzzy match: use first significant word of opponent name
  const keyword = opponent.split(/\s+/).filter(w => w.length > 2)[0] ?? opponent
  const { data: games } = await supabase
    .from('games')
    .select('game_date, result, score_brazuka, score_opponent, home_or_away')
    .eq('team_id', 1)
    .ilike('opponent', `%${keyword}%`)
    .not('result', 'is', null)
    .order('game_date', { ascending: false })
    .limit(50)

  if (!games || games.length === 0) return null

  const wins   = games.filter(g => g.result === 'win').length
  const draws  = games.filter(g => g.result === 'draw').length
  const losses = games.filter(g => g.result === 'loss').length
  const gf     = games.reduce((s, g) => s + (g.score_brazuka ?? 0), 0)
  const ga     = games.reduce((s, g) => s + (g.score_opponent ?? 0), 0)

  return {
    played: games.length, wins, draws, losses, gf, ga,
    recent: games.slice(0, 5).map(g => ({
      date: g.game_date,
      result: g.result as 'win' | 'draw' | 'loss',
      score: g.score_brazuka != null ? `${g.score_brazuka}–${g.score_opponent}` : null,
      homeOrAway: g.home_or_away as 'home' | 'away',
    })),
  }
}

export async function getTeams() {
  const { data } = await supabase.from('teams').select('id, name').order('id')
  return data ?? []
}

export async function getSeasons(teamId?: number) {
  let query = supabase
    .from('seasons')
    .select('id, name, team_id, start_date')
    .order('start_date', { ascending: false })  // newest first in pills
  if (teamId) query = query.eq('team_id', teamId)
  const { data } = await query
  return data ?? []
}

export async function getGames(seasonId?: number, teamId?: number) {
  let query = supabase
    .from('games')
    .select('id, game_date, opponent, home_or_away, result, score_brazuka, score_opponent, scorers_known, venue, field, season_id, team_id')
    .order('game_date', { ascending: false })
    .limit(1000)
  if (seasonId) query = query.eq('season_id', seasonId)
  else if (teamId) query = query.eq('team_id', teamId)
  const { data } = await query
  return data ?? []
}

export async function getOverallRecord(seasonId?: number, teamId?: number) {
  let query = supabase.from('games').select('result, score_brazuka, score_opponent').limit(1000)
  if (seasonId) query = query.eq('season_id', seasonId)
  else if (teamId) query = query.eq('team_id', teamId)
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

export async function getTopPlayers(seasonId?: number, teamId?: number) {
  // Fetch goals (with game_id for participation inference)
  let goalsQuery = supabase
    .from('goals')
    .select('player, player_id, count, game_id, games!inner(season_id, team_id)')
    .eq('own_goal', false)
  if (seasonId) goalsQuery = goalsQuery.eq('games.season_id', seasonId)
  else if (teamId) goalsQuery = goalsQuery.eq('games.team_id', teamId)

  // Fetch assists (team_id stored directly on row)
  let assistsQuery = supabase
    .from('assists')
    .select('player, player_id, count, game_id, season_id, team_id')
    .limit(2000)
  if (seasonId) assistsQuery = assistsQuery.eq('season_id', seasonId)
  else if (teamId) assistsQuery = assistsQuery.eq('team_id', teamId)

  let teamGamesQuery = supabase.from('games').select('id').limit(5000)
  if (seasonId) teamGamesQuery = teamGamesQuery.eq('season_id', seasonId)
  else if (teamId) teamGamesQuery = teamGamesQuery.eq('team_id', teamId)

  // Display name overrides (e.g. "Mazza" for Marcelo Mazzafera)
  const displayNamesQuery = supabase
    .from('players')
    .select('id, display_name')
    .not('display_name', 'is', null)

  const [{ data: goalsData }, { data: assistsData }, { data: teamGamesData }, { data: displayNamesData }] = await Promise.all([
    goalsQuery, assistsQuery, teamGamesQuery, displayNamesQuery,
  ])

  const teamGameIdSet = new Set<number>((teamGamesData ?? []).map(g => Number(g.id)))

  const displayNames: Record<number, string> = {}
  for (const row of displayNamesData ?? []) {
    if (row.display_name) displayNames[row.id] = row.display_name
  }

  type PlayerEntry = { name: string; playerId: number | null; goals: number; assists: number }
  const totals: Record<string, PlayerEntry> = {}
  const key = (id: number | null, name: string) => id != null ? `id:${id}` : `name:${name}`

  for (const row of goalsData ?? []) {
    const k = key(row.player_id, row.player)
    if (!totals[k]) totals[k] = { name: row.player, playerId: row.player_id ?? null, goals: 0, assists: 0 }
    totals[k].goals += row.count
  }

  for (const row of assistsData ?? []) {
    const k = key(row.player_id, row.player)
    if (!totals[k]) totals[k] = { name: row.player, playerId: row.player_id ?? null, goals: 0, assists: 0 }
    totals[k].assists += row.count
  }

  // Fetch appearances only for the player_ids we know about — keeps query small (avoids 1000-row page limit)
  const knownPlayerIds = [...new Set(
    Object.values(totals).map(e => e.playerId).filter((id): id is number => id != null)
  )]

  // appearances is now the single source of truth for roster data (game_players migrated in)
  // Paginate: Supabase anon key caps at 1000 rows per request
  const roosterData: { player_id: number; game_id: number }[] = []
  if (knownPlayerIds.length > 0) {
    let offset = 0
    const PAGE = 1000
    while (true) {
      const { data } = await supabase.from('appearances')
        .select('player_id, game_id')
        .in('player_id', knownPlayerIds)
        .range(offset, offset + PAGE - 1)
      if (!data || data.length === 0) break
      roosterData.push(...data)
      if (data.length < PAGE) break
      offset += PAGE
    }
  }

  // MP per player = appearances intersected with this team's game IDs
  const playerMP = new Map<number, Set<number>>()
  for (const row of roosterData) {
    if (!row.player_id || !row.game_id) continue
    const gid = Number(row.game_id)
    if (!teamGameIdSet.has(gid)) continue
    const pid = Number(row.player_id)
    if (!playerMP.has(pid)) playerMP.set(pid, new Set())
    playerMP.get(pid)!.add(gid)
  }

  return Object.entries(totals)
    .map(([, { name, playerId, goals, assists }]) => {
      const contributions = goals + assists
      const mp = playerId != null ? (playerMP.get(Number(playerId))?.size ?? 0) : 0
      const gamesPlayed = mp > 0 ? mp : null
      const gpInferred = false
      const displayName = playerId != null && displayNames[playerId] ? displayNames[playerId] : name
      return {
        player: displayName, playerId, goals, assists, gamesPlayed,
        contributions,
        participationRate: gamesPlayed ? +((contributions / gamesPlayed).toFixed(2)) : null,
        gpInferred,
      }
    })
    .sort((a, b) => b.contributions - a.contributions || b.goals - a.goals)
}

export async function getSeasonHistory(teamId: number) {
  const [{ data: games }, { data: divGames }] = await Promise.all([
    supabase
      .from('games')
      .select('result, score_brazuka, score_opponent, season_id, seasons!inner(name, start_date, league_position)')
      .eq('team_id', teamId)
      .not('result', 'is', null)
      .limit(1000),
    supabase
      .from('division_games')
      .select('season_name, home_team, away_team')
      .eq('league', 'brazuka')
      .limit(5000),
  ])

  if (!games) return []

  // Count distinct teams per season from division_games
  const teamsBySeasonName = new Map<string, Set<string>>()
  for (const g of divGames ?? []) {
    if (!teamsBySeasonName.has(g.season_name)) teamsBySeasonName.set(g.season_name, new Set())
    teamsBySeasonName.get(g.season_name)!.add(g.home_team)
    teamsBySeasonName.get(g.season_name)!.add(g.away_team)
  }

  const bySeasonId: Record<number, {
    name: string; start_date: string; league_position: number | null; total_teams: number | null;
    wins: number; losses: number; draws: number; gf: number; ga: number
  }> = {}

  for (const g of games) {
    const s = (g.seasons as unknown) as { name: string; start_date: string; league_position: number | null }
    const sid = g.season_id
    if (!bySeasonId[sid]) {
      const total_teams = teamsBySeasonName.get(s.name)?.size ?? null
      bySeasonId[sid] = { name: s.name, start_date: s.start_date, league_position: s.league_position ?? null, total_teams, wins: 0, losses: 0, draws: 0, gf: 0, ga: 0 }
    }
    const row = bySeasonId[sid]
    if (g.result === 'win') row.wins++
    else if (g.result === 'loss') row.losses++
    else if (g.result === 'draw') row.draws++
    if (g.score_brazuka != null) row.gf += g.score_brazuka
    if (g.score_opponent != null) row.ga += g.score_opponent
  }

  return Object.values(bySeasonId).sort((a, b) =>
    new Date(b.start_date).getTime() - new Date(a.start_date).getTime()
  )
}

export async function getEloRankings(league = 'brazuka') {
  const { data } = await supabase
    .from('elo_ratings')
    .select('team_name, rating, games_played')
    .eq('league', league)
    .order('rating', { ascending: false })
    .limit(50)
  return data ?? []
}

export async function getPlayerImpact(): Promise<Record<number, { winLift: number; pValue: number; confidenceLevel: string }>> {
  const { data } = await supabase
    .from('player_impact')
    .select('player_id, win_lift, p_value, confidence_level')
  if (!data) return {}
  const map: Record<number, { winLift: number; pValue: number; confidenceLevel: string }> = {}
  for (const row of data) {
    map[row.player_id] = {
      winLift: row.win_lift,
      pValue: row.p_value,
      confidenceLevel: row.confidence_level,
    }
  }
  return map
}

const GOALKEEPERS: { id: number; name: string }[] = [
  { id: 55, name: 'Alexis' },
  { id: 40, name: 'Marcelo D' },
  { id: 81, name: 'Igor Moreira' },
  { id: 63, name: 'Darley' },
  { id: 52, name: 'Victor Ozorio' },
]

export async function getGoalkeeperStats() {
  const gkIds = GOALKEEPERS.map(g => g.id)

  // Appearances from both tables, deduplicated by (game_id, player_id)
  const [{ data: apps }, { data: gps }, { data: games }] = await Promise.all([
    supabase.from('appearances').select('game_id, player_id').in('player_id', gkIds).limit(2000),
    supabase.from('game_players').select('game_id, player_id').in('player_id', gkIds).limit(2000),
    supabase.from('games').select('id, result, score_opponent').eq('team_id', 1).in('result', ['win', 'draw', 'loss']).limit(1000),
  ])

  const seen = new Map<string, { game_id: number; player_id: number }>()
  for (const r of [...(apps ?? []), ...(gps ?? [])]) {
    const k = `${r.game_id}:${r.player_id}`
    if (!seen.has(k)) seen.set(k, r)
  }

  const gamesById = new Map((games ?? []).map(g => [g.id, g]))
  const gkGameIds = new Map<number, Set<number>>(gkIds.map(id => [id, new Set()]))
  for (const r of seen.values()) {
    gkGameIds.get(r.player_id)?.add(r.game_id)
  }

  return GOALKEEPERS.map(({ id, name }) => {
    const gameIds = gkGameIds.get(id) ?? new Set<number>()
    const played = [...gameIds].map(gid => gamesById.get(gid)).filter(Boolean) as { result: string; score_opponent: number | null }[]
    const mp = played.length
    const wins = played.filter(g => g.result === 'win').length
    const draws = played.filter(g => g.result === 'draw').length
    const losses = played.filter(g => g.result === 'loss').length
    const gc = played.reduce((s, g) => s + (g.score_opponent ?? 0), 0)
    const pts = wins * 3 + draws
    return {
      id, name, mp, wins, draws, losses, gc,
      gcPerGame: mp > 0 ? +(gc / mp).toFixed(2) : null,
      winPct: mp > 0 ? Math.round((wins / mp) * 100) : null,
      ptsRate: mp > 0 ? Math.round((pts / (mp * 3)) * 100) : null,
    }
  })
}

export type DivisionStanding = {
  team: string; pos: number; mp: number; pts: number; totalTeams: number; seasonName: string
  w: number; d: number; l: number; gf: number; ga: number; gd: number
}

export type TeamProjection = {
  team: string
  projPosMedian: number   // 50th percentile
  projPosMean:   number   // weighted average — used for tie-breaking
  projPos25:     number   // 25th percentile (better)
  projPos75:     number   // 75th percentile (worse)
  probTop3:      number   // 0–100
  probBottom3:   number   // 0–100
}

export async function getCurrentSeasonStandings(league = 'brazuka'): Promise<DivisionStanding[]> {
  const { data: latest } = await supabase
    .from('division_games')
    .select('season_name, game_date')
    .eq('league', league)
    .order('game_date', { ascending: false })
    .limit(1)
  if (!latest?.[0]) return []

  const seasonName = latest[0].season_name
  const { data: games } = await supabase
    .from('division_games')
    .select('home_team, away_team, home_score, away_score')
    .eq('season_name', seasonName)
    .eq('league', league)
    .limit(500)
  if (!games) return []

  const t: Record<string, { mp: number; w: number; d: number; l: number; gf: number; ga: number }> = {}
  const add = (name: string) => { if (!t[name]) t[name] = { mp: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0 } }
  for (const g of games) {
    add(g.home_team); add(g.away_team)
    t[g.home_team].mp++; t[g.away_team].mp++
    t[g.home_team].gf += g.home_score; t[g.home_team].ga += g.away_score
    t[g.away_team].gf += g.away_score; t[g.away_team].ga += g.home_score
    if (g.home_score > g.away_score)      { t[g.home_team].w++; t[g.away_team].l++ }
    else if (g.home_score < g.away_score) { t[g.home_team].l++; t[g.away_team].w++ }
    else                                   { t[g.home_team].d++; t[g.away_team].d++ }
  }

  const totalTeams = Object.keys(t).length
  return Object.entries(t)
    .map(([team, s]) => {
      const pts = s.w * 3 + s.d
      const gd  = s.gf - s.ga
      return { team, pts, gd, mp: s.mp, w: s.w, d: s.d, l: s.l, gf: s.gf, ga: s.ga }
    })
    .sort((a, b) => b.pts - a.pts || b.gd - a.gd)
    .map((s, i) => ({ ...s, pos: i + 1, totalTeams, seasonName }))
}

export type PlayerBadge = {
  slug: string; name: string; description: string; icon: string
  gameId: number | null; notes: string | null
}

export type WithWithoutStats = {
  mp: number; wins: number; draws: number; losses: number
  gf: number; ga: number
  winPct: number; gfPerGame: number; gaPerGame: number
}

export type PlayerProfile = {
  withStats:    WithWithoutStats | null
  withoutStats: WithWithoutStats | null
  badges:       PlayerBadge[]
}

export async function getPlayerProfile(playerId: number, teamId = 1): Promise<PlayerProfile> {
  const [{ data: allGames }, { data: appRows }, { data: badgeRows }] = await Promise.all([
    supabase.from('games').select('id, result, score_brazuka, score_opponent').eq('team_id', teamId).not('result', 'is', null).limit(2000),
    supabase.from('appearances').select('game_id').eq('player_id', playerId).limit(2000),
    supabase.from('player_badges').select('badge_slug, game_id, notes, badges!inner(name, description, icon)').eq('player_id', playerId),
  ])

  const withIds = new Set<number>()
  for (const r of appRows ?? []) withIds.add(r.game_id)

  const calc = (games: typeof allGames): WithWithoutStats | null => {
    if (!games?.length) return null
    const mp     = games.length
    const wins   = games.filter(g => g.result === 'win').length
    const draws  = games.filter(g => g.result === 'draw').length
    const losses = games.filter(g => g.result === 'loss').length
    const gf     = games.reduce((s, g) => s + (g.score_brazuka  ?? 0), 0)
    const ga     = games.reduce((s, g) => s + (g.score_opponent ?? 0), 0)
    return { mp, wins, draws, losses, gf, ga,
      winPct:    Math.round(wins / mp * 100),
      gfPerGame: +( gf / mp).toFixed(2),
      gaPerGame: +( ga / mp).toFixed(2),
    }
  }

  const withGames    = (allGames ?? []).filter(g => withIds.has(g.id))
  const withoutGames = withIds.size > 0 ? (allGames ?? []).filter(g => !withIds.has(g.id)) : []

  const badges: PlayerBadge[] = (badgeRows ?? []).map(b => {
    const badge = b.badges as unknown as { name: string; description: string; icon: string }
    return { slug: b.badge_slug, name: badge.name, description: badge.description, icon: badge.icon, gameId: b.game_id ?? null, notes: b.notes ?? null }
  })

  return {
    withStats:    withIds.size > 0 ? calc(withGames) : null,
    withoutStats: withIds.size > 0 ? calc(withoutGames) : null,
    badges,
  }
}

export async function getSeasonProjection(league = 'brazuka'): Promise<TeamProjection[]> {
  // 1. Find current season
  const { data: latest } = await supabase
    .from('division_games')
    .select('season_name')
    .eq('league', league)
    .order('game_date', { ascending: false })
    .limit(1)
  if (!latest?.[0]) return []
  const seasonName = latest[0].season_name

  // 2. Fetch all played games this season (division_games only stores completed results)
  const { data: games } = await supabase
    .from('division_games')
    .select('home_team, away_team, home_score, away_score')
    .eq('season_name', seasonName)
    .eq('league', league)
    .not('home_score', 'is', null)
    .limit(500)
  if (!games || games.length === 0) return []

  // 3. Build current standings + track played pairs
  const t: Record<string, { mp: number; w: number; d: number; l: number; gf: number; ga: number }> = {}
  const playedPairs: Record<string, number> = {}
  const pairKey = (a: string, b: string) => (a < b ? `${a}|||${b}` : `${b}|||${a}`)
  const add = (name: string) => { if (!t[name]) t[name] = { mp: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0 } }

  for (const g of games) {
    add(g.home_team); add(g.away_team)
    t[g.home_team].mp++; t[g.away_team].mp++
    t[g.home_team].gf += g.home_score; t[g.home_team].ga += g.away_score
    t[g.away_team].gf += g.away_score; t[g.away_team].ga += g.home_score
    if (g.home_score > g.away_score)       { t[g.home_team].w++; t[g.away_team].l++ }
    else if (g.home_score < g.away_score)  { t[g.home_team].l++; t[g.away_team].w++ }
    else                                    { t[g.home_team].d++; t[g.away_team].d++ }
    const pk = pairKey(g.home_team, g.away_team)
    playedPairs[pk] = (playedPairs[pk] ?? 0) + 1
  }

  const teams = Object.keys(t)
  const n = teams.length
  if (n < 2) return []

  // 4. Detect round-robin format: max times any pair has met = gamesPerMatchup
  const paircounts = Object.values(playedPairs)
  const gamesPerMatchup = paircounts.length > 0 ? Math.max(...paircounts) : 1

  // 5. Build remaining fixtures
  const remaining: { home: string; away: string }[] = []
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const pk = pairKey(teams[i], teams[j])
      const played = playedPairs[pk] ?? 0
      const toPlay = Math.max(0, gamesPerMatchup - played)
      for (let k = 0; k < toPlay; k++) {
        // Alternate home advantage each repeat
        if (k % 2 === 0) remaining.push({ home: teams[i], away: teams[j] })
        else             remaining.push({ home: teams[j], away: teams[i] })
      }
    }
  }

  // 6. Fetch ELO ratings with fuzzy name matching
  const { data: eloData } = await supabase
    .from('elo_ratings')
    .select('team_name, rating')
    .eq('league', league)
    .limit(50)

  const eloMap: Record<string, number> = {}
  for (const row of eloData ?? []) eloMap[row.team_name.toLowerCase()] = row.rating

  const DEFAULT_ELO = 1500
  const getElo = (team: string): number => {
    const lower = team.toLowerCase()
    if (eloMap[lower] != null) return eloMap[lower]
    // partial match: find elo entry whose name contains or is contained by team
    for (const [ename, elo] of Object.entries(eloMap)) {
      if (lower.includes(ename) || ename.includes(lower)) return elo
    }
    return DEFAULT_ELO
  }

  // 7. Monte Carlo – 10 000 simulations
  const SIMS = 10_000
  // positionCounts[team][pos] = # of sims where team finished at pos
  const positionCounts: Record<string, number[]> = {}
  for (const team of teams) positionCounts[team] = new Array(n + 1).fill(0)

  const baseW: Record<string, number> = {}
  const basePts: Record<string, number> = {}
  const baseGd: Record<string, number> = {}
  for (const team of teams) {
    baseW[team]   = t[team].w
    basePts[team] = t[team].w * 3 + t[team].d
    baseGd[team]  = t[team].gf - t[team].ga
  }

  for (let sim = 0; sim < SIMS; sim++) {
    const pts: Record<string, number> = { ...basePts }
    const gd:  Record<string, number> = { ...baseGd  }

    for (const { home, away } of remaining) {
      const { win: pWin, draw: pDraw } = predictGame(getElo(home), getElo(away), true)
      const r = Math.random()
      if (r < pWin) {
        pts[home] += 3; gd[home]++; gd[away]--
      } else if (r < pWin + pDraw) {
        pts[home]++; pts[away]++
      } else {
        pts[away] += 3; gd[away]++; gd[home]--
      }
    }

    const ranked = teams.slice().sort((a, b) => pts[b] - pts[a] || gd[b] - gd[a])
    for (let i = 0; i < ranked.length; i++) positionCounts[ranked[i]][i + 1]++
  }

  // 8. Aggregate: percentiles + top-3 / bottom-3 probabilities
  return teams.map(team => {
    const counts = positionCounts[team]
    let cumulative = 0
    let p25 = n, p50 = n, p75 = n
    let probTop3 = 0, probBottom3 = 0

    for (let pos = 1; pos <= n; pos++) {
      cumulative += counts[pos]
      const pct = cumulative / SIMS
      if (p25 === n && pct >= 0.25) p25 = pos
      if (p50 === n && pct >= 0.50) p50 = pos
      if (p75 === n && pct >= 0.75) p75 = pos
      if (pos <= 3)     probTop3    += counts[pos]
      if (pos > n - 3)  probBottom3 += counts[pos]
    }

    let posSum = 0
    for (let pos = 1; pos <= n; pos++) posSum += pos * counts[pos]

    return {
      team,
      projPosMedian: p50,
      projPosMean:   posSum / SIMS,
      projPos25:     p25,
      projPos75:     p75,
      probTop3:      Math.round(probTop3    / SIMS * 100),
      probBottom3:   Math.round(probBottom3 / SIMS * 100),
    }
  }).sort((a, b) => a.projPosMean - b.projPosMean)
}

export async function getTopOpponents(teamId: number, seasonId?: number) {
  let query = supabase
    .from('games')
    .select('opponent, result')
    .eq('team_id', teamId)
    .not('result', 'is', null)
    .limit(1000)
  if (seasonId) query = query.eq('season_id', seasonId)
  const { data } = await query
  if (!data) return []

  const map: Record<string, { played: number; wins: number; losses: number; draws: number }> = {}
  for (const g of data) {
    if (!map[g.opponent]) map[g.opponent] = { played: 0, wins: 0, losses: 0, draws: 0 }
    map[g.opponent].played++
    if (g.result === 'win') map[g.opponent].wins++
    else if (g.result === 'loss') map[g.opponent].losses++
    else if (g.result === 'draw') map[g.opponent].draws++
  }

  return Object.entries(map)
    .map(([opponent, s]) => ({ opponent, ...s }))
    .sort((a, b) => b.played - a.played)
    .slice(0, 10)
}
