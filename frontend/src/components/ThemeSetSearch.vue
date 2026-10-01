<script setup lang="ts">
  /**
   * Série: nájsť set podľa názvu či čísla a zistiť, do ktorej série a roka
   * patrí. Hľadá len medzi setmi, ktoré appka pozná (katalóg a stiahnuté
   * vlny Brickset), nič nevolá von; upozornenie nad poľom to vopred povie.
   */
  import { useDebounceFn } from '@vueuse/core'
  import { computed, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { api } from '@/api/client'
  import SetImage from '@/components/SetImage.vue'
  import { count } from '@/utils/format'
  import { imageSrc } from '@/utils/imageSrc'

  interface Found {
    catalog: { catalog_num: string, name: string, image_url?: string | null }
    theme: string | null
    year: number | null
    owned: number
    wanted: boolean
  }

  const { t } = useI18n()
  const query = ref<string | null>('')
  const results = ref<Found[]>([])
  const loading = ref(false)
  const searched = ref(false)
  let asked = 0

  /** Koľko setov appka pozná; hľadanie nájde len medzi nimi. */
  const known = ref<number | null>(null)
  const note = computed(() => t('themes.findNote', {
    known: known.value === null
      ? ''
      : t('themes.findKnown', { count: t('collection.setsPlural', known.value, { named: { count: count(known.value) } }) }),
  }))
  onMounted(async () => {
    const { data } = await api.GET('/themes/find/count', {})
    known.value = data?.count ?? null
  })

  async function search (text: string): Promise<void> {
    const mine = ++asked
    loading.value = true
    const { data } = await api.GET('/themes/find', { params: { query: { q: text } } })
    if (mine !== asked) return
    results.value = (data ?? []) as Found[]
    searched.value = true
    loading.value = false
  }

  const later = useDebounceFn((text: string) => {
    search(text).catch(() => {
      loading.value = false
    })
  }, 300)

  watch(query, value => {
    const text = (value ?? '').trim()
    if (text.length < 2) {
      asked++
      results.value = []
      searched.value = false
      loading.value = false
      return
    }
    later(text)
  })
</script>

<template>
  <div class="d-flex flex-column ga-2" style="max-width: 720px">
    <v-alert density="compact" icon="mdi-information-outline" type="info" variant="tonal">
      {{ note }}
    </v-alert>

    <v-text-field
      v-model="query"
      clearable
      density="comfortable"
      hide-details
      :label="t('themes.findSet')"
      :loading="loading"
      prepend-inner-icon="mdi-cube-scan"
    />

    <v-list v-if="results.length > 0" border class="rounded" density="compact">
      <v-list-item
        v-for="found in results"
        :key="found.catalog.catalog_num"
        :to="found.theme ? { name: 'theme', params: { theme: found.theme }, query: found.year ? { year: String(found.year) } : {} } : { name: 'set-detail', params: { num: found.catalog.catalog_num } }"
      >
        <template #prepend>
          <SetImage
            :alt="found.catalog.name"
            class="me-3"
            rounded="sm"
            :size="40"
            :src="imageSrc(found.catalog.image_url) ?? undefined"
            style="width: 56px"
          />
        </template>

        <v-list-item-title>{{ found.catalog.name }}</v-list-item-title>

        <v-list-item-subtitle>
          {{ found.catalog.catalog_num }}
          <template v-if="found.theme"> · {{ found.theme }}<template v-if="found.year"> {{ found.year }}</template></template>
        </v-list-item-subtitle>

        <template #append>
          <v-chip
            v-if="found.owned > 0"
            color="primary"
            label
            size="x-small"
            variant="tonal"
          >{{ t('wishlist.owned', { count: t('collection.pieces', { count: found.owned }) }) }}</v-chip>

          <v-chip
            v-else-if="found.wanted"
            label
            prepend-icon="mdi-heart-outline"
            size="x-small"
            variant="tonal"
          >{{ t('nav.wishlist') }}</v-chip>
        </template>
      </v-list-item>
    </v-list>

    <div v-else-if="searched && !loading" class="text-body-medium text-medium-emphasis">
      {{ t('themes.findNone') }}
    </div>
  </div>
</template>
