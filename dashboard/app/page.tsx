import { getGames, getTopPlayers, getOverallRecord, getSeasons, getSeasonHistory, getTopOpponents, getEloRankings, getPlayerImpact, getGoalkeeperStats, getUpcomingGames, getUpcomingRecebaGames, getHeadToHead, savePrediction, getCurrentSeasonStandings, getSeasonProjection, getFieldStats } from '@/lib/data'
import PlayerTable from './PlayerTable'
import GoalkeeperTable from './GoalkeeperTable'
import SeasonFilter from './SeasonFilter'
import NextGamePredictor from './NextGamePredictor'
import CurrentSeasonTable from './CurrentSeasonTable'

export const revalidate = 60

// ── small presentational components ────────────────────────────────────────

function ResultBadge({ result }: { result: string }) {
  const styles: Record<string, string> = {
    win:  'bg-[#009C3B] text-white',
    loss: 'bg-red-500 text-white',
    draw: 'bg-[#FFDF00] text-[#111827]',
  }
  const labels: Record<string, string> = { win: 'W', loss: 'L', draw: 'D' }
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-black ${styles[result] ?? 'bg-gray-300 text-gray-700'}`}>
      {labels[result] ?? '?'}
    </span>
  )
}

function StatCard({ label, value, sub, accent = 'green' }: {
  label: string; value: string | number; sub?: string
  accent?: 'green' | 'yellow' | 'blue' | 'red'
}) {
  const color = { green: 'text-[#009C3B]', yellow: 'text-[#b89a00]', blue: 'text-[#002776]', red: 'text-red-600' }[accent]
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-1 shadow-sm">
      <span className="text-gray-400 text-xs uppercase tracking-widest">{label}</span>
      <span className={`text-3xl font-black tabular-nums ${color}`}>{value}</span>
      {sub && <span className="text-gray-400 text-xs">{sub}</span>}
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-xs uppercase tracking-widest text-gray-400 font-semibold">{children}</span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  )
}

function PositionBadge({ pos, total }: { pos: number | null; total?: number | null }) {
  if (pos === null) return <span className="text-gray-300 text-xs">—</span>
  const suffix = total ? <span className="text-gray-300 font-normal">/{total}</span> : null
  const isLast = total != null && pos === total
  if (isLast) return <span title="Dead last 😬" className="text-xs font-bold text-red-400">💀 {pos}{suffix}</span>
  if (pos === 1) return <span title="Champions">🥇 <span className="text-xs text-gray-400 font-normal">{pos}{suffix}</span></span>
  if (pos === 2) return <span title="Runners-up">🥈 <span className="text-xs text-gray-400 font-normal">{pos}{suffix}</span></span>
  if (pos === 3) return <span title="3rd place">🥉 <span className="text-xs text-gray-400 font-normal">{pos}{suffix}</span></span>
  return <span className="text-gray-500 text-xs font-semibold">{pos}{suffix}</span>
}

// ── page ───────────────────────────────────────────────────────────────────

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ season?: string; team?: string; game?: string }>
}) {
  const { season, team, game: gameParam } = await searchParams
  const teamId = team ? parseInt(team) : 1
  const seasonId = season ? parseInt(season) : undefined

  const league = teamId === 2 ? 'receba' : 'brazuka'
  const [games, players, record, seasons, seasonHistory, topOpponents, eloRankings, playerImpact, goalkeepers, upcomingGames, divisionStandings, seasonProjection, fieldStats] = await Promise.all([
    getGames(seasonId, teamId),
    getTopPlayers(seasonId, teamId),
    getOverallRecord(seasonId, teamId),
    getSeasons(teamId),
    getSeasonHistory(teamId),
    getTopOpponents(teamId, seasonId),
    getEloRankings(league),
    getPlayerImpact(),
    getGoalkeeperStats(),
    (!seasonId && teamId === 1) ? getUpcomingGames() :
    (!seasonId && teamId === 2) ? getUpcomingRecebaGames() :
    Promise.resolve([] as Awaited<ReturnType<typeof getUpcomingGames>>),
    (!seasonId) ? getCurrentSeasonStandings(league) : Promise.resolve([] as Awaited<ReturnType<typeof getCurrentSeasonStandings>>),
    (!seasonId) ? getSeasonProjection(league) : Promise.resolve([] as Awaited<ReturnType<typeof getSeasonProjection>>),
    getFieldStats(teamId),
  ])

  const gameIdx = gameParam ? Math.max(0, Math.min(parseInt(gameParam), upcomingGames.length - 1)) : 0
  const nextGame = upcomingGames[gameIdx] ?? null
  const h2h = nextGame ? await getHeadToHead(nextGame.opponent) : null

  // Merge win lift data into players (keyed by player_id to avoid name mismatch)
  const playersWithImpact = players.map(p => {
    const impact = p.playerId != null ? playerImpact[p.playerId] : undefined
    return {
      ...p,
      winLift: impact?.winLift ?? null,
      winLiftPValue: impact?.pValue ?? null,
      winLiftConfidence: impact?.confidenceLevel ?? null,
    }
  })

  const myTeamElo = teamId === 2
    ? eloRankings.find(r => r.team_name === 'Receba FC')?.rating ?? 1000
    : eloRankings.find(r => r.team_name === 'Brazuka US')?.rating ?? 1000

  // Snapshot prediction for the next game (upserts — safe to call on every render)
  if (nextGame) {
    const oppElo = eloRankings.find(t => t.team_name.toLowerCase().includes(
      nextGame.opponent.split(' ').filter(w => w.length > 2)[0]?.toLowerCase() ?? ''
    ))?.rating ?? 1000
    savePrediction(nextGame, myTeamElo, oppElo).catch(() => {})
  }
  const total = record.wins + record.losses + record.draws
  const winPct = total > 0 ? Math.round((record.wins / total) * 100) : 0
  const pts = record.wins * 3 + record.draws
  const ptsRate = total > 0 ? Math.round((pts / (total * 3)) * 100) : null
  const teamName = teamId === 2 ? 'RECEBA FC' : 'BRAZUKA'

  return (
    <main className="min-h-screen bg-[#f5f7f5] text-gray-900">

      {/* Brazilian stripe */}
      <div className="h-1.5 w-full" style={{ background: 'linear-gradient(90deg, #009C3B 0%, #009C3B 40%, #FFDF00 40%, #FFDF00 70%, #002776 70%, #002776 100%)' }} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.jpg" alt="Brazuka FC crest" className="w-16 h-16 rounded-full object-cover border-2 border-[#009C3B]/30 shrink-0 shadow-sm" />
            <div>
              <h1 className="text-2xl font-black tracking-tight leading-tight">
                <span className="text-[#009C3B]">BRAZUKA</span>
                <span className="text-gray-300 font-light mx-2">&</span>
                <span className="text-[#002776]">RECEBA FC</span>
              </h1>
              <p className="text-gray-400 text-sm mt-0.5">Magnuson Park · Seattle</p>
            </div>
          </div>

          {/* Team tabs */}
          <div className="mt-5 flex items-center gap-1">
            {[{ id: 1, label: 'Brazuka US', day: 'Tuesday' }, { id: 2, label: 'Receba FC', day: 'Thursday' }].map(t => (
              <a
                key={t.id}
                href={`/?team=${t.id}`}
                className={`px-4 py-1.5 rounded-full text-sm font-semibold border transition-colors ${
                  teamId === t.id
                    ? 'bg-[#009C3B] text-white border-[#009C3B]'
                    : 'text-gray-500 border-gray-300 hover:border-[#009C3B] hover:text-[#009C3B]'
                }`}
              >
                {t.label} <span className="opacity-60 text-xs font-normal">{t.day}</span>
              </a>
            ))}
          </div>

          {/* Season filter: year → season two-step */}
          <SeasonFilter seasons={seasons} teamId={teamId} seasonId={seasonId} />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-10">

        {/* Record */}
        <section>
          <SectionLabel>{seasonId ? 'Season Record' : `All-time Record · ${teamName}`}</SectionLabel>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Wins"     value={record.wins}    accent="green"  />
            <StatCard label="Losses"   value={record.losses}  accent="red"    />
            <StatCard label="Draws"    value={record.draws}   accent="yellow" />
            <StatCard label="Win Rate" value={`${winPct}%`}   accent="green"  sub={`${total} games`} />
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <StatCard label="Pts Rate"   value={ptsRate != null ? `${ptsRate}%` : '—'} accent="blue" sub={`${pts} pts · W=3 D=1 L=0`} />
            <StatCard label="Goals For"  value={record.goalsFor}      accent="green" sub="all games" />
            <StatCard label="Goals vs"   value={record.goalsAgainst}  accent="red"   sub="all games" />
          </div>
        </section>

        {/* Next Game Predictor — all-time view for both teams */}
        {!seasonId && upcomingGames.length > 0 && nextGame && (
          <section>
            <SectionLabel>Next Game</SectionLabel>
            <NextGamePredictor
              nextGame={nextGame}
              h2h={h2h}
              eloTeams={eloRankings}
              brazukaElo={myTeamElo}
              upcomingGames={upcomingGames}
              selectedIdx={gameIdx}
              divisionStandings={divisionStandings}
            />
          </section>
        )}

        {/* Current Season Standings + Projection */}
        {!seasonId && divisionStandings.length > 0 && (
          <section>
            <SectionLabel>Current Season Standings</SectionLabel>
            <CurrentSeasonTable
              standings={divisionStandings}
              projections={seasonProjection}
              teamId={teamId}
            />
          </section>
        )}

        {/* Top Players */}
        {players.length > 0 && (
          <section>
            <SectionLabel>Top Players</SectionLabel>
            <PlayerTable players={playersWithImpact} teamId={teamId} />
          </section>
        )}

        {/* Recent Games — before opponents */}
        <section>
          <SectionLabel>{seasonId ? 'Games' : 'Recent Games'}</SectionLabel>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            {games.slice(0, seasonId ? undefined : 15).map((g, i, arr) => {
              const score = g.score_brazuka != null ? `${g.score_brazuka} – ${g.score_opponent ?? '?'}` : 'Forfeit'
              const date = new Date(g.game_date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
              return (
                <div key={g.id} className={`flex items-center gap-3 px-5 py-4 ${i !== arr.length - 1 ? 'border-b border-gray-100' : ''}`}>
                  <ResultBadge result={g.result} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-800 truncate">{g.opponent}</span>
                      <span className="text-gray-400 text-xs">{g.home_or_away === 'home' ? '🏠' : '✈️'}</span>
                    </div>
                    <div className="text-gray-400 text-xs mt-0.5">
                      {date}{g.field && <span className="ml-2">· {g.field}</span>}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-black tabular-nums text-sm text-gray-800">{score}</div>
                    {!g.scorers_known && g.score_brazuka != null && (
                      <div className="text-gray-300 text-xs">scorers unknown</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Top Opponents */}
        {topOpponents.length > 0 && (
          <section>
            <SectionLabel>Top Opponents</SectionLabel>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
              <table className="w-full min-w-[360px] text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 text-left">Opponent</th>
                    <th className="px-3 py-3 text-center">P</th>
                    <th className="px-3 py-3 text-center">W</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">D</th>
                    <th className="px-3 py-3 text-center">L</th>
                    <th className="px-4 py-3 text-right">Win%</th>
                  </tr>
                </thead>
                <tbody>
                  {topOpponents.map((o, i) => {
                    const winPct = Math.round((o.wins / o.played) * 100)
                    return (
                      <tr key={o.opponent} className={`${i !== topOpponents.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
                        <td className="px-4 py-3 font-medium text-gray-800">{o.opponent}</td>
                        <td className="px-3 py-3 text-center text-gray-500">{o.played}</td>
                        <td className="px-3 py-3 text-center text-[#009C3B] font-bold">{o.wins}</td>
                        <td className="px-3 py-3 text-center text-gray-400 hidden sm:table-cell">{o.draws}</td>
                        <td className="px-3 py-3 text-center text-red-500">{o.losses}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${winPct >= 50 ? 'bg-[#009C3B]/10 text-[#009C3B]' : 'bg-red-50 text-red-500'}`}>
                            {winPct}%
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            </div>
          </section>
        )}

        {/* Season by Season — all-time view only */}
        {!seasonId && seasonHistory.length > 0 && (
          <section>
            <SectionLabel>Season by Season</SectionLabel>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 text-left">Season</th>
                    <th className="px-3 py-3 text-center">Pos</th>
                    <th className="px-3 py-3 text-center">W</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">D</th>
                    <th className="px-3 py-3 text-center">L</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">GD</th>
                    <th className="px-3 py-3 text-center">Pts</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">Pts%</th>
                    <th className="px-4 py-3 text-center">Win%</th>
                  </tr>
                </thead>
                <tbody>
                  {seasonHistory.map((s, i) => {
                    const mp = s.wins + s.draws + s.losses
                    const gd = s.gf - s.ga
                    const pts = s.wins * 3 + s.draws
                    const ptsRate = mp > 0 ? Math.round((pts / (mp * 3)) * 100) : null
                    const winPct = mp > 0 ? Math.round((s.wins / mp) * 100) : 0
                    return (
                      <tr key={i} className={`${i !== seasonHistory.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
                        <td className="px-4 py-3 font-medium text-gray-800 whitespace-nowrap">{s.name}</td>
                        <td className="px-3 py-3 text-center text-lg leading-none">
                          <PositionBadge pos={s.league_position} total={s.total_teams} />
                        </td>
                        <td className="px-3 py-3 text-center text-[#009C3B] font-bold">{s.wins}</td>
                        <td className="px-3 py-3 text-center text-gray-500 hidden sm:table-cell">{s.draws}</td>
                        <td className="px-3 py-3 text-center text-red-500">{s.losses}</td>
                        <td className={`px-3 py-3 text-center font-medium hidden sm:table-cell ${gd > 0 ? 'text-[#009C3B]' : gd < 0 ? 'text-red-500' : 'text-gray-400'}`}>
                          {gd > 0 ? `+${gd}` : gd}
                        </td>
                        <td className="px-3 py-3 text-center font-black text-[#002776]">{pts}</td>
                        <td className="px-3 py-3 text-center tabular-nums text-gray-600 hidden sm:table-cell">{ptsRate != null ? `${ptsRate}%` : '—'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${winPct >= 50 ? 'bg-[#009C3B]/10 text-[#009C3B]' : 'bg-red-50 text-red-500'}`}>
                            {winPct}%
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            </div>
          </section>
        )}

        {/* Goalkeepers — Brazuka only */}
        {teamId === 1 && (
          <section>
            <SectionLabel>Goalkeepers</SectionLabel>
            <GoalkeeperTable goalkeepers={goalkeepers} />
          </section>
        )}

        {/* ELO Division Rankings */}
        {eloRankings.length > 0 && (
          <section>
            <SectionLabel>Division ELO Rankings</SectionLabel>
            <p className="text-gray-400 text-xs mb-3">
              {teamId === 2
                ? `All-time power ranking across all teams in Receba FC\u2019s Thursday division. Based on ${eloRankings.reduce((s, r) => s + r.games_played, 0) / 2 | 0}+ league games since 2023. Starting ELO: 1000.`
                : `All-time power ranking across all teams in Brazuka\u2019s Tuesday Men\u2019s division. Based on ${eloRankings.reduce((s, r) => s + r.games_played, 0) / 2 | 0}+ league games since 2021. Starting ELO: 1000.`
              }
            </p>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 text-left w-8">#</th>
                    <th className="px-3 py-3 text-left">Team</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">MP</th>
                    <th className="px-4 py-3 text-right">ELO</th>
                  </tr>
                </thead>
                <tbody>
                  {eloRankings.map((r, i) => {
                    const isMyTeam = teamId === 2 ? r.team_name === 'Receba FC' : r.team_name === 'Brazuka US'
                    return (
                      <tr key={r.team_name} className={`${i !== eloRankings.length - 1 ? 'border-b border-gray-100' : ''} ${isMyTeam ? 'bg-[#009C3B]/5' : 'hover:bg-gray-50'}`}>
                        <td className="px-4 py-3 text-gray-400 text-xs tabular-nums">{i + 1}</td>
                        <td className="px-3 py-3 font-medium text-gray-800">
                          {r.team_name}
                          {isMyTeam && <span className="ml-2 text-[10px] font-bold text-[#009C3B] bg-[#009C3B]/10 px-1.5 py-0.5 rounded-full">{teamId === 2 ? 'FC' : 'US'}</span>}
                        </td>
                        <td className="px-3 py-3 text-center text-gray-400 tabular-nums text-xs hidden sm:table-cell">{r.games_played}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`font-black tabular-nums ${isMyTeam ? 'text-[#009C3B]' : 'text-gray-700'}`}>
                            {r.rating.toFixed(0)}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            </div>
          </section>
        )}

        {/* Field Stats */}
        {fieldStats.length > 0 && (
          <section>
            <SectionLabel>Performance by Field</SectionLabel>
            <p className="text-gray-400 text-xs mb-3">All-time results broken down by venue. Min. 5 games.</p>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
              <table className="w-full min-w-[360px] text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 text-left">Campo</th>
                    <th className="px-3 py-3 text-center">MP</th>
                    <th className="px-3 py-3 text-center">W</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">D</th>
                    <th className="px-3 py-3 text-center">L</th>
                    <th className="px-3 py-3 text-center">Win%</th>
                    <th className="px-3 py-3 text-center hidden sm:table-cell">GF/g</th>
                    <th className="px-4 py-3 text-center hidden sm:table-cell">GA/g</th>
                  </tr>
                </thead>
                <tbody>
                  {fieldStats.map((f, i) => {
                    const pct = Math.round(f.winPct * 100)
                    const color = pct >= 55 ? 'text-[#009C3B]' : pct <= 40 ? 'text-red-400' : 'text-gray-700'
                    return (
                      <tr key={f.field} className={`${i !== fieldStats.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
                        <td className="px-4 py-3 font-medium text-gray-800">{f.field}</td>
                        <td className="px-3 py-3 text-center text-gray-400 tabular-nums text-xs">{f.played}</td>
                        <td className="px-3 py-3 text-center text-[#009C3B] tabular-nums text-xs font-medium">{f.wins}</td>
                        <td className="px-3 py-3 text-center text-gray-400 tabular-nums text-xs hidden sm:table-cell">{f.draws}</td>
                        <td className="px-3 py-3 text-center text-red-400 tabular-nums text-xs font-medium">{f.losses}</td>
                        <td className="px-3 py-3 text-center tabular-nums">
                          <span className={`font-black text-sm ${color}`}>{pct}%</span>
                        </td>
                        <td className="px-3 py-3 text-center text-gray-500 tabular-nums text-xs hidden sm:table-cell">{(f.gf / f.played).toFixed(1)}</td>
                        <td className="px-4 py-3 text-center text-gray-500 tabular-nums text-xs hidden sm:table-cell">{(f.ga / f.played).toFixed(1)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            </div>
          </section>
        )}

        <footer className="text-center text-gray-300 text-xs pb-4">
          🇧🇷 BRAZUKA & RECEBA FC · Seattle
        </footer>

      </div>
    </main>
  )
}
