/**
 * Obdobie grafu: rýchle voľby (1M až Všetko) a orezanie krivky na obdobie.
 *
 * Výber obdobia s poľami od–do je `composables/useChartRange.ts`, používa ho
 * portfólio na Prehľade aj graf ceny v detailoch.
 */

export type RangePreset = '1m' | '3m' | '6m' | '1y' | 'ytd' | 'all'

export const RANGE_PRESETS: RangePreset[] = ['1m', '3m', '6m', '1y', 'ytd', 'all']

function startOfDay (ms: number): number {
  const d = new Date(ms)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

/** Rozsah pre rýchlu voľbu, počítaný od `now`; Všetko je bez hraníc. */
export function presetRange (value: RangePreset, now: number): [number | null, number | null] {
  const back = (months: number): number => {
    const d = new Date(now)
    d.setMonth(d.getMonth() - months)
    return startOfDay(d.getTime())
  }
  switch (value) {
    case '1m': { return [back(1), now] }
    case '3m': { return [back(3), now] }
    case '6m': { return [back(6), now] }
    case '1y': { return [back(12), now] }
    case 'ytd': { return [new Date(new Date(now).getFullYear(), 0, 1).getTime(), now] }
    default: { return [null, null] }
  }
}

interface XY { x: number, y: number }

/** Hodnota v čase `at` na úsečke medzi dvoma bodmi. */
function between (a: XY, b: XY, at: number): XY {
  const share = b.x === a.x ? 0 : (at - a.x) / (b.x - a.x)
  return { x: at, y: a.y + (b.y - a.y) * share }
}

/**
 * Body krivky v období. Na okraji, kde krivka pokračuje aj mimo obdobia,
 * pribudne bod dopočítaný z bodov okolo, inak by krivka v období začínala
 * až prvou cenou v ňom (a pri riedkej histórii by v mesiaci nebolo nič).
 * Pred prvou a za poslednou cenou sa nič nedomýšľa.
 */
export function clipSeries (points: XY[], from: number | null, to: number | null): XY[] {
  const lo = from ?? Number.NEGATIVE_INFINITY
  const hi = to ?? Number.POSITIVE_INFINITY
  const inside = points.filter(p => p.x >= lo && p.x <= hi)
  const out: XY[] = []

  const before = points.findLast(p => p.x < lo)
  const afterStart = points.find(p => p.x >= lo)
  if (before && afterStart && afterStart.x > lo) {
    out.push(between(before, afterStart, lo))
  }
  out.push(...inside)
  const after = points.find(p => p.x > hi)
  const beforeEnd = points.findLast(p => p.x <= hi)
  if (after && beforeEnd && beforeEnd.x < hi) {
    out.push(between(beforeEnd, after, hi))
  }
  return out
}
