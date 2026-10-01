<script setup lang="ts">
  /**
   * Otázka po kúpe setu, ktorý je v Chcem: odstrániť ho zo zoznamu, alebo
   * nechať (napríklad keď chcem ďalší kus). Zavretie bez voľby = nič sa
   * neuloží, volajúci to dostane ako ``cancel``.
   */
  import { useI18n } from 'vue-i18n'

  const open = defineModel<boolean>({ required: true })
  defineProps<{ name: string }>()
  const emit = defineEmits<{ choose: [keep: boolean], cancel: [] }>()

  const { t } = useI18n()

  function choose (keep: boolean): void {
    open.value = false
    emit('choose', keep)
  }

  function closed (value: boolean): void {
    if (!value) emit('cancel')
  }
</script>

<template>
  <v-dialog v-model="open" max-width="440" @update:model-value="closed">
    <v-card :title="t('wishlist.keepTitle')">
      <v-card-text>{{ t('wishlist.keepText', { name }) }}</v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn data-test="keep-wish" variant="text" @click="choose(true)">{{ t('wishlist.keepYes') }}</v-btn>

        <v-btn color="primary" data-test="drop-wish" variant="flat" @click="choose(false)">
          {{ t('wishlist.keepNo') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
