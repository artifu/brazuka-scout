'use client'

import { useState } from 'react'

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
  winLift: number | null
  pValue: number | null
  confidence: string | null
}) {
  if (winLift === null || confidence === null || pValue === null) {
    return <span className="text-gray-300">—</span>
  }

  const pct = Math.round(winLift * 100)
  const sign = pct >= 0 ? '+' : ''
  const c = CONFIDENCE_DOT[confidence] ?? CONFIDENCE_DOT.low

  // Color by value: green ≥ +2%, red ≤ -1%, grey in between
  const colorCls = pct >= 2
    ? 'bg-green-50 text-green-700'
    : pct <= -1
      ? 'bg-red-50 text-red-600'
      : 'bg-gray-100 text-gray-400'

  const tooltip = `${sign}${pct}% win probability when present · ${c.label} · p=${pValue.toFixed(3)}`

  return (
    <span
      title={tooltip}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-semibold tabular-nums text-xs cursor-default ${colorCls}`}
    >
      {sign}{pct}%
      <span className="text-[10px] leading-none">{c.dot}</span>
    </span>
  )
}

export default function PlayerTable({ players }: { players: Player[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('contributions')
  const [sortDesc, setSortDesc] = useState(true)

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortDesc(d => !d)
    else { setSortKey(key); setSortDesc(true) }
  }

  const sorted = [...players].sort((a, b) => {
    const av = a[sortKey] ?? -Infinity
    const bv = b[sortKey] ?? -Infinity
    return sortDesc ? (bv as number) - (av as number) : (av as number) - (bv as number)
  })

  function Th({ label, k, title }: { label: string; k: SortKey; title?: string }) {
    const active = sortKey === k
    return (
      <th
        className={`px-3 py-3 text-center cursor-pointer select-none transition-colors ${active ? 'text-[#009C3B]' : 'text-gray-400 hover:text-gray-600'}`}
        onClick={() => handleSort(k)}
        title={title}
      >
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
            <Th label="G"      k="goals"            title="Goals" />
            <Th label="A"      k="assists"           title="Assists" />
            <th className="hidden sm:table-cell px-3 py-3 text-center text-gray-400 cursor-pointer select-none" onClick={() => handleSort('contributions')} title="Goals + Assists">
              G+A<span className="ml-0.5 text-[10px]">{sortKey === 'contributions' ? (sortDesc ? '▼' : '▲') : ''}</span>
            </th>
            <Th label="MP"     k="gamesPlayed"       title="Matches Played" />
            <Th label="G+A/MP" k="participationRate" title="Goal contributions per match" />
            <Th label="Win Lift" k="winLift"         title="Win probability increase when player is present (OLS regression, controlled for opponent strength)" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((p, i) => (
            <tr key={p.player} className={`${i !== sorted.length - 1 ? 'border-b border-gray-100' : ''} hover:bg-gray-50`}>
              <td className="px-5 py-3 text-gray-400 text-xs tabular-nums text-right">{medal(i) ?? i + 1}</td>
              <td className="px-3 py-3 font-medium text-gray-800">{p.player}</td>
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
          ))}
        </tbody>
      </table>
      <div className="px-5 py-2.5 bg-gray-50 text-gray-400 text-xs border-t border-gray-100 flex items-center gap-3 flex-wrap">
        <span>Goal &amp; assist data partial — more seasons being parsed from group chat. MP marked ≥ is inferred from scoring/assisting.</span>
        <span className="text-gray-300">·</span>
        <span>Win Lift: OLS model (draw=0.33), controlled for opponent strength &amp; home advantage. Hover for confidence.</span>
      </div>
    </div>
  )
}
