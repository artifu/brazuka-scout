'use client'

import { useState, useCallback } from 'react'
import { getPlayerProfile, type PlayerProfile, type WithWithoutStats } from '@/lib/data'

type GK = {
  id: number
  name: string
  mp: number
  wins: number
  draws: number
  losses: number
  gc: number
  gcPerGame: number | null
  winPct: number | null
  ptsRate: number | null
}

const BADGE_SHORT_LABEL: Record<string, string> = {
  hattrick:           'Hat Trick',
  poker:              'Poker',
  manita:             'Manita',
  garcom:             'Garçom',
  champ_winter1_2024: '1st Title',
  champ_winter2_2024: '2nd Title',
  champ_spring_2025:  '3rd Title',
  champ_summer_2025:  '4th Title',
  victus:             'Victus',
  victus_ii:          'Victus II',
  yellow_card:        'Yellow Card',
  blue_card:          'Blue Card',
  injury:             'Tipo Ronaldo',
  love_doping:        'Love Doping',
  rat_trick:          'Rat Trick',
  sitter_misser:      'Sitter Misser',
  shoot_fofo:         'Shoot Fofo',
  stylish_shorts:     'Stylish Shorts',
  sleepy_gus:         'Sleepy Gus',
  cordiality:         'Cordiality',
  little_roll:        'Little Roll',
  tip_toe:            'Tip Toe',
  friend:             'Friend',
  orbit:              'Orbit',
  hunger:             'Hunger',
  famine:             'Famine',
  saci:               'Saci',
  glass_bones:        'Glass Bones',
}

function StatPill({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className={`flex flex-col items-center px-3 py-2 rounded-lg ${highlight ? 'bg-[#009C3B]/8' : 'bg-gray-50'}`}>
      <span className="text-[10px] uppercase tracking-widest text-gray-400 mb-0.5">{label}</span>
      <span className={`text-base font-black tabular-nums ${highlight ? 'text-[#009C3B]' : 'text-gray-700'}`}>{value}</span>
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
        <StatPill label="MP"     value={mp} />
        <StatPill label="Win%"   value={`${winPct}%`} highlight />
        <StatPill label="W/D/L"  value={`${wins}·${draws}·${losses}`} />
        <StatPill label="Gls/MP" value={gfPerGame.toFixed(2)} />
        <StatPill label="GA/MP"  value={gaPerGame.toFixed(2)} />
      </div>
    </div>
  )
}

function BadgeShelf({ badges }: { badges: PlayerProfile['badges'] }) {
  if (badges.length === 0) return <p className="text-xs text-gray-300 italic">No badges yet</p>
  const grouped: Record<string, { icon: string; name: string; description: string; count: number }> = {}
  for (const b of badges) {
    if (!grouped[b.slug]) grouped[b.slug] = { icon: b.icon, name: b.name, description: b.description, count: 0 }
    grouped[b.slug].count++
  }
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(grouped).map(([slug, { name, description, count }]) => (
        <div key={slug} className="relative group">
          <div className="flex flex-col items-center gap-1 px-2.5 py-1.5 bg-amber-50 border border-amber-200 rounded-lg cursor-default select-none hover:bg-amber-100 transition-colors">
            <div className="flex items-center gap-1">
              <img src={`/badges/${slug}.svg`} alt={name} className="w-8 h-8" />
              {count > 1 && <span className="text-[10px] font-black text-amber-700 tabular-nums">×{count}</span>}
            </div>
            <span className="text-[8px] font-bold text-amber-900 leading-none tracking-wide">
              {BADGE_SHORT_LABEL[slug] ?? name}
            </span>
          </div>
          <div className="pointer-events-none absolute bottom-full left-0 mb-2 z-[9999] opacity-0 group-hover:opacity-100 transition-opacity duration-150 w-48">
            <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl">
              <p className="font-bold leading-snug">{name}{count > 1 ? ` ×${count}` : ''}</p>
              <p className="text-gray-300 mt-1 leading-snug">{description}</p>
            </div>
            <div className="w-2 h-2 bg-gray-900 rotate-45 mx-auto -mt-1" />
          </div>
        </div>
      ))}
    </div>
  )
}

function PlayerProfilePanel({ playerId }: { playerId: number }) {
  const [profile, setProfile] = useState<PlayerProfile | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetched, setFetched] = useState(false)

  const load = useCallback(async () => {
    if (fetched) return
    setLoading(true)
    const p = await getPlayerProfile(playerId, 1)
    setProfile(p)
    setLoading(false)
    setFetched(true)
  }, [playerId, fetched])

  if (!fetched && !loading) load()

  if (loading || !profile) {
    return (
      <div className="px-5 py-4 flex items-center gap-2 text-gray-400 text-xs">
        <span className="animate-spin">⏳</span> Loading…
      </div>
    )
  }

  return (
    <div className="px-5 py-4 space-y-4 bg-gray-50/80 border-t border-gray-100">
      {profile.withStats !== null ? (
        <div className="flex flex-col sm:flex-row gap-4">
          <WithWithoutBlock stats={profile.withStats}    label="With player" />
          <div className="hidden sm:block w-px bg-gray-200 self-stretch" />
          <WithWithoutBlock stats={profile.withoutStats} label="Without player" />
        </div>
      ) : (
        <p className="text-xs text-gray-400 italic">Appearance tracking not yet available for this player.</p>
      )}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mb-2">Achievements</p>
        <BadgeShelf badges={profile.badges} />
      </div>
    </div>
  )
}

export default function GoalkeeperTable({ goalkeepers }: { goalkeepers: GK[] }) {
  const [expanded, setExpanded] = useState<number | null>(null)

  function toggle(id: number) {
    setExpanded(prev => prev === id ? null : id)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-visible shadow-sm">
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
          {goalkeepers.map((gk, i) => {
            const isExpanded = expanded === gk.id
            const isLast = i === goalkeepers.length - 1
            return (
              <>
                <tr
                  key={gk.id}
                  onClick={() => toggle(gk.id)}
                  className={`cursor-pointer hover:bg-gray-50 group transition-colors ${isExpanded ? 'bg-gray-50' : ''} ${!isExpanded && !isLast ? 'border-b border-gray-100' : ''}`}
                >
                  <td className={`py-3 font-medium transition-all ${isExpanded ? 'pl-[10px] pr-3 border-l-2 border-[#009C3B]' : 'px-5 border-l-2 border-transparent'}`}>
                    <span className={`${isExpanded ? 'text-[#009C3B]' : 'text-gray-800'} group-hover:underline underline-offset-2 decoration-dotted decoration-gray-400`}>
                      {gk.name}
                    </span>
                  </td>
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

                {isExpanded && (
                  <tr key={`${gk.id}-profile`} className={!isLast ? 'border-b border-gray-100' : ''}>
                    <td colSpan={6} className="p-0">
                      <PlayerProfilePanel playerId={gk.id} />
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
      <div className="px-5 py-2.5 bg-gray-50 text-gray-400 text-xs border-t border-gray-100">
        Stats based on games where GK appearance was recorded. No PK data available yet.
      </div>
    </div>
  )
}
