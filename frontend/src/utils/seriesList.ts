/**
 * Figúrky: stav série, filter podľa stavu a zoradenie. Čisté funkcie, nech
 * sa dajú otestovať bez obrazovky (MinifigsView).
 */

import type { CmfMember, CmfSeries } from '@/api/types'
import type { SortDir } from '@/utils/tableSort'
import { sortRows } from '@/utils/tableSort'

export type SeriesState = 'collecting' | 'complete' | 'untouched'
export type StateFilter = 'all' | SeriesState | 'almost'
/** Výber nad kartami; ďalšie kľúče (mám, chýba, kompletnosť) má len hlavička tabuľky. */
export const MENU_SERIES_SORTS = ['leastMissing', 'yearDesc', 'yearAsc', 'nameAsc', 'nameDesc'] as const
export const SERIES_SORTS = [
  ...MENU_SERIES_SORTS, 'ownedDesc', 'ownedAsc', 'missingAsc', 'missingDesc', 'progressDesc', 'progressAsc',
  'purchaseDesc', 'purchaseAsc', 'valueDesc', 'valueAsc', 'priceAtDesc', 'priceAtAsc',
  'profitDesc', 'profitAsc', 'profitPctDesc', 'profitPctAsc', 'wholeDesc', 'wholeAsc',
] as const
export type SeriesSort = (typeof SERIES_SORTS)[number]

/** Stĺpce tabuľky sérií, ktoré radia (fotka nie). */
export type SeriesColumn = 'name' | 'year' | 'owned' | 'missing' | 'progress'
  | 'purchase' | 'value' | 'priceAt' | 'profit' | 'profitPct' | 'whole'

/**
 * Kľúč stĺpca pre každý smer; prvý je predvolený (názov od A, rok od
 * najnovšieho, mám a kompletnosť od najväčšieho, chýba od najmenej).
 * Smer je súčasťou kľúča, lebo tak je zoradenie v adrese (`?sort=yearAsc`).
 */
const COLUMN_SORTS: Record<SeriesColumn, [SeriesSort, SeriesSort]> = {
  name: ['nameAsc', 'nameDesc'],
  year: ['yearDesc', 'yearAsc'],
  owned: ['ownedDesc', 'ownedAsc'],
  missing: ['missingAsc', 'missingDesc'],
  progress: ['progressDesc', 'progressAsc'],
  // Sumy ako v Zbierke: od najväčšieho, dátum ceny od najnovšieho.
  purchase: ['purchaseDesc', 'purchaseAsc'],
  value: ['valueDesc', 'valueAsc'],
  priceAt: ['priceAtDesc', 'priceAtAsc'],
  profit: ['profitDesc', 'profitAsc'],
  profitPct: ['profitPctDesc', 'profitPctAsc'],
  // Celá séria z uložených cien (každá figúrka raz), od najdrahšej.
  whole: ['wholeDesc', 'wholeAsc'],
}

/** Zoradenie po kliku na hlavičku: iný stĺpec predvoleným smerom, ten istý otočí. */
export function seriesSortFromHeader (column: SeriesColumn, current: SeriesSort): SeriesSort {
  const [first, second] = COLUMN_SORTS[column]
  return current === first ? second : first
}

/** Smer šípky v hlavičke, alebo null, keď sa podľa stĺpca neradí. */
export function seriesHeaderDir (column: SeriesColumn, current: SeriesSort): SortDir | null {
  if (!COLUMN_SORTS[column].includes(current)) {
    return null
  }
  return current.endsWith('Asc') ? 'asc' : 'desc'
}

type Row = Pick<CmfSeries, 'name' | 'owned' | 'total' | 'year'>
  & Partial<Pick<CmfSeries, 'purchase_total' | 'market_total' | 'profit' | 'profit_pct' | 'price_at' | 'series_total'>>

type SumColumn = 'purchase' | 'value' | 'priceAt' | 'profit' | 'profitPct' | 'whole'

/** Suma série ako číslo; séria bez mojej figúrky či bez ceny ju nemá (na konci). */
function sumValue (row: Row, column: SumColumn): number | null {
  const raw = {
    purchase: row.purchase_total,
    value: row.market_total,
    priceAt: row.price_at,
    profit: row.profit,
    profitPct: row.profit_pct,
    whole: row.series_total,
  }[column]
  if (raw === null || raw === undefined) {
    return null
  }
  return column === 'priceAt' ? new Date(String(raw)).getTime() : Number(raw)
}

/** Figúrky jednej série: všetky, tie, čo mám, alebo tie, čo chýbajú. */
export type MemberShow = 'all' | 'owned' | 'missing'

/** Voľba z adresy (`?show=missing` z Prehľadu); neznáma = všetky. */
export function memberShowFrom (value: unknown): MemberShow {
  return value === 'owned' || value === 'missing' ? value : 'all'
}

/** Skoro kompletná: chýbajú najviac toľko figúrok. */
export const ALMOST_MISSING = 2

export function seriesState (row: Row): SeriesState {
  if (row.owned === 0) {
    return 'untouched'
  }
  return row.owned >= row.total ? 'complete' : 'collecting'
}

export function missingOf (row: Row): number {
  return Math.max(0, row.total - row.owned)
}

/** „Skoro kompletné“ je podmnožina „zbieram“: niečo mám a chýba najviac 2. */
export function matchesState (row: Row, filter: StateFilter): boolean {
  if (filter === 'all') {
    return true
  }
  if (filter === 'almost') {
    return seriesState(row) === 'collecting' && missingOf(row) <= ALMOST_MISSING
  }
  return seriesState(row) === filter
}

