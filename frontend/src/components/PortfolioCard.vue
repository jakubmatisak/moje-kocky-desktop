<script setup lang="ts">
  import type { TimelinePoint } from '@/api/types'
  /**
   * Hodnota portfólia s výberom obdobia.
   *
   * Rýchle voľby (mesiac až všetko), vlastné od–do a ťahanie v grafe sú
   * jeden a ten istý rozsah. Pre krátke obdobie sa dotiahnu denné body,
   * inak stačia týždenné zo Zbierky; denné sa pýtajú raz a potom sa držia.
   * Zvolené obdobie si pamätá prehliadač, je to pohodlie jedného diváka.
   *
   * Zisk za zvolené obdobie (`periodChange`) posiela Prehľadu, ten ho ukáže
   * pod dlaždicami; pri celej histórii nič.
   */
  import type { RangePreset } from '@/utils/chartRange'
  import type { PeriodChange } from '@/utils/periodChange'
  import { computed, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { api } from '@/api/client'
  import DateField from '@/components/DateField.vue'
  import PortfolioChart from '@/components/PortfolioChart.vue'
  import { useChartRange } from '@/composables/useChartRange'
  import { onPageReload } from '@/composables/usePageLoad'
  import { useCollectionStore } from '@/stores/collection'
  import { RANGE_PRESETS } from '@/utils/chartRange'
  import { periodChange } from '@/utils/periodChange'

  const props = defineProps<{ weekly: TimelinePoint[] }>()
  const emit = defineEmits<{ period: [change: PeriodChange | null] }>()

  const { t } = useI18n()

  const DAY = 86_400_000
  const DAILY_UP_TO = 186 * DAY
  const STORAGE_KEY = 'moje-kocky.portfolio-range'

  function loadPreset (): RangePreset {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as RangePreset | null
      return saved && RANGE_PRESETS.includes(saved) ? saved : '1y'
    } catch {
      return '1y'
    }
  }

  const { preset, from, to, fromInput, toInput: toInputValue, setEdge, setRange: onRange, showAll } = useChartRange(
    loadPreset(),
    value => {
      try {
        localStorage.setItem(STORAGE_KEY, value)
      } catch {
        // Súkromné okno alebo zablokované úložisko: len si to nezapamätáme.
      }
    },
  )
  const daily = ref<TimelinePoint[] | null>(null)
  const loadingDaily = ref(false)

  /**
   * Dĺžka toho, čo je naozaj vidno. „Rok“ pri dvojmesačnej histórii sú
   * dva mesiace, a tie si zaslúžia denné body.
   */
  const span = computed(() => {
    const first = props.weekly[0]
    const historyStart = first ? new Date(first.day).getTime() : Date.now()
    const start = Math.max(from.value ?? historyStart, historyStart)
    return (to.value ?? Date.now()) - start
  })

  const collection = useCollectionStore()

  const useDaily = computed(() => span.value <= DAILY_UP_TO)

  watch(useDaily, async needDaily => {
    if (!needDaily || daily.value !== null || loadingDaily.value) return
    loadingDaily.value = true
    const { data } = await api.GET('/stats/timeline', {
      params: { query: { step: 'day', ...collection.statsQuery() } },
    })
    daily.value = data ?? []
    loadingDaily.value = false
  }, { immediate: true })

  /** Denný rad znova, ak už bol stiahnutý; týždenný prichádza s Prehľadom. */
  async function reloadDaily (): Promise<void> {
    if (daily.value === null) return
    const { data } = await api.GET('/stats/timeline', {
      params: { query: { step: 'day', ...collection.statsQuery() } },
    })
    daily.value = data ?? []
  }

  // Prepínač dnešných peňazí: denný rad sa musí stiahnuť znova.
  watch(() => [collection.real, collection.scope], reloadDaily)
  // Tlačidlo Obnoviť stránku v hornej lište.
  onPageReload(reloadDaily)

  const points = computed(() => (useDaily.value && daily.value ? daily.value : props.weekly))

  const period = computed(() => (preset.value === 'all' ? null : periodChange(points.value, from.value, to.value)))
  watch(period, value => emit('period', value), { immediate: true })
</script>

<template>
  <v-card border class="pa-4 h-100 d-flex flex-column" flat>
    <div class="d-flex align-start ga-3 flex-wrap mb-2">
      <div>
        <div class="text-title-large font-weight-medium">{{ t('dashboard.chartTitle') }}</div>
        <div class="text-body-small text-medium-emphasis">{{ t('dashboard.chartHint') }}</div>
      </div>

      <v-spacer />

      <v-btn-toggle
        v-model="preset"
        density="compact"
        divided
        variant="outlined"
      >
        <v-btn v-for="value in RANGE_PRESETS" :key="value" size="small" :value="value">
          {{ t(`dashboard.range.${value}`) }}
        </v-btn>
      </v-btn-toggle>
    </div>

    <div class="d-flex align-center flex-wrap ga-2 mb-2">
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
        :model-value="toInputValue"
        @update:model-value="setEdge('to', String($event ?? ''))"
      />

      <v-btn
        v-if="preset !== 'all'"
        prepend-icon="mdi-arrow-expand-horizontal"
        size="small"
        variant="text"
        @click="showAll"
      >{{ t('dashboard.range.showAll') }}</v-btn>

      <v-progress-circular
        v-if="loadingDaily"
        color="primary"
        indeterminate
        size="18"
        width="2"
      />
    </div>

    <div class="flex-grow-1" style="min-height: 260px">
      <PortfolioChart :from="from" :points="points" :to="to" @range="onRange" />
    </div>
  </v-card>
</template>

<style scoped>
.range-field {
  flex: 0 1 170px;
}
</style>
