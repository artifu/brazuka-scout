'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

type Season = { id: number; name: string }

export default function SeasonFilter({ seasons, teamId, seasonId }: {
  seasons: Season[]
  teamId: number
  seasonId?: number
}) {
  const router = useRouter()

  // Group seasons by year (last word of name)
  const yearMap: Record<string, Season[]> = {}
  for (const s of seasons) {
    const year = s.name.split(' ').pop() ?? 'Unknown'
    if (!yearMap[year]) yearMap[year] = []
    yearMap[year].push(s)
  }
  const years = Object.keys(yearMap).sort((a, b) => parseInt(b) - parseInt(a))

  // Which year does the current season belong to?
  const currentSeason = seasons.find(s => s.id === seasonId)
  const defaultYear = currentSeason ? (currentSeason.name.split(' ').pop() ?? null) : null
  const [selectedYear, setSelectedYear] = useState<string | null>(defaultYear)

  const seasonsForYear = selectedYear ? (yearMap[selectedYear] ?? []) : []

  const pill = (active: boolean, blue?: boolean) =>
    `px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
      active
        ? blue ? 'bg-[#002776] text-white border-[#002776]' : 'bg-[#009C3B] text-white border-[#009C3B]'
        : 'text-gray-500 border-gray-300 hover:border-[#009C3B] hover:text-[#009C3B]'
    }`

  return (
    <div className="mt-3 space-y-2">
      {/* Row 1: year selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-gray-400 text-xs uppercase tracking-widest w-12 shrink-0">Year</span>
        <button
          className={pill(!selectedYear)}
          onClick={() => { setSelectedYear(null); router.push(`/?team=${teamId}`) }}
        >
          All time
        </button>
        {years.map(y => (
          <button
            key={y}
            className={pill(selectedYear === y, true)}
            onClick={() => setSelectedYear(selectedYear === y ? null : y)}
          >
            {y}
          </button>
        ))}
      </div>

      {/* Row 2: season selector (only when year chosen) */}
      {selectedYear && seasonsForYear.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-400 text-xs uppercase tracking-widest w-12 shrink-0">Season</span>
          {seasonsForYear.map(s => {
            const label = s.name.replace(/\s+\d{4}$/, '') // strip year, show e.g. "Summer"
            return (
              <button
                key={s.id}
                className={pill(s.id === seasonId)}
                onClick={() => router.push(`/?team=${teamId}&season=${s.id}`)}
              >
                {label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