/** Číslo stĺpca; séria bez roka či ešte nestiahnutá (nula figúrok) ho nemá. */
function columnValue (row: Row, column: 'year' | 'owned' | 'missing' | 'progress' | SumColumn): number | null {
  if (column !== 'year' && column !== 'owned' && column !== 'missing' && column !== 'progress') {
    return sumValue(row, column)
  }
  if (column === 'year') {
    return row.year ?? null
  }
  if (row.total <= 0) {
    return null
  }
  if (column === 'owned') {
    return row.owned
  }
  if (column === 'missing') {
    return missingOf(row)
  }
  return row.owned / row.total
}

/** Podľa čísla stĺpca; prázdna hodnota na konci v oboch smeroch, pri zhode názov. */
function byColumn (a: Row, b: Row, column: Parameters<typeof columnValue>[1], desc: boolean, byName: number): number {
  const x = columnValue(a, column)
  const y = columnValue(b, column)
  if (x === null || y === null) {
    return (x === null ? 1 : 0) - (y === null ? 1 : 0) || byName
  }
  return (desc ? y - x : x - y) || byName
}

/** „Series 2“ patrí pred „Series 10“, preto porovnanie s číslami (`collator`). */
export function compareSeries (a: Row, b: Row, sort: SeriesSort, collator: Intl.Collator): number {
  const byName = collator.compare(a.name, b.name)
  const order = { collecting: 0, complete: 1, untouched: 2 }
  switch (sort) {
    case 'yearDesc': { return byColumn(a, b, 'year', true, byName) }
    case 'yearAsc': { return byColumn(a, b, 'year', false, byName) }
    case 'nameAsc': { return byName }
    case 'nameDesc': { return -byName }
    case 'ownedDesc': { return byColumn(a, b, 'owned', true, byName) }
    case 'ownedAsc': { return byColumn(a, b, 'owned', false, byName) }
    case 'missingAsc': { return byColumn(a, b, 'missing', false, byName) }
    case 'missingDesc': { return byColumn(a, b, 'missing', true, byName) }
    case 'progressDesc': { return byColumn(a, b, 'progress', true, byName) }
    case 'progressAsc': { return byColumn(a, b, 'progress', false, byName) }
    case 'purchaseDesc': { return byColumn(a, b, 'purchase', true, byName) }
    case 'purchaseAsc': { return byColumn(a, b, 'purchase', false, byName) }
    case 'valueDesc': { return byColumn(a, b, 'value', true, byName) }
    case 'valueAsc': { return byColumn(a, b, 'value', false, byName) }
    case 'priceAtDesc': { return byColumn(a, b, 'priceAt', true, byName) }
    case 'priceAtAsc': { return byColumn(a, b, 'priceAt', false, byName) }
    case 'profitDesc': { return byColumn(a, b, 'profit', true, byName) }
    case 'profitAsc': { return byColumn(a, b, 'profit', false, byName) }
    case 'profitPctDesc': { return byColumn(a, b, 'profitPct', true, byName) }
    case 'profitPctAsc': { return byColumn(a, b, 'profitPct', false, byName) }
    case 'wholeDesc': { return byColumn(a, b, 'whole', true, byName) }
    case 'wholeAsc': { return byColumn(a, b, 'whole', false, byName) }
    default: {
      // Najmenej chýba: rozbehnuté podľa toho, koľko chýba; kompletné za nimi, nezačaté na konci.
      return order[seriesState(a)] - order[seriesState(b)] || missingOf(a) - missingOf(b) || byColumn(a, b, 'year', true, byName)
    }
  }
}

// --- figúrky jednej série ---------------------------------------------------

/** Stĺpce tabuľky figúrok série, ktoré radia (fotka a akcie nie). */
export type MemberSort = 'number' | 'name' | 'state' | 'wanted'
  | 'purchase' | 'value' | 'priceAt' | 'profit' | 'profitPct'

type Member = Pick<CmfMember, 'catalog' | 'owned' | 'wanted'>
  & Partial<Pick<CmfMember, 'purchase_total' | 'market_total' | 'profit' | 'profit_pct' | 'price_at' | 'market_now' | 'market_now_at'>>

/** Číslo a názov od A; stav, Chcem a sumy od najväčšieho (dátum ceny od najnovšieho). */
export function memberDefaultDir (sort: MemberSort): SortDir {
  return sort === 'number' || sort === 'name' ? 'asc' : 'desc'
}

function num (value: string | number | null | undefined): number | null {
  return value === null || value === undefined ? null : Number(value)
}

function time (value: string | null | undefined): number | null {
  return value ? new Date(value).getTime() : null
}

const MEMBER_VALUES: Record<MemberSort, (m: Member) => number | string | null> = {
  number: m => m.catalog.catalog_num,
  name: m => m.catalog.name,
  // Počet kusov: dvakrát vlastnená pred raz vlastnenou, chýbajúca (0) na druhom konci.
  state: m => m.owned,
  wanted: m => (m.wanted ? 1 : 0),
  purchase: m => num(m.purchase_total),
  // Chýbajúca figúrka sa radí podľa ceny na trhu, nech sa dá nájsť najlacnejšia.
  value: m => num(m.market_total ?? m.market_now),
  priceAt: m => time(m.price_at ?? m.market_now_at),
  profit: m => num(m.profit),
  profitPct: m => num(m.profit_pct),
}

/** Figúrky zoradené podľa stĺpca; pri zhode podľa čísla (71046-2 pred 71046-10). */
export function sortMembers<T extends Member> (members: readonly T[], sort: MemberSort, dir: SortDir): T[] {
  const byNumber = sortRows(members, MEMBER_VALUES.number, 'asc')
  return sort === 'number' ? sortRows(members, MEMBER_VALUES.number, dir) : sortRows(byNumber, MEMBER_VALUES[sort], dir)
}
