<script setup lang="ts">
  /**
   * Vývoj trhovej ceny jedného setu: nový a použitý kus a k tomu kúpna cena.
   *
   * História prichádza s každou obnovou ceny zadarmo (`price_events_*`),
   * graf teda nestojí žiadne volanie navyše. Body nového a použitého kusu
   * majú rôzne dátumy, preto je os x číselná (čas v ms), nie kategórie:
   * rozostupy tak zodpovedajú času a netreba knižnicu na dátumy.
   *
   * `events` sú nákupy a predaje: zvislá čiarkovaná čiara v ten deň (plugin
   * `eventLines`) a značka dole, ktorá pri prejdení myšou povie počet a sumu.
   *
   * S `periods` má výber obdobia ako portfólio na Prehľadu (1M až Všetko,
   * od–do, `useChartRange`). Krivky sa orežú na obdobie a na okraji dostanú
   * bod dopočítaný z cien okolo (`clipSeries`), nákupy mimo obdobia zmiznú.
   * Obdobie si nepamätá nič, každý graf začína celou históriou.
   */
  import type { PricePoint } from '@/api/types'
  import type { ChartEvent } from '@/utils/chartEvents'
  import type { Plugin } from 'chart.js'
  import {
    Chart as ChartJS,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Tooltip,
  } from 'chart.js'
  import { computed } from 'vue'
  import { Line } from 'vue-chartjs'
  import { useI18n } from 'vue-i18n'
  import { useTheme } from 'vuetify'
  import DateField from '@/components/DateField.vue'
  import { useChartRange } from '@/composables/useChartRange'
  import { CHART_COLORS } from '@/plugins/vuetify'
  import { clipSeries, RANGE_PRESETS } from '@/utils/chartRange'
  import { amount, displayCurrency, exactMoney, pricesHidden, toDisplay, toNumber } from '@/utils/format'

  ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Legend)

  const props = defineProps<{
    newPoints: PricePoint[]
    usedPoints: PricePoint[]
    /** Priemerná kúpna cena vlastnených kusov, ak ju poznáme. */
    purchase: number | null
    /** Nákupy a predaje na zvislé čiary. */
    events?: ChartEvent[]
    /** Výber obdobia nad grafom. */
    periods?: boolean
  }>()

  const { preset, from, to, fromInput, toInput, setEdge, showAll } = useChartRange('all')

  const EVENT_COLORS: Record<string, string> = { buy: CHART_COLORS.themes[1]!, sell: CHART_COLORS.proceeds }

  const eventPoints = computed(() => (props.events ?? [])
    .map(e => ({ ...e, x: new Date(`${e.day.slice(0, 10)}T12:00:00`).getTime() }))
    .filter(e => (from.value === null || e.x >= from.value) && (to.value === null || e.x <= to.value)))

  const { t } = useI18n()
  const theme = useTheme()

  const gridColor = computed(() =>
    theme.current.value.dark ? 'rgba(255,255,255,0.09)' : 'rgba(0,0,0,0.08)',
  )
  const textColor = computed(() =>
    theme.current.value.dark ? '#A9A4A3' : '#5C5B5B',
  )

  /**
   * Jeden bod na deň, posledný z neho. Aktuálna cena sa ukladá pri každej
   * obnove, takže tri obnovy za deň by inak spravili tri body nad sebou.
   */
  function series (points: PricePoint[]): { x: number, y: number }[] {
    const byDay = new Map<string, { x: number, y: number }>()
    for (const p of points) {
      const y = toNumber(p.avg_price)
      if (y === null || y <= 0) continue
      const x = new Date(p.captured_at).getTime()
      const day = p.captured_at.slice(0, 10)
      const seen = byDay.get(day)
      // Body v mene zobrazenia, aby osi mali okrúhle sumy v nej.
      if (!seen || seen.x < x) byDay.set(day, { x, y: toDisplay(y) })
    }
    return [...byDay.values()].toSorted((a, b) => a.x - b.x)
  }

  const allNew = computed(() => series(props.newPoints))
  const allUsed = computed(() => series(props.usedPoints))
  const newSeries = computed(() => clipSeries(allNew.value, from.value, to.value))
  const usedSeries = computed(() => clipSeries(allUsed.value, from.value, to.value))

  /** Graf má zmysel od dvoch rôznych dní v aspoň jednej krivke (celej histórie). */
  const hasData = computed(() => allNew.value.length > 1 || allUsed.value.length > 1)
  /** V zvolenom období nie je ani jedna cena. */
  const emptyPeriod = computed(() => newSeries.value.length === 0 && usedSeries.value.length === 0)

  const span = computed(() => {
    const xs = [...newSeries.value, ...usedSeries.value, ...eventPoints.value].map(p => p.x)
    if (xs.length === 0) return { min: from.value ?? 0, max: to.value ?? Date.now() }
    return { min: Math.min(...xs), max: Math.max(...xs) }
  })

  /** Výška značiek udalostí: najnižšia suma v grafe, nech sú pri osi x. */
  const eventY = computed(() => {
    const ys = [...newSeries.value, ...usedSeries.value].map(p => p.y)
    if (props.purchase !== null) ys.push(toDisplay(props.purchase))
    return ys.length > 0 ? Math.min(...ys) : 0
  })

  /** Zvislé čiarkované čiary v dňoch nákupov a predajov, cez celú výšku grafu. */
  const eventLines: Plugin<'line'> = {
    id: 'eventLines',
    beforeDatasetsDraw (chart) {
      const { ctx, chartArea, scales } = chart
      const x = scales.x
      if (!x) return
      ctx.save()
      ctx.setLineDash([4, 4])
      ctx.lineWidth = 1.2
      for (const e of eventPoints.value) {
        const px = x.getPixelForValue(e.x)
        if (px < chartArea.left || px > chartArea.right) continue
        ctx.strokeStyle = EVENT_COLORS[e.kind] ?? CHART_COLORS.invested
        ctx.beginPath()
        ctx.moveTo(px, chartArea.top)
        ctx.lineTo(px, chartArea.bottom)
        ctx.stroke()
      }
      ctx.restore()
    },
  }

  const dayFormat = new Intl.DateTimeFormat('sk-SK', { day: 'numeric', month: 'numeric', year: 'numeric' })
  const monthFormat = new Intl.DateTimeFormat('sk-SK', { month: 'short', year: 'numeric' })
  const shortDayFormat = new Intl.DateTimeFormat('sk-SK', { day: 'numeric', month: 'numeric' })
  /** Pri pár týždňoch deň a mesiac, pri dlhšej histórii mesiac a rok. */
  const tickFormat = computed(() =>
    span.value.max - span.value.min < 120 * 86_400_000 ? shortDayFormat : monthFormat,
  )

  /**
   * Pri lacnej figúrke sa cena hýbe o centy a celé eurá by na osi dali
   * desaťkrát „4 €“. Desatinné miesta len vtedy, keď je rozpätie malé.
   */
  const yDecimals = computed(() => {
    const ys = [...newSeries.value, ...usedSeries.value].map(p => p.y)
    if (props.purchase !== null) ys.push(toDisplay(props.purchase))
    return ys.length > 0 && Math.max(...ys) - Math.min(...ys) < 10 ? 2 : 0
  })

  const chartData = computed(() => {
    const datasets = []
    if (newSeries.value.length > 0) {
      datasets.push({
        label: t('detail.historyNew'),
        data: newSeries.value,
        borderColor: CHART_COLORS.value,
        backgroundColor: CHART_COLORS.value,
        borderWidth: 2.4,
        tension: 0.2,
        pointRadius: 2.5,
        pointHoverRadius: 5,
      })
    }
    if (usedSeries.value.length > 0) {
      datasets.push({
        label: t('detail.historyUsed'),
        data: usedSeries.value,
        borderColor: CHART_COLORS.themes[2],
        backgroundColor: CHART_COLORS.themes[2],
        borderWidth: 2.4,
        tension: 0.2,
        pointRadius: 2.5,
        pointHoverRadius: 5,
      })
    }
    if (props.purchase !== null) {
      datasets.push({
        label: t('detail.historyPurchase'),
        data: [
          { x: span.value.min, y: toDisplay(props.purchase) },
          { x: span.value.max, y: toDisplay(props.purchase) },
        ],
        borderColor: CHART_COLORS.invested,
        backgroundColor: CHART_COLORS.invested,
        borderDash: [5, 4],
        borderWidth: 1.6,
        pointRadius: 0,
        pointHoverRadius: 0,
      })
    }
    for (const kind of ['buy', 'sell']) {
      const points = eventPoints.value.filter(e => e.kind === kind)
      if (points.length === 0) continue
      datasets.push({
        label: t(kind === 'buy' ? 'detail.historyBought' : 'detail.historySold'),
        data: points.map(e => ({ x: e.x, y: eventY.value })),
        events: points,
        borderColor: EVENT_COLORS[kind],
        backgroundColor: EVENT_COLORS[kind],
        showLine: false,
        pointStyle: 'triangle',
        pointRadius: 6,
        pointHoverRadius: 8,
      })
    }
    return { datasets }
  })

  const chartOptions = computed(() => ({
    // Nový objekt pri skrytí cien: graf prekreslí osi aj popisy so sumami.
    hiddenPrices: pricesHidden.value,
    // Aj pri zmene meny zobrazenia: body sú prepočítané, osi v novej mene.
    displayCurrency: displayCurrency.value.code,
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'nearest' as const, intersect: false },
    plugins: {
      legend: {
        position: 'bottom' as const,
        align: 'start' as const,
        labels: { boxWidth: 12, boxHeight: 3, color: textColor.value, font: { size: 11 } },
      },
      tooltip: {
        callbacks: {
          title: (items: { parsed: { x: number | null } }[]) =>
            items[0]?.parsed.x == null ? '' : dayFormat.format(new Date(items[0].parsed.x)),
          label: (ctx: { dataset: { label?: string, events?: ChartEvent[] }, dataIndex: number, parsed: { y: number | null } }) => {
            const event = ctx.dataset.events?.[ctx.dataIndex]
            if (event) {
              return t('detail.historyEvent', {
                what: ctx.dataset.label,
                count: event.count,
                amount: exactMoney(event.amount),
              })
            }
            return `${ctx.dataset.label}: ${amount(ctx.parsed.y)}`
          },
        },
      },
    },
    scales: {
      x: {
        type: 'linear' as const,
        min: span.value.min,
        max: span.value.max,
        grid: { display: false },
        ticks: {
          color: textColor.value,
          font: { size: 10 },
          maxTicksLimit: 6,
          callback: (value: string | number) => tickFormat.value.format(new Date(Number(value))),
        },
      },
      y: {
        grid: { color: gridColor.value },
        border: { display: false },
        ticks: {
          color: textColor.value,
          font: { size: 10 },
          callback: (value: string | number) => amount(value, { decimals: yDecimals.value }),
        },
      },
    },
  }))
