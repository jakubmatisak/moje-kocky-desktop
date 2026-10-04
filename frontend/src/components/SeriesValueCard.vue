<script setup lang="ts">
  import type { SeriesValue, TimelinePoint } from '@/api/types'
  /**
   * Cena mojich figúrok zo série, ako karta ceny v detaile jednej figúrky:
   * kúpené, hodnota a zisk spolu, vývoj portfólia série a obnova cien.
   *
   * Graf je ten istý ako portfólio na Prehľade (`/stats/timeline` s filtrom
   * `series`): od prvého nákupu, každý kus až odo dňa kúpy, bez trhovej ceny
   * kúpnou cenou, predaný do dňa predaja. Prepínač jednej série ho nemení.
   *
   * BrickEconomy cenu celej série nemá, hodnota je súčet mojich figúrok
   * (`GET /prices/series/{num}`). Duplikáty sa pripočítavajú; „Hodnota jednej
   * série“ ráta každú figúrku raz a ide len pri kompletnej sérii. Obnova
   * obnoví len figúrky, ktoré mám (`POST /prices/refresh-all?num=`), a bez
   * kľúča BrickEconomy sa tlačidlo neukáže (`auth.can`).
   */
  import { computed, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { api } from '@/api/client'
  import PortfolioChart from '@/components/PortfolioChart.vue'
  import { onPageReload } from '@/composables/usePageLoad'
  import { useAuthStore } from '@/stores/auth'
  import { useCollectionStore } from '@/stores/collection'
  import { usePriceStore } from '@/stores/prices'
  import { exactMoney, money, percent, shortDate, toNumber } from '@/utils/format'

  const props = defineProps<{ num: string }>()

  const { t } = useI18n()
  const auth = useAuthStore()
  const priceStore = usePriceStore()
  const collection = useCollectionStore()

  const value = ref<SeriesValue | null>(null)
  const timeline = ref<TimelinePoint[]>([])

  async function loadTimeline (): Promise<void> {
    const { data } = await api.GET('/stats/timeline', {
      params: { query: { step: 'day', series: [props.num] } },
    })
    timeline.value = data ?? []
  }
  const single = ref(false)
  const refreshing = ref(false)
  const refreshNote = ref<string | null>(null)

  async function load (): Promise<void> {
    const { data } = await api.GET('/prices/series/{num}', {
      params: { path: { num: props.num }, query: { single: single.value } },
    })
    if (data) {
      value.value = data
      // Server hodnotu jednej série pri nekompletnej sérii nedá; prepínač sa vráti.
      if (single.value && !data.single) single.value = false
    }
  }

  const hasPrice = computed(() => value.value?.market_total !== null && value.value?.market_total !== undefined)
  const profitClass = computed(() => {
    const profit = toNumber(value.value?.profit)
    if (profit === null) return ''
    return profit >= 0 ? 'text-positive' : 'text-negative'
  })

  async function refresh (): Promise<void> {
    refreshing.value = true
    refreshNote.value = null
    await priceStore.refreshOne(props.num, async () => {
      await Promise.all([load(), loadTimeline(), collection.refreshAll(), auth.loadKeys()])
      const s = priceStore.status
      refreshNote.value = s ? t('detail.refreshNoteSeries', { updated: s.updated, left: s.calls_left }) : null
      refreshing.value = false
    })
  }

  watch(single, () => load())
  watch(() => props.num, () => {
    single.value = false
    load()
    loadTimeline()
  })
  onMounted(() => Promise.all([load(), loadTimeline()]))
  onPageReload(() => Promise.all([load(), loadTimeline()]))
</script>

<template>
  <v-card v-if="value && value.owned_count > 0" border class="pa-4 d-flex flex-column ga-3" flat>
    <div class="d-flex align-center flex-wrap ga-2">
      <div class="text-title-large font-weight-medium me-auto">{{ t('minifigs.seriesValue.title') }}</div>

      <!-- Každá figúrka raz; ide len pri kompletnej sérii, inak by to nebola séria. -->
      <v-switch
        v-model="single"
        color="primary"
        data-test="series-single"
        density="compact"
        :disabled="!value.complete"
        hide-details
        :label="t('minifigs.seriesValue.single')"
        :title="value.complete ? t('minifigs.seriesValue.singleHint') : t('minifigs.seriesValue.singleIncomplete')"
      />
    </div>

    <div
      v-if="value.duplicates > 0 && !value.single"
      class="d-flex align-center ga-2 text-body-medium text-medium-emphasis"
      data-test="series-duplicates"
    >
      <v-icon icon="mdi-information-outline" size="18" />
      {{ t('minifigs.seriesValue.duplicatesPlural', value.duplicates, { named: { count: value.duplicates } }) }}
    </div>

    <div class="d-flex flex-wrap align-end ga-6">
      <div>
        <div class="text-body-small text-medium-emphasis">{{ t('minifigs.seriesValue.purchased') }}</div>
        <div class="text-body-large font-weight-medium">{{ exactMoney(value.purchase_total) }}</div>
      </div>

      <div>
        <div class="text-body-small text-medium-emphasis">{{ t('minifigs.seriesValue.value') }}</div>

        <!-- Bez ceny pomlčka, nie 0 €. -->
        <div class="text-body-large font-weight-medium" data-test="series-market">
          <template v-if="hasPrice">
            <span v-if="value.approx" class="text-medium-emphasis">≈ </span>{{ exactMoney(value.market_total) }}
          </template>

          <template v-else>—</template>
        </div>
      </div>

      <div v-if="hasPrice">
        <div class="text-body-small text-medium-emphasis">{{ t('minifigs.seriesValue.profit') }}</div>

        <div class="text-body-large font-weight-medium" :class="profitClass">
          {{ money(value.profit, { sign: true }) }}
          <span v-if="value.profit_pct !== null" class="text-body-medium">({{ percent(value.profit_pct, { sign: true }) }})</span>
        </div>
      </div>

      <div class="text-body-small text-medium-emphasis">
        <div v-if="value.price_at">{{ t('collection.priceAt', { date: shortDate(value.price_at) }) }}</div>

        <div v-if="value.priced_count < value.owned_count">
          {{ t('minifigs.seriesValue.pricedOf', { priced: value.priced_count, owned: value.owned_count }) }}
        </div>
      </div>
    </div>

    <div v-if="!hasPrice" class="text-body-medium text-medium-emphasis">{{ t('minifigs.seriesValue.noPrice') }}</div>

    <!-- Vývoj portfólia série ako na Prehľade: vložené, hodnota a výnos z predajov. -->
    <PortfolioChart v-if="timeline.length > 1" :points="timeline" />

    <div v-if="auth.can('brickeconomy.price_detail')" class="d-flex align-center flex-wrap ga-2">
      <span v-if="refreshNote" class="text-body-small text-medium-emphasis">{{ refreshNote }}</span>

      <v-spacer />

      <v-btn
        data-test="series-refresh"
        :loading="refreshing"
        prepend-icon="mdi-refresh"
        size="small"
        variant="outlined"
        @click="refresh"
      >{{ t('minifigs.seriesValue.refresh') }}</v-btn>
    </div>
  </v-card>
</template>
