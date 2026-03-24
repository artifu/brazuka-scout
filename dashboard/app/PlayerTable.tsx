'use client'

import { useState, useCallback } from 'react'
import { getPlayerProfile, type PlayerProfile, type WithWithoutStats } from '@/lib/data'

type Player = {
  player: string
  playerId: number | null
  goals: number
  assists: number
  gamesPlayed: number | null
  contributions: number
  participationRate: number | null
  gpInferred: boolean
  winLift: number | null
  winLiftPValue: number | null
  winLiftConfidence: string | null
}

type SortKey = 'contributions' | 'goals' | 'assists' | 'gamesPlayed' | 'participationRate' | 'winLift'

const CONFIDENCE_DOT: Record<string, { dot: string; label: string }> = {
  high:        { dot: '●', label: 'High confidence (p < 0.10)' },
  suggestive:  { dot: '◑', label: 'Suggestive (p < 0.25)'      },
  low:         { dot: '○', label: 'Inconclusive (p ≥ 0.25)'    },
}

function WinLiftCell({ winLift, pValue, confidence }: {
  winLift: number | null; pValue: number | null; confidence: string | null
}) {
  if (winLift === null || confidence === null || pValue === null)
    return <span className="text-gray-300">—</span>
  const pct  = Math.round(winLift * 100)
  const sign = pct >= 0 ? '+' : ''
  const c    = CONFIDENCE_DOT[confidence] ?? CONFIDENCE_DOT.low
  const colorCls = pct >= 2 ? 'bg-green-50 text-green-700' : pct <= -1 ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-400'
  return (
    <span title={`${sign}${pct}% win probability when present · ${c.label} · p=${pValue.toFixed(3)}`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-semibold tabular-nums text-xs cursor-default ${colorCls}`}>
      {sign}{pct}%
      <span className="text-[10px] leading-none">{c.dot}</span>
    </span>
  )
}

function StatPill({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
  return (
    <div className={`flex flex-col items-center px-3 py-2 rounded-lg ${highlight ? 'bg-[#009C3B]/8' : 'bg-gray-50'}`}>
      <span className="text-[10px] uppercase tracking-widest text-gray-400 mb-0.5">{label}</span>
      <span className={`text-base font-black tabular-nums ${highlight ? 'text-[#009C3B]' : 'text-gray-700'}`}>{value}</span>
      {sub && <span className="text-[10px] text-gray-400 mt-0.5">{sub}</span>}
    </div>
  )
}

function WithWithoutBlock({ stats, label }: { stats: WithWithoutStats | null; label: string }) {
  if (!stats) return (
    <div className="flex-1 min-w-0">
      <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-2">{label}</p>
      <p className="text-xs text-gray-300 italic">No appearance data yet</p>
    </div>
  )
  const { mp, wins, draws, losses, winPct, gfPerGame, gaPerGame } = stats
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        <StatPill label="MP"      value={mp}               />
        <StatPill label="Win%"    value={`${winPct}%`}     highlight={true} />
        <StatPill label="W/D/L"   value={`${wins}·${draws}·${losses}`} />
        <StatPill label="Gls/MP"  value={gfPerGame.toFixed(2)} />
        <StatPill label="GA/MP"   value={gaPerGame.toFixed(2)} />
      </div>
    </div>
  )
}

function BadgeShelf({ badges }: { badges: PlayerProfile['badges'] }) {
  if (badges.length === 0) return (
    <p className="text-xs text-gray-300 italic">No badges yet</p>
  )
  // Group by slug: show count if multiple
  const grouped: Record<string, { icon: string; name: string; description: string; count: number }> = {}
  for (const b of badges) {
    if (!grouped[b.slug]) grouped[b.slug] = { icon: b.icon, name: b.name, description: b.description, count: 0 }
    grouped[b.slug].count++
  }
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(grouped).map(([slug, { icon, name, description, count }]) => (
        <div key={slug} className="relative group">
          <div className="flex items-center gap-1 px-2.5 py-1.5 bg-amber-50 border border-amber-200 rounded-lg cursor-default select-none hover:bg-amber-100 transition-colors">
            <span className="text-lg leading-none">{icon}</span>
            {count > 1 && (
              <span className="text-[10px] font-black text-amber-700 tabular-nums">×{count}</span>
            )}
          </div>
          {/* Tooltip */}
          <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
              <p className="font-bold">{icon} {name}{count > 1 ? ` ×${count}` : ''}</p>
              <p className="text-gray-300 mt-0.5">{description}</p>
            </div>
            <div className="w-2 h-2 bg-gray-900 rotate-45 mx-auto -mt-1" />
          </div>
        </div>
      ))}
    </div>
  )
}

function PlayerProfilePanel({ playerId, teamId }: { playerId: number; teamId?: number }) {
  const [profile, setProfile] = useState<PlayerProfile | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetched, setFetched] = useState(false)

  const load = useCallback(async () => {
    if (fetched) return
    setLoading(true)
    const p = await getPlayerProfile(playerId, teamId ?? 1)
    setProfile(p)
    setLoading(false)
    setFetched(true)
  }, [playerId, teamId, fetched])

  // Trigger load on mount
  if (!fetched && !loading) load()

  if (loading || !profile) {
    return (
      <div className="px-5 py-4 flex items-center gap-2 text-gray-400 text-xs">
        <span className="animate-spin">⏳</span> Loading…
      </div>
    )
  }

  const hasPresence = profile.withStats !== null

  return (
    <div className="px-5 py-4 space-y-4 bg-gray-50/80 border-t border-gray-100">
      {/* With / Without */}
      {hasPresence && (
        <div className="flex flex-col sm:flex-row gap-4">
          <WithWithoutBlock stats={profile.withStats}    label="With player" />
          <div className="hidden sm:block w-px bg-gray-200 self-stretch" />
          <WithWithoutBlock stats={profile.withoutStats} label="Without player" />
        </div>
      )}
      {!hasPresence && (
        <p className="text-xs text-gray-400 italic">Appearance tracking not yet available for this player.</p>
      )}

      {/* Badges */}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mb-2">Achievements</p>
        <BadgeShelf badges={profile.badges} />
      </div>
    </div>
  )
}

export default function PlayerTable({ players, teamId }: { players: Player[]; teamId?: number }) {
  const [sortKey, setSortKey]       = useState<SortKey>('contributions')
  const [sortDesc, setSortDesc]     = useState(true)
  const [expanded, setExpanded]     = useState<number | null>(null)

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortDesc(d => !d)
    else { setSortKey(key); setSortDesc(true) }
  }

  function toggleExpand(playerId: number | null) {
    if (playerId === null) return
    setExpanded(prev => prev === playerId ? null : playerId)
  }

  const sorted = [...players].sort((a, b) => {
    const av = a[sortKey] ?? -Infinity
    const bv = b[sortKey] ?? -Infinity
    return sortDesc ? (bv as number) - (av as number) : (av as number) - (bv as number)
  })

  function Th({ label, k, title }: { label: string; k: SortKey; title?: string }) {
    const active = sortKey === k
    return (
      <th className={`px-3 py-3 text-center cursor-pointer select-none transition-colors ${active ? 'text-[#009C3B]' : 'text-gray-400 hover:text-gray-600'}`}
        onClick={() => handleSort(k)} title={title}>
        {label}
        <span className="ml-0.5 text-[10px]">{active ? (sortDesc ? '▼' : '▲') : ''}</span>
      </th>
    )
  }

  const medal = (i: number) => i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : null

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs uppercase tracking-wider">
            <th className="px-5 py-3 text-left w-8 text-gray-400">#</th>
            <th className="px-3 py-3 text-left text-gray-400">Player</th>
            <Th label="G"       k="goals"            title="Goals" />
            <Th label="A"       k="assists"          title="Assists" />
            <th className="hidden sm:table-cell px-3 py-3 text-center text-gray-400 cursor-pointer select-none"
              onClick={() => handleSort('contributions')} title="Goals + Assists">
              G+A<span className="ml-0.5 text-[10px]">{sortKey === 'contributions' ? (sortDesc ? '▼' : '▲') : ''}</span>
            </th>
            <Th label="MP"      k="gamesPlayed"      title="Matches Played" />
            <Th label="G+A/MP"  k="participationRate" title="Goal contributions per match" />
            <Th label="Win Lift" k="winLift"          title="Win probability increase when player is present" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((p, i) => {
            const isExpanded = p.playerId !== null && expanded === p.playerId
            const isLast     = i === sorted.length - 1
            return (
              <>
                <tr
                  key={p.player}
                  onClick={() => toggleExpand(p.playerId)}
                  className={`${!isExpanded && !isLast ? 'border-b border-gray-100' : ''} ${p.playerId !== null ? 'cursor-pointer hover:bg-gray-50' : ''} ${isExpanded ? 'bg-gray-50' : ''} transition-colors`}
                >
                  <td className="px-5 py-3 text-gray-400 text-xs tabular-nums text-right">{medal(i) ?? i + 1}</td>
                  <td className="px-3 py-3 font-medium text-gray-800">
                    <span className="flex items-center gap-1.5">
                      {p.player}
                      {p.playerId !== null && (
                        <span className={`text-[10px] transition-transform duration-200 ${isExpanded ? 'rotate-180 text-[#009C3B]' : 'text-gray-300'}`}>▼</span>
                      )}
                    </span>
                  </td>
                  <td className={`px-3 py-3 text-center tabular-nums font-bold ${sortKey === 'goals' ? 'text-[#009C3B]' : 'text-gray-600'}`}>{p.goals}</td>
                  <td className={`px-3 py-3 text-center tabular-nums ${sortKey === 'assists' ? 'text-[#002776] font-bold' : 'text-gray-500'}`}>
                    {p.assists > 0 ? p.assists : <span className="text-gray-300">—</span>}
                  </td>
                  <td className={`hidden sm:table-cell px-3 py-3 text-center tabular-nums font-bold ${sortKey === 'contributions' ? 'text-[#009C3B]' : 'text-gray-600'}`}>{p.contributions}</td>
                  <td className="px-3 py-3 text-center text-gray-400 tabular-nums">
                    {p.gamesPlayed != null
                      ? <>{p.gpInferred && <span className="text-gray-300 text-[10px] mr-0.5">≥</span>}{p.gamesPlayed}</>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums">
                    {p.participationRate != null
                      ? <span className={`font-semibold ${sortKey === 'participationRate' ? 'text-[#009C3B]' : 'text-gray-700'}`}>{p.participationRate.toFixed(2)}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <WinLiftCell winLift={p.winLift} pValue={p.winLiftPValue} confidence={p.winLiftConfidence} />
                  </td>
                </tr>

                {isExpanded && p.playerId !== null && (
                  <tr key={`${p.player}-profile`} className={!isLast ? 'border-b border-gray-100' : ''}>
                    <td colSpan={8} className="p-0">
                      <PlayerProfilePanel playerId={p.playerId} teamId={teamId} />
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
      <div className="px-5 py-2.5 bg-gray-50 text-gray-400 text-xs border-t border-gray-100 flex items-center gap-3 flex-wrap">
        <span>Click a player to see their impact stats and achievements.</span>
        <span className="text-gray-300">·</span>
        <span>MP marked ≥ is inferred from scoring/assisting.</span>
        <span className="text-gray-300">·</span>
        <span>Win Lift: OLS model, controlled for opponent strength &amp; home advantage.</span>
      </div>
    </div>
  )
}
