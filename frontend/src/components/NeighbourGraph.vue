<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useId, watch } from 'vue'
import { createLayout, type Layout, type LayoutLink } from '../composables/forceLayout'

/**
 * The documents that look like the one that was sent, as a force graph. The pages of the document sit in a row in the
 * middle (one for an image, one for each page of a PDF), the pages of the models that look like them around, each as a
 * picture of itself, linked to the pages it looks like. The closer a neighbour looks to a page, the closer it sits and the
 * bigger and the thicker its link is; neighbours that look like each other are linked too, which makes groups.
 * A node can be dragged (the others give way to it); a neighbour can be chosen, with the mouse, the finger or the keyboard.
 */
interface Node {
  id: string
  label: string
  imageUrl: string
}
interface Neighbour extends Node {
  /** 0 to 1: the biggest it is on any page. */
  similarity: number
}

const props = defineProps<{
  pages: Node[]
  neighbours: Neighbour[]
  links: { source: string; target: string; similarity: number }[]
  selectedId?: string | null
}>()
const emit = defineEmits<{ select: [id: string | null] }>()

// The graph is drawn at the size of its frame (the picture's units are pixels), so it fills it; a document with many pages
// is wider than the frame, which then scrolls sideways.
const DEFAULT_WIDTH = 800
const DEFAULT_HEIGHT = 540
const PAGE_SLOT = 84
const RATIO = 190 / 140 // a sheet is taller than wide
// What a node needs besides its picture: its name and its score, below it.
const CAPTION = 22
const frameWidth = ref(DEFAULT_WIDTH)
const height = ref(DEFAULT_HEIGHT)
const width = computed(() => Math.max(frameWidth.value, props.pages.length > 1 ? props.pages.length * PAGE_SLOT : 0))
const uid = useId()

interface Drawn extends Node {
  similarity: number | null
  isPage: boolean
  w: number
  h: number
  x: number
  y: number
}

const pageWidth = computed(() => (props.pages.length === 1 ? 96 : Math.max(36, Math.min(80, width.value / props.pages.length - 16))))
const widthOf = (similarity: number | null) => (similarity === null ? pageWidth.value : 56 + similarity * 28)
const isPage = (id: string) => props.pages.some((p) => p.id === id)

const positions = shallowRef<Map<string, { x: number; y: number }>>(new Map())
let layout: Layout | null = null
let frame = 0

function publish() {
  positions.value = new Map(layout?.nodes.map((n) => [n.id, { x: n.x, y: n.y }]))
}

function build() {
  cancelAnimationFrame(frame)
  // The distances are for a graph of 540 px: a bigger frame spreads the nodes out, a smaller one brings them together.
  const scale = Math.min(width.value, height.value) / DEFAULT_HEIGHT
  // Never nearer than two nodes can be without covering each other, whatever the similarity says.
  const radii = new Map<string, number>([
    ...props.pages.map((p) => [p.id, (pageWidth.value * RATIO) / 2 + CAPTION] as [string, number]),
    ...props.neighbours.map((n) => [n.id, (widthOf(n.similarity) * RATIO) / 2 + CAPTION] as [string, number]),
  ])
  const wanted: LayoutLink[] = props.links.map((l) => {
    const toPage = isPage(l.source) || isPage(l.target)
    const wish = (toPage ? 150 + (1 - l.similarity) * 260 : 170 + (1 - l.similarity) * 200) * scale
    return {
      source: l.source,
      target: l.target,
      distance: Math.max(wish, (radii.get(l.source) ?? 0) + (radii.get(l.target) ?? 0) + 12),
      strength: toPage ? 0.8 : 0.25,
    }
  })
  layout = createLayout(
    [
      // The pages of the document, held, in a row.
      ...props.pages.map((p, i) => ({
        id: p.id,
        radius: (pageWidth.value * RATIO) / 2 + CAPTION,
        fixed: true,
        x: ((i + 0.5) * width.value) / props.pages.length,
        y: height.value / 2,
      })),
      ...props.neighbours.map((n) => ({ id: n.id, radius: (widthOf(n.similarity) * RATIO) / 2 + CAPTION })),
    ],
    wanted,
    width.value,
    height.value,
  )
  // Settled before it is shown: the nodes do not fly in from everywhere each time.
  layout.settle()
  publish()
}

