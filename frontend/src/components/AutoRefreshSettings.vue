<script setup lang="ts">
  /**
   * Automatická denná obnova cien (len desktop): prepínač, čas a počet.
   *
   * Uloží sa hneď do `preferences.autoRefresh`; server podľa toho prestaví
   * úlohu v Plánovači úloh Windows. Bez schopnosti `brickeconomy.prices`
   * (kľúč BrickEconomy a zapnutá obnova cien) je prepínač zakázaný.
   */
  import { computed, onMounted, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { api } from '@/api/client'
  import TimeField from '@/components/TimeField.vue'
  import { useAuthStore } from '@/stores/auth'
  import { useNotifyStore } from '@/stores/notify'
  import { useProfileStore } from '@/stores/preferences'
  import { usePriceStore } from '@/stores/prices'
  import { autoLastLabel } from '@/utils/autoRefresh'

  const { t } = useI18n()
  const auth = useAuthStore()
  const notify = useNotifyStore()
  const profile = useProfileStore()
  const prices = usePriceStore()

  const DEFAULTS = { enabled: false, time: '07:00', limit: 80 }
  const enabled = ref(DEFAULTS.enabled)
  const time = ref(DEFAULTS.time)
  const limit = ref<string>(String(DEFAULTS.limit))

  const allowed = computed(() => auth.can('brickeconomy.prices'))
  const limitValue = computed(() => {
    const value = Number(limit.value)
    return Number.isInteger(value) && value >= 1 && value <= 100 ? value : null
  })
  const last = computed(() => autoLastLabel(prices.status?.auto_last, (key, named) => t(key, named ?? {})))

  async function save (): Promise<void> {
    if (limitValue.value === null) return
    const body = { enabled: enabled.value && allowed.value, time: time.value, limit: limitValue.value }
    const { error } = await api.PUT('/auth/me/preferences/{key}', {
      params: { path: { key: 'autoRefresh' } },
      body,
    })
    if (error) {
      notify.error(error, t('sources.saveFailed'))
      return
    }
    profile.remember('autoRefresh', body)
    notify.success(t('notice.saved'))
  }

  onMounted(async () => {
    await profile.load()
    const stored = profile.get('autoRefresh') as Partial<typeof DEFAULTS> | null
    enabled.value = stored?.enabled === true
    time.value = typeof stored?.time === 'string' ? stored.time : DEFAULTS.time
    limit.value = String(typeof stored?.limit === 'number' ? stored.limit : DEFAULTS.limit)
    prices.fetchStatus()
  })
</script>

<template>
  <div class="d-flex flex-column ga-2" data-test="auto-refresh">
    <v-switch
      v-model="enabled"
      color="primary"
      data-test="auto-refresh-switch"
      density="compact"
      :disabled="!allowed"
      hide-details
      :label="t('sources.autoRefresh.switch')"
      @update:model-value="save"
    />

    <div class="text-body-small text-medium-emphasis">
      {{ allowed ? t('sources.autoRefresh.hint') : t('sources.autoRefresh.needsKey') }}
    </div>

    <div v-if="allowed" class="d-flex flex-wrap ga-3">
      <TimeField
        v-model="time"
        data-test="auto-refresh-time"
        density="compact"
        :disabled="!enabled"
        hide-details
        :label="t('sources.autoRefresh.time')"
        style="max-width: 160px"
        variant="outlined"
        @update:model-value="save"
      />

      <v-text-field
        v-model="limit"
        data-test="auto-refresh-limit"
        density="compact"
        :disabled="!enabled"
        :error-messages="limitValue === null ? t('sources.autoRefresh.limitInvalid') : undefined"
        :hint="t('sources.autoRefresh.limitHint')"
        inputmode="numeric"
        :label="t('sources.autoRefresh.limit')"
        persistent-hint
        style="max-width: 260px"
        variant="outlined"
        @change="save"
      />
    </div>

    <div v-if="last" class="text-body-small text-medium-emphasis" data-test="auto-refresh-last">{{ last }}</div>
  </div>
</template>
