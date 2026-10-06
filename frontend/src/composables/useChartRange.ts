/**
 * Výber obdobia grafu: rýchle voľby, polia od–do a „Celá história“.
 *
 * Rýchla voľba, vlastné od–do aj ťahanie v grafe (`setRange`) sú jeden
 * a ten istý rozsah; vlastný je `custom`. Opätovné kliknutie na zvolenú
 * voľbu by ju vo `v-btn-toggle` zrušilo, vtedy ostane, čo bolo. Pamätanie
 * voľby nechá na volajúcom (`onPreset`): Prehľad si ju drží v prehliadači,
 * graf ceny nie.
 */

import type { RangePreset } from '@/utils/chartRange'
import type { Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import { presetRange } from '@/utils/chartRange'

export type ChartPreset = RangePreset | 'custom'

const DAY = 86_400_000

function toInput (ms: number | null): string {
  if (ms === null) {
    return ''
  }
  const d = new Date(ms)
  const pad = (n: number): string => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function useChartRange (initial: RangePreset, onPreset?: (value: RangePreset) => void): {
  preset: Ref<ChartPreset>
  from: Ref<number | null>
  to: Ref<number | null>
  fromInput: Ref<string>
  toInput: Ref<string>
  setEdge: (edge: 'from' | 'to', raw: string) => void
  setRange: (start: number, end: number) => void
  showAll: () => void
} {
  const preset = ref<ChartPreset>(initial)
  const from = ref<number | null>(null)
  const to = ref<number | null>(null)

  function applyPreset (value: ChartPreset): void {
    if (value === 'custom') {
      return
    }
    const [start, end] = presetRange(value, Date.now())
    from.value = start
    to.value = end
    onPreset?.(value)
  }

  watch(preset, (value, previous) => {
    if (value === null || value === undefined) {
      preset.value = previous ?? 'all'
      return
    }
    applyPreset(value)
  }, { immediate: true })

  function setEdge (edge: 'from' | 'to', raw: string): void {
    const ms = raw ? new Date(`${raw}T00:00:00`).getTime() : null
    if (ms !== null && Number.isNaN(ms)) {
      return
    }
    if (edge === 'from') {
      from.value = ms
    } else {
      to.value = ms === null ? null : ms + DAY - 1
    }
    preset.value = 'custom'
  }

  function setRange (start: number, end: number): void {
    from.value = start
    to.value = end
    preset.value = 'custom'
  }

  function showAll (): void {
    preset.value = 'all'
    applyPreset('all')
  }

  return {
    preset,
    from,
    to,
    fromInput: computed(() => toInput(from.value)),
    toInput: computed(() => toInput(to.value)),
    setEdge,
    setRange,
    showAll,
  }
}