// Moving the nodes: while one is dragged the layout runs, and stops when it has calmed down.
function animate() {
  if (!layout) return
  const energy = layout.tick()
  publish()
  frame = energy > 0.05 || dragging.value ? requestAnimationFrame(animate) : 0
}

watch(() => [props.pages, props.neighbours, props.links], build, { immediate: true })

// Follows the size of the frame: the layout is made again for it (it settles at once, and is the same each time).
const scroller = ref<HTMLElement>()
let observer: ResizeObserver | undefined
onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !scroller.value) return
  observer = new ResizeObserver(([entry]) => {
    const { width: w, height: h } = entry.contentRect
    if (!w || !h || (Math.abs(w - frameWidth.value) < 8 && Math.abs(h - height.value) < 8)) return
    frameWidth.value = Math.round(w)
    height.value = Math.round(h)
    build()
  })
  observer.observe(scroller.value)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  cancelAnimationFrame(frame)
  stopDrag()
})

const nodes = computed<Drawn[]>(() => {
  const at = (id: string) => positions.value.get(id) ?? { x: width.value / 2, y: height.value / 2 }
  const drawn = (n: Node, similarity: number | null): Drawn => {
    const w = widthOf(similarity)
    return { ...n, similarity, isPage: similarity === null, w, h: w * RATIO, ...at(n.id) }
  }
  return [...props.pages.map((p) => drawn(p, null)), ...props.neighbours.map((n) => drawn(n, n.similarity))]
})

const edges = computed(() =>
  props.links.flatMap((l) => {
    const a = positions.value.get(l.source)
    const b = positions.value.get(l.target)
    const strong = isPage(l.source) || isPage(l.target)
    return a && b ? [{ key: `${l.source}>${l.target}`, similarity: l.similarity, strong, x1: a.x, y1: a.y, x2: b.x, y2: b.y }] : []
  }),
)

const percent = (similarity: number) => `${Math.round(similarity * 100)} %`
const shorten = (text: string) => (text.length > 22 ? `${text.slice(0, 21)}…` : text)
const ariaLabel = (n: Drawn) =>
  n.similarity === null ? `Page du document envoyé : ${n.label}` : `${n.label}, ressemblance ${percent(n.similarity)}`

// --- dragging and choosing

const svg = ref<SVGSVGElement>()
const dragging = ref<string | null>(null)
let moved = 0
let origin = { x: 0, y: 0 }
let wasFixed = false

/** Where a pointer is in the graph's own coordinates, whatever size the picture is shown at. */
function toGraph(event: PointerEvent) {
  const box = svg.value?.getBoundingClientRect()
  if (!box?.width || !box.height) return { x: event.clientX, y: event.clientY }
  return { x: ((event.clientX - box.left) / box.width) * width.value, y: ((event.clientY - box.top) / box.height) * height.value }
}

function onMove(event: PointerEvent) {
  const node = layout?.nodes.find((n) => n.id === dragging.value)
  if (!node) return
  const at = toGraph(event)
  moved = Math.max(moved, Math.hypot(at.x - origin.x, at.y - origin.y))
  node.x = Math.max(node.radius, Math.min(width.value - node.radius, at.x))
  node.y = Math.max(node.radius, Math.min(height.value - node.radius, at.y))
  layout?.reheat()
  publish() // the node follows the pointer at once, the others give way on the next frames
  if (!frame) frame = requestAnimationFrame(animate)
}

function stopDrag() {
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUp)
  window.removeEventListener('pointercancel', onUp)
}

function onUp() {
  const id = dragging.value
  const node = layout?.nodes.find((n) => n.id === id)
  if (node) node.fixed = wasFixed
  dragging.value = null
  stopDrag()
  // A press that hardly moved is a click: on a page of the document it chooses nothing.
  if (id && moved < 4) emit('select', isPage(id) || props.selectedId === id ? null : id)
  layout?.reheat()
  if (!frame) frame = requestAnimationFrame(animate)
}

