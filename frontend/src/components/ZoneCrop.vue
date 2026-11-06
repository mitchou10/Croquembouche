<script setup lang="ts">
import { computed, ref } from 'vue'
import { pageUrl } from '../data/api'
import type { TemplateDocument, Zone } from '../data/mock'

/** What a zone covers on a page of a document: the page cut down to the bounding box of the zone, nothing is fetched but the
 *  page itself. */
const props = defineProps<{ document: TemplateDocument; zone: Zone; maxHeight?: number }>()

// The zone is in fractions of the page, so its shape on screen is only known once the page's own proportions are.
const ratio = ref<number | null>(null)
const onLoad = (event: Event) => {
  const img = event.target as HTMLImageElement
  if (img.naturalHeight) ratio.value = img.naturalWidth / img.naturalHeight
}

const src = computed(() => (props.document.id ? pageUrl(props.document.id, props.zone.page) : props.document.url))
const box = computed(() => {
  const xs = props.zone.points.map((p) => p.x)
  const ys = props.zone.points.map((p) => p.y)
  const x = Math.min(...xs)
  const y = Math.min(...ys)
  // Never zero, so a flat zone still shows.
  return { x, y, w: Math.max(Math.max(...xs) - x, 0.005), h: Math.max(Math.max(...ys) - y, 0.005) }
})

const height = computed(() => props.maxHeight ?? 10)
// Wider than tall or the reverse, the crop keeps the shape of the zone on the page.
const aspect = computed(() => (ratio.value ? (box.value.w * ratio.value) / box.value.h : null))
const frameStyle = computed(() =>
  aspect.value ? { aspectRatio: String(aspect.value), width: `min(100%, ${height.value * aspect.value}rem)` } : { display: 'none' },
)
const imageStyle = computed(() => ({
  width: `${100 / box.value.w}%`,
  left: `${(-box.value.x / box.value.w) * 100}%`,
  top: `${(-box.value.y / box.value.h) * 100}%`,
}))
</script>

<template>
  <div class="crop" data-testid="zone-crop">
    <div class="crop__frame" :style="frameStyle">
      <img class="crop__image" :src="src" alt="" :style="imageStyle" @load="onLoad" />
    </div>
  </div>
</template>

<style scoped>
.crop__frame {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-default-grey);
  background: var(--background-contrast-grey);
}

.crop__image {
  position: absolute;
  max-width: none;
  height: auto;
}
</style>
