<script setup lang="ts">
  import type { SeriesRefreshPlan, SeriesValue } from '@/api/types'
  /**
   * Cena mojich figúrok zo série, ako karta ceny v detaile jednej figúrky:
   * kúpené, hodnota a zisk spolu, vývoj ceny a obnova cien.
   *
   * Graf je súčet histórie cien z BrickEconomy (`history`), ako pri jednej
   * figúrke, nie od nákupu; pred prvou cenou figúrky sa ráta jej prvá cena
   * a riadok pod grafom povie, do kedy je súčet odhad. Ako pri sete sú čiary
   * dve, Nový a Rozbalený (`history_used`, len keď cenu pozná každá figúrka).
   * Zvislé čiary sú nákupy
   * a predaje (`events`). Zisk v súčtoch je od nákupu.
   *
   * BrickEconomy cenu celej série nemá, hodnota je súčet mojich figúrok
   * (`GET /prices/series/{num}`). Duplikáty sa pripočítavajú; „Hodnota jednej
   * série“ ráta každú figúrku raz a ide len pri kompletnej sérii. Obnova
   * obnoví len figúrky, ktoré mám (`POST /prices/refresh-all?num=`), a bez
   * kľúča BrickEconomy sa tlačidlo neukáže (`auth.can`).
   *
   * Na posúdenie ponuky na kúpu karta ukáže aj Chýba mi (súčet cien
   * figúrok, ktoré nemám, zelenou) a Celú sériu (každá figúrka raz, cena
   * nového kusu) so zelenou čiarkovanou čiarou v grafe (`history_all`), aj
   * keď zo série nemám nič. Ceny chýbajúcich sa ťahajú len na kliknutie:
   * Zistiť ceny chýbajúcich najprv povie, koľko volaní to stojí
   * (`GET /prices/series/{num}/refresh-plan`), a stiahne až po potvrdení
   * (`refresh-all?whole_series=true`); cena mladšia než 15 dní ostane.
   */
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { api, onCollectionChanged } from '@/api/client'
  import PriceHistoryChart from '@/components/PriceHistoryChart.vue'
  import { onPageReload } from '@/composables/usePageLoad'
  import { useAuthStore } from '@/stores/auth'
  import { useCollectionStore } from '@/stores/collection'
  import { usePriceStore } from '@/stores/prices'
  import { exactMoney, money, percent, shortDate, toNumber } from '@/utils/format'

  const props = defineProps<{ num: string }>()
  /** Po stiahnutí cien celej série: stránka načíta aj ceny pri chýbajúcich figúrkach. */
  const emit = defineEmits<{ 'prices-updated': [] }>()

  const { t } = useI18n()
  const auth = useAuthStore()
  const priceStore = usePriceStore()
  const collection = useCollectionStore()

  const value = ref<SeriesValue | null>(null)
  const single = ref(false)
  const refreshing = ref(false)
  const refreshNote = ref<string | null>(null)
  /** Plán pred Zistiť ceny chýbajúcich; s ním je otvorené potvrdenie. */
  const plan = ref<SeriesRefreshPlan | null>(null)
  const confirming = ref(false)
  const planning = ref(false)
  /** Všetky ceny sú aktuálne, nebolo čo sťahovať (počet dní). */
  const allFresh = ref<number | null>(null)

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

  const owned = computed(() => (value.value?.owned_count ?? 0) > 0)
  const members = computed(() => value.value?.member_count ?? 0)
  const unpriced = computed(() => Math.max(0, members.value - (value.value?.series_priced ?? 0)))
  /** Čiara celej série je zo figúrok s cenou; pri neúplnej legenda povie z koľkých. */
  const wholeLabel = computed(() => unpriced.value > 0
    ? t('minifigs.seriesValue.wholeOf', { priced: value.value?.series_priced ?? 0, total: members.value })
    : t('minifigs.seriesValue.whole'))
  const canFetchMissing = computed(() =>
    auth.can('brickeconomy.price_detail') && (value.value?.missing_count ?? 0) > 0)
  const hasPrice = computed(() => value.value?.market_total !== null && value.value?.market_total !== undefined)
  /** Kúpna cena len figúrok s cenou (hodnota mínus zisk), na čiaru v grafe. */
  const pricedPurchase = computed(() => {
    const market = toNumber(value.value?.market_total)
    const profit = toNumber(value.value?.profit)
    return market === null || profit === null ? null : market - profit
  })
  const profitClass = computed(() => {
    const profit = toNumber(value.value?.profit)
    if (profit === null) return ''
    return profit >= 0 ? 'text-positive' : 'text-negative'
  })

  async function refresh (): Promise<void> {
    refreshing.value = true
    refreshNote.value = null
    await priceStore.refreshOne(props.num, async () => {
      await Promise.all([load(), collection.refreshAll(), auth.loadKeys()])
      const s = priceStore.status
      refreshNote.value = s ? t('detail.refreshNoteSeries', { updated: s.updated, left: s.calls_left }) : null
      refreshing.value = false
    })
  }

  /** Najprv len počet volaní, von nejde nič; stiahne až potvrdenie. */
  async function askWhole (): Promise<void> {
    planning.value = true
    allFresh.value = null
    const [{ data }] = await Promise.all([
      api.GET('/prices/series/{num}/refresh-plan', { params: { path: { num: props.num } } }),
      priceStore.fetchStatus(),
    ])
    planning.value = false
    if (!data) return
    if (data.calls === 0) {
      allFresh.value = data.max_age_days
      return
    }
    plan.value = data
    confirming.value = true
  }

  async function fetchWhole (): Promise<void> {
    confirming.value = false
    refreshing.value = true
    refreshNote.value = null
    await priceStore.refreshOne(props.num, async () => {
      await Promise.all([load(), collection.refreshAll(), auth.loadKeys()])
      const s = priceStore.status
      refreshNote.value = s ? t('detail.refreshNoteSeries', { updated: s.updated, left: s.calls_left }) : null
      refreshing.value = false
      emit('prices-updated')
    }, true)
  }

  watch(single, () => load())
  watch(() => props.num, () => {
    single.value = false
    load()
  })
  onMounted(load)
  onPageReload(load)
  // Kúpa, úprava či zmazanie figúrok (aj hromadné, aj „Mám ju“): súčty aj graf hneď,
  // nie až po obnovení okna.
  onUnmounted(onCollectionChanged(() => {
    load()
  }))