function onDown(event: PointerEvent, id: string) {
  const node = layout?.nodes.find((n) => n.id === id)
  if (!node || event.button > 0) return
  dragging.value = id
  moved = 0
  origin = toGraph(event)
  wasFixed = node.fixed
  node.fixed = true // held by the pointer, wherever it goes
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  window.addEventListener('pointercancel', onUp)
}

function onKey(event: KeyboardEvent, id: string) {
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  if (!isPage(id)) emit('select', props.selectedId === id ? null : id)
}

defineExpose({ nodes })
</script>

<template>
  <div ref="scroller" class="graph-frame">
    <svg
      ref="svg"
      class="graph"
      :width="width"
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      role="group"
      aria-label="Documents qui ressemblent à celui envoyé"
      data-testid="graph"
    >
      <g aria-hidden="true">
        <line
          v-for="e in edges"
          :key="e.key"
          class="graph__edge"
          :class="{ 'graph__edge--weak': !e.strong }"
          :x1="e.x1"
          :y1="e.y1"
          :x2="e.x2"
          :y2="e.y2"
          :stroke-width="e.strong ? 1 + e.similarity * 4 : 0.5 + e.similarity * 2"
        />
      </g>
      <defs>
        <clipPath v-for="n in nodes" :id="`${uid}-${n.id}`" :key="n.id">
          <rect :x="-n.w / 2" :y="-n.h / 2" :width="n.w" :height="n.h" rx="4" />
        </clipPath>
      </defs>
      <g
        v-for="n in nodes"
        :key="n.id"
        class="graph__node"
        :class="{
          'graph__node--page': n.isPage,
          'graph__node--selected': n.id === selectedId,
          'graph__node--dragging': n.id === dragging,
        }"
        :transform="`translate(${n.x} ${n.y})`"
        :role="n.isPage ? 'img' : 'button'"
        :tabindex="n.isPage ? undefined : 0"
        :aria-label="ariaLabel(n)"
        :aria-pressed="n.isPage ? undefined : n.id === selectedId"
        :data-testid="`node-${n.id}`"
        @pointerdown.prevent="onDown($event, n.id)"
        @keydown="onKey($event, n.id)"
      >
        <rect class="graph__frame" :x="-n.w / 2 - 3" :y="-n.h / 2 - 3" :width="n.w + 6" :height="n.h + 6" rx="6" />
        <image
          :href="n.imageUrl"
          :x="-n.w / 2"
          :y="-n.h / 2"
          :width="n.w"
          :height="n.h"
          preserveAspectRatio="xMidYMid slice"
          :clip-path="`url(#${uid}-${n.id})`"
        />
        <text class="graph__label" :y="n.h / 2 + 18" text-anchor="middle">{{ shorten(n.label) }}</text>
        <text v-if="n.similarity !== null" class="graph__score" :y="n.h / 2 + 34" text-anchor="middle">{{ percent(n.similarity) }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.graph-frame {
  width: 100%;
  min-width: 0;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}

.graph {
  display: block;
  touch-action: none;
  user-select: none;
}

.graph__edge {
  stroke: var(--border-action-high-blue-france);
  stroke-linecap: round;
  opacity: 0.55;
}

.graph__edge--weak {
  stroke: var(--border-default-grey);
  stroke-dasharray: 4 4;
  opacity: 0.9;
}

.graph__node {
  cursor: grab;
  outline: none;
}

.graph__node--dragging {
  cursor: grabbing;
}

.graph__frame {
  fill: var(--background-default-grey);
  stroke: var(--border-default-grey);
  stroke-width: 1;
}

.graph__node--page .graph__frame {
  stroke: var(--border-action-high-blue-france);
  stroke-width: 3;
}

.graph__node--selected .graph__frame {
  stroke: var(--border-action-high-blue-france);
  stroke-width: 3;
  filter: drop-shadow(0 2px 6px rgb(0 0 0 / 0.3));
}

.graph__node:focus-visible .graph__frame {
  stroke: #0a76f6;
  stroke-width: 4;
}

.graph__label,
.graph__score {
  fill: var(--text-default-grey);
  font-size: 13px;
  paint-order: stroke;
  stroke: var(--background-default-grey);
  stroke-width: 4px;
  pointer-events: none;
}

.graph__score {
  fill: var(--text-action-high-blue-france);
  font-weight: 700;
}
</style>
