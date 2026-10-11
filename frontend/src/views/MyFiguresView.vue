<script setup lang="ts">
  /**
   * Moje figúrky: kusy figúrok zo sérií (aj nerozbalené sáčky) na obrazovke
   * Zbierky so sekciou `figures`. Filtre (Umiestnenie, Krabica…), súčty
   * Kúpené · Hodnota · Zisk aj hromadná úprava sú tie isté ako v Zbierke.
   *
   * Vlastná trasa a obal, aby sa obrazovka pri prechode zo Zbierky pripojila
   * znova a nastavila si sekciu; inak by ju Vue použil tak, ako bola.
   */
  import FiguresTabs from '@/components/FiguresTabs.vue'
  import CollectionView from '@/views/CollectionView.vue'
</script>

<template>
  <CollectionView section="figures">
    <template #header>
      <FiguresTabs />
    </template>
  </CollectionView>
</template>