</script>

<template>
  <v-card v-if="value && (owned || members > 0)" border class="pa-4 d-flex flex-column ga-3" flat>
    <div class="d-flex align-center flex-wrap ga-2">
      <div class="text-title-large font-weight-medium me-auto">
        {{ owned ? t('minifigs.seriesValue.title') : t('minifigs.seriesValue.titleWhole') }}
      </div>

      <!-- Každá figúrka raz; ide len pri kompletnej sérii, inak by to nebola séria. -->
      <v-switch
        v-if="owned"
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

    <div v-if="owned" class="d-flex flex-wrap align-end ga-6">
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

    <div v-if="owned && !hasPrice" class="text-body-medium text-medium-emphasis">{{ t('minifigs.seriesValue.noPrice') }}</div>

    <!-- Na posúdenie ponuky: chýbajúce zelenou a celá séria, každá figúrka raz, nový kus. -->
    <div v-if="members > 0" class="d-flex flex-wrap align-end ga-6">
      <div v-if="owned && value.missing_count > 0" data-test="series-missing">
        <div class="d-flex align-center ga-1 text-body-small text-medium-emphasis">
          {{ t('minifigs.seriesValue.missing') }}

          <v-chip data-test="series-missing-count" label size="x-small" variant="tonal">
            {{ t('minifigs.seriesValue.figuresPlural', value.missing_count, { named: { count: value.missing_count } }) }}
          </v-chip>
        </div>

        <div class="text-body-large font-weight-medium text-positive">
          {{ value.missing_total !== null && value.missing_total !== undefined ? exactMoney(value.missing_total) : '—' }}
        </div>
      </div>

      <div data-test="series-whole" :title="t('minifigs.seriesValue.wholeHint')">
        <div class="d-flex align-center ga-1 text-body-small text-medium-emphasis">
          {{ t('minifigs.seriesValue.whole') }}

          <v-chip data-test="series-whole-count" label size="x-small" variant="tonal">
            {{ t('minifigs.seriesValue.figuresPlural', members, { named: { count: members } }) }}
          </v-chip>
        </div>

        <div class="text-body-large font-weight-medium text-positive">
          {{ value.series_total !== null && value.series_total !== undefined ? exactMoney(value.series_total) : '—' }}
        </div>
      </div>

      <div v-if="unpriced > 0" class="text-body-small text-medium-emphasis" data-test="series-unpriced">
        {{ t('minifigs.seriesValue.unpricedPlural', unpriced, { named: { count: unpriced } }) }}
      </div>
    </div>

    <!-- Súčet histórie cien z BrickEconomy ako pri jednej figúrke; zvislé čiary sú nákupy a predaje. -->
    <PriceHistoryChart
      :events="value.events"
      :new-points="value.history"
      periods
      :purchase="pricedPurchase"
      :used-points="value.history_used"
      :whole-label="wholeLabel"
      :whole-points="value.history_all"
    />

    <div v-if="value.estimated_until && value.history.length > 1" class="text-body-small text-medium-emphasis" data-test="series-estimated">
      {{ t('minifigs.seriesValue.estimated', { date: shortDate(value.estimated_until) }) }}
    </div>

    <div v-if="auth.can('brickeconomy.price_detail')" class="d-flex align-center flex-wrap ga-2">
      <span v-if="refreshNote" class="text-body-small text-medium-emphasis">{{ refreshNote }}</span>

      <span v-if="allFresh !== null" class="text-body-small text-medium-emphasis" data-test="series-whole-fresh">
        {{ t('minifigs.seriesValue.allFresh', { days: allFresh }) }}
      </span>

      <v-spacer />

      <v-btn
        v-if="canFetchMissing"
        color="positive"
        data-test="series-whole-refresh"
        :disabled="refreshing"
        :loading="planning"
        prepend-icon="mdi-cash-sync"
        size="small"
        variant="tonal"
        @click="askWhole"
      >{{ t('minifigs.seriesValue.refreshWhole') }}</v-btn>

      <v-btn
        v-if="owned"
        data-test="series-refresh"
        :loading="refreshing"
        prepend-icon="mdi-refresh"
        size="small"
        variant="outlined"
        @click="refresh"
      >{{ t('minifigs.seriesValue.refresh') }}</v-btn>
    </div>

    <!-- Potvrdenie pred volaniami: koľko to stojí a koľko dnes ostáva. -->
    <v-dialog v-model="confirming" max-width="440">
      <v-card v-if="plan" :title="t('minifigs.seriesValue.confirmTitle')">
        <v-card-text class="d-flex flex-column ga-2" data-test="series-whole-confirm-text">
          <div>{{ t('minifigs.seriesValue.confirmCallsPlural', plan.calls, { named: { count: plan.calls } }) }}</div>

          <div v-if="plan.fresh > 0" class="text-medium-emphasis">
            {{ t('minifigs.seriesValue.confirmFresh', { days: plan.max_age_days, count: plan.fresh }) }}
          </div>

          <div class="text-medium-emphasis">
            {{ t('minifigs.seriesValue.confirmQuota', { left: priceStore.callsLeft, limit: priceStore.callsLimit }) }}
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />

          <v-btn variant="text" @click="confirming = false">{{ t('add.cancel') }}</v-btn>

          <v-btn
            color="primary"
            data-test="series-whole-confirm"
            variant="flat"
            @click="fetchWhole"
          >{{ t('minifigs.seriesValue.confirm') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
