<script setup lang="ts">
  /**
   * Sumy na karte série či figúrky vo Figúrkach, rovnako ako na karte setu
   * v Zbierke: Kúpené → Hodnota, zisk v % a pod nimi „cena z“.
   *
   * Figúrka, ktorú nemám (\`missing\`), má len cenu na trhu so štítkom „Nemám,
   * len cena“, nech sa nezamení s mojou hodnotou. Bez ceny pomlčka, nie 0 €.
   * Pri sérii s duplikátmi povie, že súčet ich ráta.
   */
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { exactMoney, percent, shortDate } from '@/utils/format'

  const props = defineProps<{
    purchase?: string | null
    value?: string | null
    profitPct?: number | null
    approx?: boolean
    priceAt?: string | null
    /** Chýbajúca figúrka: cena na trhu a jej dátum namiesto mojich súm. */
    missing?: boolean
    marketNow?: string | null
    marketNowAt?: string | null
    /** Kusy navyše v súčte (séria s duplikátmi, figúrka mám × 2). */
    duplicates?: number
  }>()

  const { t } = useI18n()

  const hasValue = computed(() => props.value !== null && props.value !== undefined)
</script>

<template>
  <div v-if="missing" class="d-flex flex-column ga-1" data-test="figure-market">
    <v-chip
      class="align-self-start"
      label
      prepend-icon="mdi-tag-outline"
      size="x-small"
      variant="outlined"
    >{{ t('minifigs.marketOnly') }}</v-chip>

    <div v-if="marketNow" class="d-flex flex-column">
      <span class="text-body-small text-medium-emphasis">{{ t('minifigs.marketNow') }}</span>
      <span class="text-body-large font-weight-medium">{{ exactMoney(marketNow) }}</span>

      <span v-if="marketNowAt" class="text-body-small text-medium-emphasis text-no-wrap">
        {{ t('collection.priceAt', { date: shortDate(marketNowAt) }) }}
      </span>
    </div>

    <span v-else class="text-body-medium text-medium-emphasis">{{ t('collection.unknownPrice') }}</span>
  </div>

  <div v-else class="d-flex flex-column ga-1" data-test="figure-value">
    <div class="d-flex align-end ga-2">
      <div class="d-flex flex-column">
        <span class="text-body-small text-medium-emphasis">{{ t('collection.purchased') }}</span>
        <span class="text-body-medium">{{ exactMoney(purchase) }}</span>
      </div>

      <v-icon class="mb-1" color="medium-emphasis" icon="mdi-arrow-right" size="16" />

      <div class="d-flex flex-column">
        <span class="text-body-small text-medium-emphasis">{{ t('collection.value') }}</span>

        <span v-if="!hasValue" class="text-body-medium text-medium-emphasis text-no-wrap">
          {{ t('collection.unknownPrice') }}
        </span>

        <span
          v-else
          class="text-body-large font-weight-medium"
          :title="approx ? t('collection.approxPriceHint') : undefined"
        ><span v-if="approx" class="text-medium-emphasis">≈ </span>{{ exactMoney(value) }}</span>
      </div>

      <v-chip
        v-if="profitPct !== null && profitPct !== undefined"
        class="ms-auto"
        :color="profitPct >= 0 ? 'positive' : 'negative'"
        label
        size="small"
        variant="tonal"
      >{{ percent(profitPct, { decimals: 0 }) }}</v-chip>
    </div>

    <div v-if="priceAt" class="text-body-small text-medium-emphasis text-no-wrap">
      {{ t('collection.priceAt', { date: shortDate(priceAt) }) }}
    </div>

    <!-- Súčet ráta každý kus, aj druhý a tretí tej istej figúrky. -->
    <div v-if="duplicates" class="text-body-small duplicates-note" data-test="figure-duplicates">
      <v-icon icon="mdi-information-outline" size="14" />
      {{ t('minifigs.valueWithDuplicatesPlural', duplicates, { named: { count: duplicates } }) }}
    </div>
  </div>
</template>

<style scoped>
.duplicates-note {
  color: #B25E00;
}

.v-theme--dark .duplicates-note {
  color: #FFB74D;
}
</style>
