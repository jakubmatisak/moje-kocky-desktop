/**
 * Zisk za zvolené obdobie grafu portfólia (Prehľad: 6M, 1R, od–do).
 *
 * Z bodu na začiatku a na konci obdobia: nerealizovaný zisk vtedy a teraz
 * (v % z vloženého) a jeho zmena v eurách. Peniaze dokúpené počas obdobia
 * nie sú zisk, preto sa ráta zmena zisku, nie zmena hodnoty; do základu na
 * percentá sa ale pripočítajú (hodnota na začiatku + nové vklady). Predaje
 * v období sú zvlášť: realizovaný a nerealizovaný zisk sa nesčítavajú.
 */

import type { TimelinePoint } from '@/api/types'
import { toNumber } from '@/utils/format'

export interface PeriodChange {
  startDay: string
  endDay: string
  /** Zmena nerealizovaného zisku v eurách. */
  change: number
  /** Zmena v % zo základu (hodnota na začiatku + nové vklady); bez základu null. */
  pct: number | null
  /** Nerealizovaný zisk v % z vloženého na začiatku a na konci. */
  pctStart: number | null
  pctEnd: number | null
  /** Čo priniesli predaje počas obdobia (výnos, nie zisk). */
  sold: number
}

type Point = Pick<TimelinePoint, 'day' | 'invested' | 'market_value' | 'proceeds'>

function dayMs (day: string): number {
  return new Date(`${day.slice(0, 10)}T00:00:00`).getTime()
}

/** Bez obdobia (celá história) alebo s jediným bodom v ňom nič. */
export function periodChange (points: Point[], from: number | null, to: number | null): PeriodChange | null {
  if (from === null && to === null) {
    return null
  }
  const sorted = points.toSorted((a, b) => dayMs(a.day) - dayMs(b.day))
  if (sorted.length < 2) {
    return null
  }
  const before = sorted.filter(p => from === null || dayMs(p.day) <= from)
  const start = before.at(-1) ?? sorted[0]
  const end = sorted.findLast(p => to === null || dayMs(p.day) <= to)
  if (!start || !end || dayMs(end.day) <= dayMs(start.day)) {
    return null
  }

  const num = (value: string | null | undefined): number => toNumber(value) ?? 0
  const investedStart = num(start.invested)
  const investedEnd = num(end.invested)
  const valueStart = num(start.market_value)
  const valueEnd = num(end.market_value)
  const gainStart = valueStart - investedStart
  const gainEnd = valueEnd - investedEnd
  const change = gainEnd - gainStart
  const base = valueStart + Math.max(0, investedEnd - investedStart)
  return {
    startDay: start.day.slice(0, 10),
    endDay: end.day.slice(0, 10),
    change,
    pct: base > 0 ? change / base * 100 : null,
    pctStart: investedStart > 0 ? gainStart / investedStart * 100 : null,
    pctEnd: investedEnd > 0 ? gainEnd / investedEnd * 100 : null,
    sold: num(end.proceeds) - num(start.proceeds),
  }
}
