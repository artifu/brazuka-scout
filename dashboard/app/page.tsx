import { getGames, getTopScorers, getOverallRecord, getSeasons } from '@/lib/data'

export const revalidate = 60

function ResultBadge({ result }: { result: string }) {
  const styles: Record<string, string> = {
    win:  'bg-green-500/20 text-green-400 border border-green-500/30',
    loss: 'bg-red-500/20 text-red-400 border border-red-500/30',
    draw: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  }
  const labels: Record<string, string> = { win: 'W', loss: 'L', draw: 'D' }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${styles[result] ?? 'bg-gray-700 text-gray-400'}`}>
      {labels[result] ?? '?'}
    </span>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-1">
      <span className="text-gray-500 text-xs uppercase tracking-widest">{label}</span>
      <span className="text-3xl font-bold text-white">{value}</span>
      {sub && <span className="text-gray-500 text-xs">{sub}</span>}
    </div>
  )
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ season?: string }>
}) {
  const { season } = await searchParams
  const seasonId = season ? parseInt(season) : undefined

  const [games, scorers, record, seasons] = await Promise.all([
    getGames(seasonId),
    getTopScorers(seasonId),
    getOverallRecord(seasonId),
    getSeasons(),
  ])

  const total = record.wins + record.losses + record.draws
  const winPct = total > 0 ? Math.round((record.wins / total) * 100) : 0
  const activeSeason = seasons.find(s => s.id === seasonId) ?? seasons[0]

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">⚽</span>
            <h1 className="text-2xl font-black tracking-tight">BRAZUKA & RECEBA FC</h1>
          </div>
          <p className="text-gray-500 text-sm ml-11">Tuesday Men&apos;s D · Magnuson Park, Seattle</p>

          {/* Season selector */}
          <div className="mt-5 ml-11 flex items-center gap-2 flex-wrap">
            {seasons.map(s => (
              <a
                key={s.id}
                href={`/?season=${s.id}`}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  (seasonId ? s.id === seasonId : s.id === seasons[0]?.id)
                    ? 'bg-green-500/20 text-green-400 border-green-500/40'
                    : 'text-gray-500 border-gray-700 hover:border-gray-500'
                }`}
              >
                {s.name}
              </a>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-10">

        <section>
          <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-4">Season Record</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Wins" value={record.wins} />
            <StatCard label="Losses" value={record.losses} />
            <StatCard label="Draws" value={record.draws} />
            <StatCard label="Win Rate" value={`${winPct}%`} sub={`${total} games played`} />
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <StatCard label="Goals Scored" value={record.goalsFor} sub="known games only" />
            <StatCard label="Goals Conceded" value={record.goalsAgainst} sub="known games only" />
          </div>
        </section>

        <section>
          <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-4">Top Scorers</h2>
          {scorers.length === 0 ? (
            <p className="text-gray-600 text-sm">No scorer data yet.</p>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              {scorers.map((s, i) => (
                <div key={s.player} className={`flex items-center gap-4 px-5 py-3 ${i !== scorers.length - 1 ? 'border-b border-gray-800' : ''}`}>
                  <span className="text-gray-600 text-sm w-5 text-right">{i + 1}</span>
                  <span className="flex-1 font-medium">{s.player}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${Math.max(8, (s.goals / scorers[0].goals) * 80)}px` }} />
                    <span className="text-green-400 font-bold tabular-nums w-6 text-right">{s.goals}</span>
                    <span className="text-gray-600 text-xs">⚽</span>
                  </div>
                </div>
              ))}
              <div className="px-5 py-2 bg-gray-800/50 text-gray-600 text-xs">
                ⚠ Only includes games where scorers were recorded — most games have missing scorer data.
              </div>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-4">Recent Games</h2>
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            {games.map((g, i) => {
              const score = g.score_brazuka != null
                ? `${g.score_brazuka} – ${g.score_opponent ?? '?'}`
                : 'Forfeit'
              const date = new Date(g.game_date + 'T12:00:00').toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric'
              })
              return (
                <div key={g.id} className={`flex items-center gap-3 px-5 py-3.5 ${i !== games.length - 1 ? 'border-b border-gray-800' : ''}`}>
                  <ResultBadge result={g.result} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{g.opponent}</span>
                      <span className="text-gray-600 text-xs">{g.home_or_away === 'home' ? '🏠' : '✈️'}</span>
                    </div>
                    <div className="text-gray-600 text-xs mt-0.5">
                      {date}
                      {g.venue && <span className="ml-2 text-gray-700">· {g.field ?? g.venue}</span>}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold tabular-nums">{score}</div>
                    {!g.scorers_known && g.score_brazuka != null && (
                      <div className="text-gray-600 text-xs">scorers unknown</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

      </div>
    </main>
  )
}
