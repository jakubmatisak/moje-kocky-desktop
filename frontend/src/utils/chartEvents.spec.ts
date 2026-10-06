import { describe, expect, it } from 'vitest'
import { eventsFromPieces } from './chartEvents'

describe('nákupy a predaje na grafe ceny', () => {
  it('kusy sa zoskupia po dňoch, predaj len pri predanom kuse', () => {
    const events = eventsFromPieces([
      { status: 'owned', purchase_date: '2026-03-12', purchase_price_eur: '20.00' },
      { status: 'owned', purchase_date: '2026-03-12', purchase_price_eur: '14.99' },
      { status: 'sold', purchase_date: '2026-01-05', purchase_price_eur: '10.00', sold_date: '2026-09-01', sold_price_eur: '30.00' },
      { status: 'owned', purchase_date: null, purchase_price_eur: '5.00', sold_date: '2026-09-02' },
    ])

    expect(events).toEqual([
      { day: '2026-01-05', kind: 'buy', count: 1, amount: '10.00' },
      { day: '2026-03-12', kind: 'buy', count: 2, amount: '34.99' },
      { day: '2026-09-01', kind: 'sell', count: 1, amount: '30.00' },
    ])
  })
})