</script>

<template>
  <div v-if="hasData">
    <div class="d-flex align-center flex-wrap ga-2 mb-1">
      <div class="text-body-small text-medium-emphasis me-auto">{{ t('detail.historyTitle') }}</div>

      <v-btn-toggle
        v-if="periods"
        v-model="preset"
        data-test="history-presets"
        density="compact"
        divided
        variant="outlined"
      >
        <v-btn v-for="value in RANGE_PRESETS" :key="value" size="small" :value="value">
          {{ t(`dashboard.range.${value}`) }}
        </v-btn>
      </v-btn-toggle>
    </div>

    <div v-if="periods" class="d-flex align-center flex-wrap ga-2 mb-2">
      <DateField
        class="range-field"
        density="compact"
        hide-details
        :label="t('filters.from')"
        :model-value="fromInput"
        @update:model-value="setEdge('from', String($event ?? ''))"
      />

      <DateField
        class="range-field"
        density="compact"
        hide-details
        :label="t('filters.to')"
        :model-value="toInput"
        @update:model-value="setEdge('to', String($event ?? ''))"
      />

      <v-btn
        v-if="preset !== 'all'"
        prepend-icon="mdi-arrow-expand-horizontal"
        size="small"
        variant="text"
        @click="showAll"
      >{{ t('dashboard.range.showAll') }}</v-btn>
    </div>

    <div v-if="emptyPeriod" class="price-history d-flex align-center justify-center text-body-medium text-medium-emphasis">
      {{ t('detail.historyEmptyPeriod') }}
    </div>

    <div v-else class="price-history">
      <Line :data="chartData as never" :options="chartOptions" :plugins="[eventLines]" />
    </div>
  </div>
</template>

<style scoped>
.price-history {
  height: 220px;
  position: relative;
}

.range-field {
  flex: 0 1 170px;
}
</style>
