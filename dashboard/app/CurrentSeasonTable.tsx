'use client'

import type { DivisionStanding, TeamProjection } from '@/lib/data'

const BRAZUKA_NAMES = ['brazuka us', 'brazuka']
const RECEBA_NAMES  = ['receba fc', 'receba']

function isBrazuka(team: string) {
  return BRAZUKA_NAMES.some(n => team.toLowerCase().includes(n))
}
function isReceba(team: string) {
  return RECEBA_NAMES.some(n => team.toLowerCase().includes(n))
}
function isMyTeam(team: string, teamId: number) {
  return teamId === 2 ? isReceba(team) : isBrazuka(team)
}

function GdCell({ gd }: { gd: number }) {
  const color = gd > 0 ? 'text-[#009C3B]' : gd < 0 ? 'text-red-500' : 'text-gray-400'
  return <span className={`tabular-nums font-medium ${color}`}>{gd > 0 ? `+${gd}` : gd}</span>
}

function ProjCell({ proj, n }: { proj: TeamProjection | undefined; n: number }) {
  if (!proj) return <span className="text-gray-300">—</span>
  const { projPosMedian: pos } = proj

  const top3    = pos <= 3
  const bottom3 = pos > n - 3
  const colorCls = top3    ? 'bg-[#009C3B]/10 text-[#009C3B] border-[#009C3B]/20'
                 : bottom3 ? 'bg-red-50 text-red-500 border-red-200'
                 :           'bg-gray-100 text-gray-500 border-gray-200'
  const medal = pos === 1 ? '🥇' : pos === 2 ? '🥈' : pos === 3 ? '🥉' : null

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-bold tabular-nums ${colorCls}`}>
      {medal && <span className="text-[11px]">{medal}</span>}
      {pos}<span className="font-normal opacity-50">/{n}</span>
    </span>
  )
}

export default function CurrentSeasonTable({
  standings,
  projections,
  teamId = 1,
}: {
  standings:   DivisionStanding[]
  projections: TeamProjection[]
  teamId?:     number
}) {
  if (standings.length === 0) return null

  const projMap = new Map(projections.map(p => [p.team, p]))
  const n = standings[0].totalTeams
  const seasonName = standings[0].seasonName

  return (
    <div className="space-y-1">
      <p className="text-gray-400 text-xs mb-3">
        {seasonName} · {n} teams · Projection based on 10 000 simulations using ELO ratings for remaining fixtures.
      </p>
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-[10px] text-gray-400 uppercase tracking-wider">
              <th className="px-3 py-3 text-center w-8">#</th>
              <th className="px-3 py-3 text-left">Team</th>
              <th className="px-2 py-3 text-center">MP</th>
              <th className="px-2 py-3 text-center">W</th>
              <th className="px-2 py-3 text-center">D</th>
              <th className="px-2 py-3 text-center">L</th>
              <th className="px-2 py-3 text-center hidden sm:table-cell">GF</th>
              <th className="px-2 py-3 text-center hidden sm:table-cell">GA</th>
              <th className="px-2 py-3 text-center">GD</th>
              <th className="px-2 py-3 text-center font-black text-[#002776]">Pts</th>
              <th className="px-3 py-3 text-right">Proj. Finish</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((s, i) => {
              const mine = isMyTeam(s.team, teamId)
              const isLast = i === standings.length - 1
              const proj = projMap.get(s.team)
              return (
                <tr
                  key={s.team}
                  className={`${!isLast ? 'border-b border-gray-100' : ''} ${mine ? 'bg-[#009C3B]/5' : 'hover:bg-gray-50'} transition-colors`}
                >
                  <td className="px-3 py-3 text-center text-gray-400 text-xs tabular-nums">
                    {s.pos === 1 ? '🥇' : s.pos === 2 ? '🥈' : s.pos === 3 ? '🥉' : s.pos}
                  </td>
                  <td className="px-3 py-3">
                    <span className={`font-medium ${mine ? 'text-[#009C3B]' : 'text-gray-800'}`}>
                      {s.team}
                    </span>
                    {mine && (
                      <span className="ml-2 text-[9px] font-bold text-[#009C3B] bg-[#009C3B]/10 px-1.5 py-0.5 rounded-full">US</span>
                    )}
                  </td>
                  <td className="px-2 py-3 text-center text-gray-400 tabular-nums">{s.mp}</td>
                  <td className="px-2 py-3 text-center text-[#009C3B] font-bold tabular-nums">{s.w}</td>
                  <td className="px-2 py-3 text-center text-gray-400 tabular-nums">{s.d}</td>
                  <td className="px-2 py-3 text-center text-red-500 tabular-nums">{s.l}</td>
                  <td className="px-2 py-3 text-center text-gray-500 tabular-nums hidden sm:table-cell">{s.gf}</td>
                  <td className="px-2 py-3 text-center text-gray-500 tabular-nums hidden sm:table-cell">{s.ga}</td>
                  <td className="px-2 py-3 text-center"><GdCell gd={s.gd} /></td>
                  <td className="px-2 py-3 text-center font-black text-[#002776] tabular-nums">{s.pts}</td>
                  <td className="px-3 py-3 text-right">
                    <ProjCell proj={proj} n={n} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <div className="px-4 py-2.5 bg-gray-50 text-gray-400 text-[10px] border-t border-gray-100">
          Proj. Finish = most likely final position based on 10 000 simulations using ELO win probabilities for remaining fixtures.
        </div>
      </div>
    </div>
  )
}
