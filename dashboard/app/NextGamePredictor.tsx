'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import type { NextGame } from '@/lib/data'

// ── Model constants (calibrated on 873 division games 2021-2025) ───────────
const INTERCEPT = -0.321
const SLOPE     = 0.0070
const DRAW_RATE = 0.096

function sigmoid(x: number) { return 1 / (1 + Math.exp(-x)) }

function predict(brazukaElo: number, oppElo: number, isHome: boolean) {
  const diff = isHome ? brazukaElo - oppElo : oppElo - brazukaElo
  const pHomeWin = sigmoid(INTERCEPT + SLOPE * diff)
  const pDraw    = DRAW_RATE
  const pWin     = isHome ? pHomeWin : Math.max(0, 1 - pHomeWin - pDraw)
  const pLoss    = Math.max(0, 1 - pWin - pDraw)
  return { win: pWin, draw: pDraw, loss: pLoss }
}

// ── Types ──────────────────────────────────────────────────────────────────
type EloTeam = { team_name: string; rating: number }
type H2H = {
  played: number; wins: number; draws: number; losses: number; gf: number; ga: number
  recent: { date: string; result: 'win' | 'draw' | 'loss'; score: string | null; homeOrAway: 'home' | 'away' }[]
} | null

// ── Outcome card ───────────────────────────────────────────────────────────
function OutcomeCard({ label, prob, bg, text }: { label: string; prob: number; bg: string; text: string }) {
  const pct = Math.round(prob * 100)
  return (
    <div className={`flex-1 rounded-xl border ${bg} border-opacity-40 p-4 flex flex-col gap-2`}>
      <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">{label}</span>
      <div className="flex items-end gap-1">
        <span className="text-4xl font-black tabular-nums text-gray-800">{pct}</span>
        <span className="text-xl font-bold text-gray-400 mb-0.5">%</span>
      </div>
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${text.replace('text-', 'bg-')}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ── Result badge ───────────────────────────────────────────────────────────
function MiniResult({ result }: { result: 'win' | 'draw' | 'loss' }) {
  const s = { win: 'bg-[#009C3B] text-white', draw: 'bg-[#FFDF00] text-[#111]', loss: 'bg-red-500 text-white' }[result]
  return <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-black shrink-0 ${s}`}>{result[0].toUpperCase()}</span>
}

// ── Game picker dropdown ────────────────────────────────────────────────────
function GamePicker({ games, selectedIdx }: { games: NextGame[]; selectedIdx: number }) {
  const router = useRouter()
  const params = useSearchParams()

  if (games.length <= 1) return null

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = new URLSearchParams(params.toString())
    next.set('game', e.target.value)
    router.push(`?${next.toString()}`)
  }

  return (
    <select
      value={selectedIdx}
      onChange={handleChange}
      className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 bg-white cursor-pointer hover:border-gray-300 focus:outline-none focus:ring-1 focus:ring-[#009C3B]/40"
    >
      {games.map((g, i) => {
        const d = new Date(g.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        return (
          <option key={i} value={i}>
            {i === 0 ? `Next · ` : ''}{d} vs {g.opponent}
          </option>
        )
      })}
    </select>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────
export default function NextGamePredictor({
  nextGame, h2h, eloTeams, brazukaElo, upcomingGames, selectedIdx,
}: {
  nextGame: NextGame
  h2h: H2H
  eloTeams: EloTeam[]
  brazukaElo: number
  upcomingGames: NextGame[]
  selectedIdx: number
}) {
  const opp     = eloTeams.find(t => t.team_name.toLowerCase().includes(nextGame.opponent.toLowerCase().split(' ')[0].toLowerCase()))
  const oppElo  = opp?.rating ?? 1000
  const isHome  = nextGame.homeOrAway === 'home'
  const { win, draw, loss } = predict(brazukaElo, oppElo, isHome)

  const eloDiff    = brazukaElo - oppElo
  const eloDiffStr = eloDiff >= 0 ? `+${eloDiff.toFixed(0)}` : `${eloDiff.toFixed(0)}`
  const advantage  = Math.abs(eloDiff) < 25 ? 'even matchup' : eloDiff > 0 ? 'Brazuka favoured' : 'Brazuka underdog'

  const dateStr = new Date(nextGame.date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">

      {/* Game header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-lg font-black text-gray-800">{nextGame.opponent}</span>
            <span className="text-xs text-gray-400">{isHome ? '🏠 Home' : '✈️ Away'}</span>
            <GamePicker games={upcomingGames} selectedIdx={selectedIdx} />
          </div>
          <div className="text-gray-400 text-sm mt-0.5">
            {dateStr}{nextGame.field ? ` · ${nextGame.field}` : ''}
          </div>
        </div>
        <div className="text-right text-xs text-gray-400 space-y-0.5">
          <div>Brazuka <span className="font-bold text-[#009C3B]">{brazukaElo.toFixed(0)}</span></div>
          <div>{nextGame.opponent.split(' ')[0]} <span className="font-bold text-gray-600">{oppElo.toFixed(0)}{!opp ? ' (est.)' : ''}</span></div>
          <div className={`font-semibold ${eloDiff > 25 ? 'text-[#009C3B]' : eloDiff < -25 ? 'text-red-500' : 'text-gray-400'}`}>
            {eloDiffStr} ELO · {advantage}
          </div>
        </div>
      </div>

      {/* Probability bar */}
      <div className="h-2 flex">
        <div className="bg-[#009C3B] transition-all" style={{ width: `${win * 100}%` }} />
        <div className="bg-[#FFDF00] transition-all"  style={{ width: `${draw * 100}%` }} />
        <div className="bg-red-500 transition-all"    style={{ width: `${loss * 100}%` }} />
      </div>

      {/* Outcome cards */}
      <div className="p-4 flex gap-3">
        <OutcomeCard label="Win"  prob={win}  bg="border-green-200"  text="text-[#009C3B]" />
        <OutcomeCard label="Draw" prob={draw} bg="border-yellow-200" text="text-yellow-500" />
        <OutcomeCard label="Loss" prob={loss} bg="border-red-100"    text="text-red-500" />
      </div>

      {/* H2H history */}
      {h2h && h2h.played > 0 ? (
        <div className="border-t border-gray-100 px-5 py-4">
          <div className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-3">Head to Head</div>
          <div className="flex items-center gap-6 flex-wrap mb-4">
            <div className="text-center">
              <div className="text-2xl font-black text-[#009C3B]">{h2h.wins}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wide">Wins</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-[#b89a00]">{h2h.draws}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wide">Draws</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-red-500">{h2h.losses}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wide">Losses</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-gray-700 tabular-nums">{h2h.gf}–{h2h.ga}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wide">Goals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-[#002776]">{h2h.played}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wide">Played</div>
            </div>
          </div>

          {/* Recent results */}
          <div className="space-y-1.5">
            {h2h.recent.map((g, i) => {
              const d = new Date(g.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
              return (
                <div key={i} className="flex items-center gap-2.5 text-sm">
                  <MiniResult result={g.result} />
                  <span className="text-gray-400 text-xs w-24 shrink-0">{d}</span>
                  {g.score && <span className="font-bold tabular-nums text-gray-700">{g.score}</span>}
                  <span className="text-gray-300 text-xs">{g.homeOrAway}</span>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="border-t border-gray-100 px-5 py-3 text-gray-400 text-xs">
          No previous meetings found in our records.
        </div>
      )}

      <div className="px-5 py-2 bg-gray-50 border-t border-gray-100 text-gray-400 text-xs">
        ELO model · calibrated on 873 division games (2021–2025) · draw rate ~10%
      </div>
    </div>
  )
}
