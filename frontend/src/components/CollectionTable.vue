<script setup lang="ts">
  /**
   * Zbierka ako tabuľka. `v-data-table-virtual` kreslí len riadky na
   * obrazovke, takže aj 1500 riadkov sa posúva plynulo. Radí server: klik
   * na hlavičku (každý stĺpec okrem fotky, `SortHeader`) zmení kľúč a smer
   * v store (`sortFromHeader`), tabuľka sama neradí nič. Pri zoskupení je
   * riadok set alebo séria, pri „každom kuse“ kus. V režime výberu klik riadok označí, inak otvorí detail setu.
   *
   * Užšia než `COMPACT_BELOW` (meria sa tabuľka, nie okno: úzko je aj pri
   * otvorenom paneli filtrov) je tabuľka v podobe `mobile` bez hlavičky
   * a riadok je kompaktný: fotka, číslo a názov, séria s rokom a kusmi,
   * sumy a pod nimi stav, umiestnenie a dátum ceny. Radí výber Zoradiť.
   */
  import type { Selection } from '@/composables/useSelection'
  import type { SortDir } from '@/stores/collection'
  import type { TableRow } from '@/utils/tableColumns'
  import type { VNodeRef } from 'vue'
  import { useElementSize } from '@vueuse/core'
  import { computed, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRouter } from 'vue-router'
  import { VDataTable, VDataTableVirtual } from 'vuetify/components'
  import SetImage from '@/components/SetImage.vue'
  import SortHeader from '@/components/SortHeader.vue'
  import { defaultDir, useCollectionStore } from '@/stores/collection'
  import { imageSrc } from '@/utils/imageSrc'
  import { COLUMNS, rowFromGroup, rowFromItem, sortFromHeader } from '@/utils/tableColumns'
  import { headerDir } from '@/utils/tableSort'

  /**
   * `fill`: široká obrazovka, tabuľka vyplní výšku výsledkov a posúva sa
   * sama (virtuálne, len riadky na obrazovke). Na telefóne sa posúva celá
   * stránka, preto obyčajná tabuľka bez vlastného posuvníka.
   */
  const props = defineProps<{ selection: Selection, sold: boolean, fill?: boolean }>()

  const { t } = useI18n()
  const router = useRouter()
  const collection = useCollectionStore()

  const rows = computed<TableRow[]>(() =>
    collection.grouping === 'item'
      ? collection.items.map(item => rowFromItem(item))
      : collection.grouped.map(row => rowFromGroup(row, props.sold)),
  )

  const COMPACT_BELOW = 900
  const card = ref<HTMLElement | null>(null)
  const { width } = useElementSize(card)
  /** Pred prvým meraním (šírka 0) ostáva široká tabuľka. */
  const compact = computed(() => width.value > 0 && width.value < COMPACT_BELOW)

  const headers = computed(() => compact.value
    ? [{ key: 'compact', title: '', sortable: false }]
    : COLUMNS.map(column => ({
      key: column.key,
      title: t(`table.${column.key}`),
      align: column.align ?? 'start',
      sortable: false,
      width: column.width,
    })))

  /** Smer šípky v hlavičke stĺpca, alebo null, keď sa podľa neho neradí. */
  function columnDir (key: string): SortDir | null {
    const column = COLUMNS.find(c => c.key === key)
    if (!column?.sort) return null
    return headerDir(column.sort, { sort: collection.sort, dir: collection.sortDir }, defaultDir)
  }

  function onHeader (key: string): void {
    const column = COLUMNS.find(c => c.key === key)
    if (!column) return
    const next = sortFromHeader(column, { sort: collection.sort, dir: collection.sortDir })
    if (!next) return
    // Nový kľúč najprv: watch v store pri zmene kľúča smer vynuluje.
    collection.sort = next.sort
    collection.sortDir = next.dir
  }

  /** Virtuálna tabuľka meria riadok cez itemRef; obyčajná ho nemá. */
  function rowRef (slot: unknown): VNodeRef | undefined {
    return (slot as { itemRef?: VNodeRef }).itemRef
  }

  function selected (row: TableRow): boolean {
    return typeof row.selectKey === 'number'
      ? props.selection.hasItem(row.selectKey)
      : props.selection.hasGroup(row.selectKey)
  }

  function onRow (row: TableRow): void {
    if (props.selection.active.value) {
      if (typeof row.selectKey === 'number') props.selection.toggleItem(row.selectKey)
      else props.selection.toggleGroup(row.selectKey)
      return
    }
    router.push({ name: 'set-detail', params: { num: row.num } })
  }

  /** Výška riadku s fotkou; virtuálna tabuľka ju potrebuje na odhad posúvania. */
  const PHOTO = 64
  const ROW_HEIGHT = 77
  const COMPACT_HEIGHT = 112
  const COMPACT_PHOTO = 56

  /** Druhý riadok kompaktnej podoby: séria · rok · kusy. */
  function compactMeta (row: TableRow): string {
    return [row.theme, row.year, t('collection.pieces', { count: row.quantity })].filter(Boolean).join(' · ')
  }

  /** Posledný riadok: stav · umiestnenie · dátum ceny, bez prázdnych. */
  function compactDetails (row: TableRow): string {
    return [conditionText(row.conditions), row.location, row.priceAt === '—' ? '' : row.priceAt]
      .filter(Boolean)
      .join(' · ')
  }

  function conditionText (conditions: Record<string, number>): string {
    const entries = Object.entries(conditions)
    if (entries.length === 1) return t(`condition.${entries[0]![0]}`)
    return entries.map(([key, n]) => `${n}× ${t(`condition.${key}`).toLowerCase()}`).join(', ')
  }
