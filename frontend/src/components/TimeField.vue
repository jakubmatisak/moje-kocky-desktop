<script setup lang="ts">
  /**
   * Časové pole: text `HH:MM` a po kliknutí `v-time-picker` z Vuetify
   * v 24-hodinovom formáte. Nie `type="time"`: ten má v každom prehliadači
   * iný vzhľad a v slovenčine ukazuje AM/PM podľa systému.
   *
   * Ručička posiela zmenu pri každom pohybe, preto sa čas drží rozpracovaný
   * a von ide až pri OK alebo zatvorení ponuky, a len keď sa zmenil.
   */
  import { ref, watch } from 'vue'

  defineOptions({ inheritAttrs: false })

  const model = defineModel<string>({ default: '07:00' })
  const open = ref(false)
  const draft = ref(model.value)

  function commit (): void {
    if (draft.value && draft.value !== model.value) model.value = draft.value
  }

  function confirm (): void {
    commit()
    open.value = false
  }

  watch(open, value => {
    if (value) draft.value = model.value
    else commit()
  })
</script>

<template>
  <v-menu v-model="open" :close-on-content-click="false" location="bottom start">
    <template #activator="{ props: menu }">
      <v-text-field
        v-bind="{ ...menu, ...$attrs }"
        append-inner-icon="mdi-clock-outline"
        :model-value="model"
        readonly
      />
    </template>

    <v-card>
      <v-time-picker v-model="draft" format="24hr" />

      <v-card-actions>
        <v-spacer />
        <v-btn data-test="time-ok" variant="text" @click="confirm">OK</v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>
