/**
 * Nákupy a predaje na zvislé čiary v grafe ceny (`PriceHistoryChart`).
 *
 * Detail setu ich skladá z vlastných kusov (`eventsFromPieces`), karta série
 * ich dostane zo servera (`SeriesValueOut.events`) v tom istom tvare.
 */

export interface ChartEvent {
  /** Deň `RRRR-MM-DD`. */
  day: string
  kind: 'buy' | 'sell' | string
  count: number
  /** Súčet kúpnych, pri predaji predajných cien. */
  amount: string | number | null
}

interface Piece {
  status: string
  purchase_date?: string | null
  purchase_price_eur?: string | null
  sold_date?: string | null
  sold_price_eur?: string | null
}

/** Kusy zoskupené po dňoch nákupu a predaja, zoradené podľa dňa. */
export function eventsFromPieces (pieces: Piece[]): ChartEvent[] {
  const grouped = new Map<string, { day: string, kind: string, count: number, sum: number }>()
  function add (day: string | null | undefined, kind: string, price: string | null | undefined): void {
    if (!day) {
      return
    }
    const key = `${day.slice(0, 10)}|${kind}`
    const found = grouped.get(key) ?? { day: day.slice(0, 10), kind, count: 0, sum: 0 }
    found.count += 1
    found.sum += Number(price ?? 0) || 0
    grouped.set(key, found)
  }
  for (const piece of pieces) {
    add(piece.purchase_date, 'buy', piece.purchase_price_eur)
    if (piece.status === 'sold') {
      add(piece.sold_date, 'sell', piece.sold_price_eur)
    }
  }
  return [...grouped.values()]
    .toSorted((a, b) => a.day.localeCompare(b.day) || a.kind.localeCompare(b.kind))
    .map(e => ({ day: e.day, kind: e.kind, count: e.count, amount: e.sum.toFixed(2) }))
}