</script>

<template>
  <v-card
    ref="card"
    border
    class="collection-table-card"
    :class="{ 'collection-table-card--fill': fill, 'collection-table-card--compact': compact }"
    flat
  >
    <component
      :is="fill ? VDataTableVirtual : VDataTable"
      class="collection-table"
      density="compact"
      fixed-header
      :headers="headers"
      :height="fill ? '100%' : undefined"
      :hide-default-footer="!fill"
      :hide-default-header="compact"
      hover
      :item-height="fill ? (compact ? COMPACT_HEIGHT : ROW_HEIGHT) : undefined"
      item-value="key"
      :items="rows"
      :items-per-page="fill ? undefined : -1"
    >
      <template v-for="column in COLUMNS" :key="column.key" #[`header.${column.key}`]="{ column: header }">
        <SortHeader
          v-if="column.sort"
          :dir="columnDir(column.key)"
          :title="header.title ?? ''"
          @sort="onHeader(column.key)"
        />

        <template v-else>{{ header.title }}</template>
      </template>

      <!--
        Riadok musí odovzdať itemRef: virtuálna tabuľka z neho meria výšku.
        Bez neho by ostala pri prvých piatich riadkoch a ďalšie by neukázala.
      -->
      <template #item="slot">
        <tr
          v-if="compact"
          :ref="rowRef(slot)"
          class="collection-table__row"
          :class="{ 'collection-table__row--selected': selection.active.value && selected(slot.item) }"
          data-test="compact-row"
          @click="onRow(slot.item)"
        >
          <td class="collection-table__compact">
            <div class="compact-layout d-flex ga-3 align-start">
              <!-- Malá fotka vľavo v stĺpci pevnej šírky: fotky všetkých riadkov sú pod sebou. -->
              <div class="compact-photo">
                <SetImage :alt="slot.item.name" rounded="sm" :size="COMPACT_PHOTO" :src="imageSrc(slot.item.image) ?? undefined" />
              </div>

              <div class="flex-grow-1 min-width-0">
                <div class="compact-line">
                  <v-icon
                    v-if="selection.active.value"
                    class="me-1"
                    :color="selected(slot.item) ? 'primary' : undefined"
                    :icon="selected(slot.item) ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'"
                    size="small"
                  />

                  <span class="text-medium-emphasis me-2">{{ slot.item.num }}</span><span class="font-weight-medium">{{ slot.item.name }}</span>
                </div>

                <div class="compact-line text-body-small text-medium-emphasis">{{ compactMeta(slot.item) }}</div>

                <div class="compact-amounts d-flex flex-wrap text-body-medium">
                  <span class="text-no-wrap"><span class="text-medium-emphasis">{{ t('table.purchase') }}</span> {{ slot.item.purchase }}</span>
                  <span class="text-no-wrap"><span class="text-medium-emphasis">{{ t('table.value') }}</span> {{ slot.item.value }}</span>

                  <span
                    class="text-no-wrap"
                    :class="slot.item.profitSign > 0 ? 'text-positive' : slot.item.profitSign < 0 ? 'text-negative' : ''"
                  ><span class="text-medium-emphasis">{{ t('table.profit') }}</span> {{ slot.item.profit }}<template v-if="slot.item.profitPct !== '—'"> ({{ slot.item.profitPct }})</template></span>
                </div>

                <div class="compact-line text-body-small text-medium-emphasis">{{ compactDetails(slot.item) }}</div>
              </div>
            </div>
          </td>
        </tr>

        <tr
          v-else
          :ref="rowRef(slot)"
          class="collection-table__row"
          :class="{ 'collection-table__row--selected': selection.active.value && selected(slot.item) }"
          @click="onRow(slot.item)"
        >
          <!-- Malá fotka, nech sa set spozná; veľká je na kartách a v detaile. -->
          <td class="collection-table__photo">
            <SetImage :alt="slot.item.name" rounded="sm" :size="PHOTO" :src="imageSrc(slot.item.image) ?? undefined" />
          </td>

          <td class="text-no-wrap">
            <v-icon
              v-if="selection.active.value"
              class="me-1"
              :color="selected(slot.item) ? 'primary' : undefined"
              :icon="selected(slot.item) ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'"
              size="small"
            />{{ slot.item.num }}
          </td>

          <td>{{ slot.item.name }}</td>
          <td>{{ slot.item.theme }}</td>
          <td class="text-end">{{ slot.item.year ?? '—' }}</td>
          <td class="text-end">{{ slot.item.quantity }}</td>
          <td>{{ conditionText(slot.item.conditions) }}</td>
          <td>{{ slot.item.location }}</td>
          <td class="text-end text-no-wrap">{{ slot.item.purchase }}</td>
          <td class="text-end text-no-wrap">{{ slot.item.value }}</td>
          <td class="text-end text-no-wrap text-medium-emphasis">{{ slot.item.priceAt }}</td>

          <td
            class="text-end text-no-wrap"
            :class="slot.item.profitSign > 0 ? 'text-positive' : slot.item.profitSign < 0 ? 'text-negative' : ''"
          >{{ slot.item.profit }}</td>

          <td class="text-end text-no-wrap">{{ slot.item.profitPct }}</td>
          <td class="text-end text-no-wrap">{{ slot.item.cagr }}</td>
        </tr>
      </template>
    </component>
  </v-card>
