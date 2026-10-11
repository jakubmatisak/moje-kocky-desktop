<script setup lang="ts">
  /**
   * Prepínač Figúrok: Série (zoznam sérií a koľko z nich mám) a Moje figúrky
   * (jednotlivé kusy s filtrami a súčtami, obrazovka Zbierky). Sú to dve
   * trasy, prepínač len vedie medzi nimi.
   */
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'

  const { t } = useI18n()
  const route = useRoute()
</script>

<template>
  <div>
    <v-btn-toggle
      color="primary"
      data-test="figures-tabs"
      density="comfortable"
      mandatory
      :model-value="route.name === 'minifig-pieces' ? 'mine' : 'series'"
      variant="outlined"
    >
      <v-btn prepend-icon="mdi-view-module-outline" :to="{ name: 'minifigs' }" value="series">
        {{ t('minifigs.tabSeries') }}
      </v-btn>

      <v-btn prepend-icon="mdi-account-box-multiple-outline" :to="{ name: 'minifig-pieces' }" value="mine">
        {{ t('minifigs.tabMine') }}
      </v-btn>
    </v-btn-toggle>
  </div>
</template>
