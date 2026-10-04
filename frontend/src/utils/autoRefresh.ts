/**
 * Text posledného automatického behu obnovy cien („dnes 7:02, obnovené
 * ceny: 23“). Čas je miestny, ako ho zapísal beh (`RRRR-MM-DDTHH:MM`).
 */

export interface AutoLast {
  at: string
  updated: number
  outcome: string
  complete: boolean
}

type Translate = (key: string, named?: Record<string, unknown>) => string

const OUTCOMES = new Set(['quota', 'reserve', 'disabled', 'stopped', 'error', 'offline'])

export function autoLastLabel (last: AutoLast | null | undefined, t: Translate, now = new Date()): string | null {
  if (!last) {
    return null
  }
  const [day = '', clock = ''] = last.at.split('T')
  const [, mm, dd] = day.split('-')
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const hm = clock.replace(/^0(\d):/, '$1:')
  const when = day === today
    ? t('sources.autoRefresh.today', { time: hm })
    : `${Number(dd)}. ${Number(mm)}. ${hm}`
  if (OUTCOMES.has(last.outcome)) {
    return t('sources.autoRefresh.lastProblem', { when, problem: t(`sources.autoRefresh.outcome.${last.outcome}`), count: last.updated })
  }
  return t('sources.autoRefresh.last', { when, count: last.updated })
}