</template>

<style scoped>
  .collection-table-card--fill {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .collection-table-card--fill .collection-table {
    flex: 1;
    min-height: 0;
  }

  /*
   * Pevné rozloženie: šírky z hlavičky platia pre všetky riadky, aj tie,
   * ktoré virtuálna tabuľka dokreslí pri posúvaní. Najmenšia šírka drží
   * stĺpce čitateľné; na úzkej obrazovke sa tabuľka posúva do strany.
   */
  .collection-table :deep(table) {
    table-layout: fixed;
    min-width: 1608px;
  }

  /* Kompaktná podoba: jeden stĺpec na celú šírku, nič sa neposúva do strany. */
  .collection-table-card--compact .collection-table :deep(table) {
    min-width: 0;
  }

  .collection-table-card--compact .collection-table :deep(td.collection-table__compact) {
    white-space: normal;
    padding-top: 8px !important;
    padding-bottom: 8px !important;
  }

  .compact-line {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Sumy v riadku s medzerou; Vuetify 4 nemá column-gap-* ani ga-x-*. */
  .compact-amounts {
    column-gap: 16px;
  }

  .compact-photo {
    flex: 0 0 72px;
    width: 72px;
  }

  .min-width-0 {
    min-width: 0;
  }

  /* Hlavička sa nesmie lámať („Kus / y“), šírky sú na to dosť veľké. */
  .collection-table :deep(th) {
    white-space: nowrap;
  }

  .collection-table :deep(td) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .collection-table__row {
    cursor: pointer;
  }

  /* Rovnako vysoké riadky ako tabuľka v Chcem. */
  .collection-table__photo {
    padding-top: 6px !important;
    padding-bottom: 6px !important;
  }

  .collection-table__row--selected {
    background: rgba(var(--v-theme-primary), 0.08);
  }
</style>
