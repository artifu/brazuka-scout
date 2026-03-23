import { getGames, getTopPlayers, getOverallRecord, getSeasons, getSeasonHistory, getTopOpponents, getEloRankings, getPlayerImpact, getGoalkeeperStats, getUpcomingGames, getHeadToHead, savePrediction } from '@/lib/data'
import PlayerTable from './PlayerTable'
import SeasonFilter from './SeasonFilter'
import NextGamePredictor from './NextGamePredictor'

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

function PositionBadge({ pos }: { pos: number | null }) {
  if (pos === null) return <span className="text-gray-300 text-xs">—</span>
  if (pos === 1) return <span title="1st place">🥇</span>
  if (pos === 2) return <span title="2nd place">🥈</span>
  if (pos === 3) return <span title="3rd place">🥉</span>
  return <span className="text-gray-500 text-xs font-semibold">{pos}</span>
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

  const [games, players, record, seasons, seasonHistory, topOpponents, eloRankings, playerImpact, goalkeepers, upcomingGames] = await Promise.all([
    getGames(seasonId, teamId),
    getTopPlayers(seasonId, teamId),
    getOverallRecord(seasonId, teamId),
    getSeasons(teamId),
    getSeasonHistory(teamId),
    getTopOpponents(teamId, seasonId),
    getEloRankings(),
    getPlayerImpact(),
    getGoalkeeperStats(),
    (!seasonId && teamId === 1) ? getUpcomingGames() : Promise.resolve([] as Awaited<ReturnType<typeof getUpcomingGames>>),
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

  const brazukaElo = eloRankings.find(r => r.team_name === 'Brazuka US')?.rating ?? 1000

  // Snapshot prediction for the next game (upserts — safe to call on every render)
  if (nextGame) {
    const oppElo = eloRankings.find(t => t.team_name.toLowerCase().includes(
      nextGame.opponent.split(' ').filter(w => w.length > 2)[0]?.toLowerCase() ?? ''
    ))?.rating ?? 1000
    savePrediction(nextGame, brazukaElo, oppElo).catch(() => {})
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

        {/* Next Game Predictor — only on all-time view for team 1 */}
        {!seasonId && teamId === 1 && upcomingGames.length > 0 && nextGame && (
          <section>
            <SectionLabel>Next Game</SectionLabel>
            <NextGamePredictor
              nextGame={nextGame}
              h2h={h2h}
              eloTeams={eloRankings}
              brazukaElo={brazukaElo}
              upcomingGames={upcomingGames}
              selectedIdx={gameIdx}
            />
          </section>
        )}

        {/* Top Players */}
        {players.length > 0 && (
          <section>
            <SectionLabel>Top Players</SectionLabel>
            <PlayerTable players={playersWithImpact} />
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
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-5 py-3 text-left">Opponent</th>
                    <th className="px-3 py-3 text-center">P</th>
                    <th className="px-3 py-3 text-center">W</th>
                    <th className="px-3 py-3 text-center">D</th>
                    <th className="px-3 py-3 text-center">L</th>
                    <th className="px-5 py-3 text-right">Record</th>
                  </tr>
                </thead>
                <tbody>
                  {topOpponents.map((o, i) => {
                    const winPct = Math.round((o.wins / o.played) * 100)
                    return (
                      <tr key={o.opponent} className={`${i !== topOpponents.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
                        <td className="px-5 py-3 font-medium text-gray-800">{o.opponent}</td>
                        <td className="px-3 py-3 text-center text-gray-500">{o.played}</td>
                        <td className="px-3 py-3 text-center text-[#009C3B] font-bold">{o.wins}</td>
                        <td className="px-3 py-3 text-center text-gray-400">{o.draws}</td>
                        <td className="px-3 py-3 text-center text-red-500">{o.losses}</td>
                        <td className="px-5 py-3 text-right">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${winPct >= 50 ? 'bg-[#009C3B]/10 text-[#009C3B]' : 'bg-red-50 text-red-500'}`}>
                            {winPct}% wins
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Season by Season — all-time view only */}
        {!seasonId && seasonHistory.length > 0 && (
          <section>
            <SectionLabel>Season by Season</SectionLabel>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-5 py-3 text-left">Season</th>
                    <th className="px-3 py-3 text-center">Pos</th>
                    <th className="px-3 py-3 text-center">W</th>
                    <th className="px-3 py-3 text-center">D</th>
                    <th className="px-3 py-3 text-center">L</th>
                    <th className="px-3 py-3 text-center">GD</th>
                    <th className="px-3 py-3 text-center">Pts</th>
                    <th className="px-3 py-3 text-center">Pts%</th>
                    <th className="px-5 py-3 text-center">Win%</th>
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
                        <td className="px-5 py-3 font-medium text-gray-800">{s.name}</td>
                        <td className="px-3 py-3 text-center text-lg leading-none">
                          <PositionBadge pos={s.league_position} />
                        </td>
                        <td className="px-3 py-3 text-center text-[#009C3B] font-bold">{s.wins}</td>
                        <td className="px-3 py-3 text-center text-gray-500">{s.draws}</td>
                        <td className="px-3 py-3 text-center text-red-500">{s.losses}</td>
                        <td className={`px-3 py-3 text-center font-medium ${gd > 0 ? 'text-[#009C3B]' : gd < 0 ? 'text-red-500' : 'text-gray-400'}`}>
                          {gd > 0 ? `+${gd}` : gd}
                        </td>
                        <td className="px-3 py-3 text-center font-black text-[#002776]">{pts}</td>
                        <td className="px-3 py-3 text-center tabular-nums text-gray-600">{ptsRate != null ? `${ptsRate}%` : '—'}</td>
                        <td className="px-5 py-3 text-center">
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
          </section>
        )}

        {/* Goalkeepers */}
        <section>
          <SectionLabel>Goalkeepers</SectionLabel>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                  <th className="px-5 py-3 text-left">Goalkeeper</th>
                  <th className="px-3 py-3 text-center" title="Matches Played">MP</th>
                  <th className="px-3 py-3 text-center" title="Goals Conceded">GC</th>
                  <th className="px-3 py-3 text-center" title="Goals Conceded per Game">GC/MP</th>
                  <th className="px-3 py-3 text-center" title="Win percentage">Win%</th>
                  <th className="px-5 py-3 text-center" title="Points rate (W=3 D=1 L=0)">Pts%</th>
                </tr>
              </thead>
              <tbody>
                {goalkeepers.map((gk, i) => (
                  <tr key={gk.id} className={`${i !== goalkeepers.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
                    <td className="px-5 py-3 font-medium text-gray-800">{gk.name}</td>
                    <td className="px-3 py-3 text-center text-gray-500 tabular-nums">{gk.mp > 0 ? gk.mp : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-3 text-center tabular-nums text-red-500 font-semibold">{gk.mp > 0 ? gk.gc : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-3 text-center tabular-nums text-gray-600">{gk.gcPerGame != null ? gk.gcPerGame.toFixed(2) : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-3 text-center">
                      {gk.winPct != null
                        ? <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${gk.winPct >= 50 ? 'bg-[#009C3B]/10 text-[#009C3B]' : 'bg-red-50 text-red-500'}`}>{gk.winPct}%</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-5 py-3 text-center">
                      {gk.ptsRate != null
                        ? <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${gk.ptsRate >= 50 ? 'bg-[#002776]/10 text-[#002776]' : 'bg-red-50 text-red-500'}`}>{gk.ptsRate}%</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-5 py-2.5 bg-gray-50 text-gray-400 text-xs border-t border-gray-100">
              Stats based on games where GK appearance was recorded. No PK data available yet.
            </div>
          </div>
        </section>

        {/* ELO Division Rankings */}
        {eloRankings.length > 0 && (
          <section>
            <SectionLabel>Division ELO Rankings</SectionLabel>
            <p className="text-gray-400 text-xs mb-3">All-time power ranking across all teams in Brazuka&apos;s Tuesday Men&apos;s division. Based on {eloRankings.reduce((s, r) => s + r.games_played, 0) / 2 | 0}+ league games since 2021. Starting ELO: 1000.</p>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-5 py-3 text-left w-8">#</th>
                    <th className="px-3 py-3 text-left">Team</th>
                    <th className="px-3 py-3 text-center">MP</th>
                    <th className="px-5 py-3 text-right">ELO</th>
                  </tr>
                </thead>
                <tbody>
                  {eloRankings.map((r, i) => {
                    const isBrazuka = r.team_name === 'Brazuka US'
                    return (
                      <tr key={r.team_name} className={`${i !== eloRankings.length - 1 ? 'border-b border-gray-100' : ''} ${isBrazuka ? 'bg-[#009C3B]/5' : 'hover:bg-gray-50'}`}>
                        <td className="px-5 py-3 text-gray-400 text-xs tabular-nums">{i + 1}</td>
                        <td className="px-3 py-3 font-medium text-gray-800">
                          {r.team_name}
                          {isBrazuka && <span className="ml-2 text-[10px] font-bold text-[#009C3B] bg-[#009C3B]/10 px-1.5 py-0.5 rounded-full">US</span>}
                        </td>
                        <td className="px-3 py-3 text-center text-gray-400 tabular-nums text-xs">{r.games_played}</td>
                        <td className="px-5 py-3 text-right">
                          <span className={`font-black tabular-nums ${isBrazuka ? 'text-[#009C3B]' : 'text-gray-700'}`}>
                            {r.rating.toFixed(0)}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
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
