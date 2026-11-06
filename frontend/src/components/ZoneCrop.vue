<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { straighten } from '../composables/perspective'
import { pageUrl } from '../data/api'
import type { TemplateDocument, Zone } from '../data/mock'

/**
 * What a zone covers on a page of a document, nothing is fetched but the page itself: the page cut down to the bounding
 * box of the zone, or, when the zone is four corners that are not straight on the page (a document that was scanned
 * turned or at an angle), brought back to an upright rectangle (see `straighten`).
 */
const props = defineProps<{ document: TemplateDocument; zone: Zone; maxHeight?: number }>()

// The zone is in fractions of the page, so its shape on screen is only known once the page's own proportions are.
const ratio = ref<number | null>(null)
const natural = ref<{ width: number; height: number } | null>(null)
const onLoad = (event: Event) => {
  const img = event.target as HTMLImageElement
  if (!img.naturalHeight) return
  ratio.value = img.naturalWidth / img.naturalHeight
  natural.value = { width: img.naturalWidth, height: img.naturalHeight }
}

// A straightened zone is drawn on a canvas of a fixed size, then scaled down to the width the frame has.
const CANVAS = 400
const frame = ref<HTMLElement>()
const scale = ref(1)
let observer: ResizeObserver | undefined
const measure = () => {
  if (frame.value?.clientWidth) scale.value = frame.value.clientWidth / CANVAS
}
onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined' && frame.value) {
    observer = new ResizeObserver(measure)
    observer.observe(frame.value)
  }
})
onBeforeUnmount(() => observer?.disconnect())

const straight = computed(() => (natural.value ? straighten(props.zone.points, natural.value.width, natural.value.height, CANVAS) : null))

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
const aspect = computed(() => straight.value?.aspect ?? (ratio.value ? (box.value.w * ratio.value) / box.value.h : null))
const frameStyle = computed(() =>
  aspect.value ? { aspectRatio: String(aspect.value), width: `min(100%, ${height.value * aspect.value}rem)` } : { display: 'none' },
)
const imageStyle = computed(() =>
  straight.value && natural.value
    ? {
        // At its own pixel size, from the top left corner of the frame, then put straight and scaled down to the frame.
        width: `${natural.value.width}px`,
        height: `${natural.value.height}px`,
        left: '0',
        top: '0',
        transformOrigin: '0 0',
        transform: `scale(${scale.value}) ${straight.value.matrix}`,
      }
    : {
        width: `${100 / box.value.w}%`,
        left: `${(-box.value.x / box.value.w) * 100}%`,
        top: `${(-box.value.y / box.value.h) * 100}%`,
      },
)
</script>

<template>
  <div class="crop" data-testid="zone-crop">
    <div ref="frame" class="crop__frame" :style="frameStyle" :data-straightened="straight ? '' : undefined">
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
