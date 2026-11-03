<script setup lang="ts" generic="T extends object">
import { computed, ref, watch } from 'vue'
import { useGridPaging } from '../composables/useGridPaging'
import { useWideScreen } from '../composables/useWideScreen'
import PagerControls from './PagerControls.vue'

/**
 * Cards in a grid, a page at a time: as many per page as the room there is, so that a page fills what is left of the
 * window and never scrolls. Goes inside a FixedPage, which gives it that room.
 */
const props = withDefaults(
  defineProps<{
    items: T[]
    itemKey: (item: T) => string | number
    /** « modèle »: the count under the cards reads « 3 modèles ». */
    noun: string
    /** What follows the count: « 4 analyses au total ». */
    suffix?: string
    /** Back to the first page when this changes (a search, a filter). */
    resetKey?: unknown
    /** Narrowest a card gets: sets how many columns there are. */
    minCard?: string
    /** Height of a card, whatever it holds. */
    rowHeight?: string
    /** From which width (in em) the page is the size of the window, as the FixedPage around it. */
    fixedFrom?: 48 | 64
  }>(),
  { suffix: '', resetKey: undefined, minCard: '17rem', rowHeight: '10rem', fixedFrom: 48 },
)

const fixed = useWideScreen(props.fixedFrom)
const area = ref<HTMLElement>()
const grid = ref<HTMLElement>()
const { pageSize } = useGridPaging(area, grid, { enabled: fixed })

// What the page starts at is kept in cards, not in pages: resizing the window changes the page size, and the card at the
// top stays on the page shown.
const firstIndex = ref(0)
const pageCount = computed(() => Math.max(1, Math.ceil(props.items.length / pageSize.value)))
const page = computed({
  get: () => Math.min(Math.floor(firstIndex.value / pageSize.value), pageCount.value - 1),
  set: (value: number) => (firstIndex.value = value * pageSize.value),
})
const visible = computed(() => props.items.slice(page.value * pageSize.value, (page.value + 1) * pageSize.value))

watch(() => props.resetKey, () => (firstIndex.value = 0))

const total = computed(() => props.items.length)
</script>

<template>
  <div ref="area" class="paged__area" :class="{ 'paged__area--from-64': fixedFrom === 64 }">
    <slot v-if="items.length === 0" name="empty" />
    <div v-else ref="grid" class="paged__grid" :style="{ '--min-card': minCard, '--row-height': rowHeight }">
      <template v-for="item in visible" :key="itemKey(item)">
        <slot name="item" :item="item" />
      </template>
    </div>
  </div>

  <footer class="paged__footer" :class="{ 'paged__footer--from-64': fixedFrom === 64 }">
    <p class="fr-mb-0" data-testid="list-total">{{ total }} {{ noun }}{{ total > 1 ? 's' : '' }}{{ suffix }}</p>
    <PagerControls v-if="pageCount > 1" v-model="page" :count="pageCount" noun="Page" />
  </footer>
</template>

<style scoped>
/* The grid sets what the paging reads: its columns, its row height and its gap (see useGridPaging). A card is as tall as
   a row, whatever it holds (see ListTile, which is made for it). */
.paged__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--min-card), 1fr));
  grid-auto-rows: var(--row-height);
  gap: 1rem;
}

.paged__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

@media (min-width: 48em) {
  .paged__area:not(.paged__area--from-64) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .paged__footer:not(.paged__footer--from-64) {
    flex-shrink: 0;
    margin-top: 0;
  }
}

@media (min-width: 64em) {
  .paged__area--from-64 {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .paged__footer--from-64 {
    flex-shrink: 0;
    margin-top: 0;
  }
}
</style>
