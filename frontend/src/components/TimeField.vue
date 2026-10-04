<script setup lang="ts">
  /**
   * Časové pole: text `HH:MM` a po kliknutí `v-time-picker` z Vuetify
   * v 24-hodinovom formáte. Nie `type="time"`: ten má v každom prehliadači
   * iný vzhľad a v slovenčine ukazuje AM/PM podľa systému.
   */
  import { ref } from 'vue'

  defineOptions({ inheritAttrs: false })

  const model = defineModel<string>({ default: '07:00' })
  const open = ref(false)
</script>

<template>
  <v-menu v-model="open" :close-on-content-click="false" location="bottom start">
    <template #activator="{ props: menu }">
      <v-text-field
        v-bind="{ ...menu, ...$attrs }"
        :model-value="model"
        prepend-inner-icon="mdi-clock-outline"
        readonly
      />
    </template>

    <v-card>
      <v-time-picker v-model="model" format="24hr" />

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false">OK</v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>
