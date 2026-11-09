<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useId, watch } from 'vue'
import { createLayout, type Layout, type LayoutLink } from '../composables/forceLayout'
import type { Neighbour, NeighbourLink } from '../data/similar'

/**
 * The documents that look like the one that was sent, as a force graph: the document in the middle, the neighbours
 * around it, each as a picture of itself. The closer a neighbour looks to the document, the closer it sits and the
 * bigger and the thicker its link is; the neighbours that look like each other are linked too, which makes groups.
 * A node can be dragged (the others give way to it) and chosen, with the mouse, the finger or the keyboard.
 */
const props = defineProps<{
  query: { name: string; imageUrl: string }
  neighbours: Neighbour[]
  links: NeighbourLink[]
  selectedId?: string | null
}>()
const emit = defineEmits<{ select: [id: string | null] }>()

// The graph is drawn at the size it is shown at (the picture's own units are pixels), so it fills its frame.
const DEFAULT_WIDTH = 800
const DEFAULT_HEIGHT = 540
const width = ref(DEFAULT_WIDTH)
const height = ref(DEFAULT_HEIGHT)
// What a node needs besides its picture: its name and its score, below it.
const CAPTION = 22
const QUERY_ID = 'query'
const RATIO = 190 / 140 // a sheet is taller than wide
const uid = useId()

interface Drawn {
  id: string
  label: string
  similarity: number | null
  imageUrl: string
  width: number
  height: number
  x: number
  y: number
}

const sizes = computed(() => {
  const sizeOf = (similarity: number) => 56 + similarity * 28
  return new Map<string, number>([
    [QUERY_ID, 96],
    ...props.neighbours.map((n) => [n.id, sizeOf(n.similarity)] as [string, number]),
  ])
})

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
  const wanted: LayoutLink[] = [
    ...props.neighbours.map((n) => ({ source: QUERY_ID, target: n.id, distance: (150 + (1 - n.similarity) * 260) * scale, strength: 0.8 })),
    ...props.links.map((l) => ({ source: l.source, target: l.target, distance: (170 + (1 - l.similarity) * 200) * scale, strength: 0.25 })),
  ]
  layout = createLayout(
    [
      { id: QUERY_ID, radius: ((sizes.value.get(QUERY_ID) ?? 96) * RATIO) / 2 + CAPTION, fixed: true },
      ...props.neighbours.map((n) => ({ id: n.id, radius: ((sizes.value.get(n.id) ?? 60) * RATIO) / 2 + CAPTION })),
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

watch(() => [props.neighbours, props.links], build, { immediate: true })

// Follows the size of the frame: the layout is made again for it (it settles at once, and is the same each time).
let observer: ResizeObserver | undefined
onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !svg.value) return
  observer = new ResizeObserver(([entry]) => {
    const { width: w, height: h } = entry.contentRect
    if (!w || !h || (Math.abs(w - width.value) < 8 && Math.abs(h - height.value) < 8)) return
    width.value = Math.round(w)
    height.value = Math.round(h)
    build()
  })
  observer.observe(svg.value)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  cancelAnimationFrame(frame)
  stopDrag()
})

const nodes = computed<Drawn[]>(() => {
  const at = (id: string) => positions.value.get(id) ?? { x: width.value / 2, y: height.value / 2 }
  const size = (id: string) => sizes.value.get(id) ?? 60
  return [
    { id: QUERY_ID, label: props.query.name, similarity: null, imageUrl: props.query.imageUrl, ...at(QUERY_ID), width: size(QUERY_ID), height: size(QUERY_ID) * RATIO },
    ...props.neighbours.map((n) => ({ id: n.id, label: n.name, similarity: n.similarity, imageUrl: n.imageUrl, ...at(n.id), width: size(n.id), height: size(n.id) * RATIO })),
  ]
})

const edges = computed(() => {
  const at = (id: string) => positions.value.get(id)
  return [
    ...props.neighbours.map((n) => ({ key: `q-${n.id}`, from: QUERY_ID, to: n.id, similarity: n.similarity, strong: true })),
    ...props.links.map((l) => ({ key: `${l.source}-${l.target}`, from: l.source, to: l.target, similarity: l.similarity, strong: false })),
  ].flatMap((e) => {
    const a = at(e.from)
    const b = at(e.to)
    return a && b ? [{ ...e, x1: a.x, y1: a.y, x2: b.x, y2: b.y }] : []
  })
})

const percent = (similarity: number) => `${Math.round(similarity * 100)} %`
const shorten = (text: string) => (text.length > 22 ? `${text.slice(0, 21)}…` : text)
const ariaLabel = (n: Drawn) => (n.similarity === null ? `Document envoyé : ${n.label}` : `${n.label}, ressemblance ${percent(n.similarity)}`)

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
  // A press that hardly moved is a click.
  if (id && moved < 4) emit('select', id === QUERY_ID || props.selectedId === id ? null : id)
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
  if (id !== QUERY_ID) emit('select', props.selectedId === id ? null : id)
}

defineExpose({ nodes })
</script>

<template>
  <svg
    ref="svg"
    class="graph"
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
        <rect :x="-n.width / 2" :y="-n.height / 2" :width="n.width" :height="n.height" rx="4" />
      </clipPath>
    </defs>
    <g
      v-for="n in nodes"
      :key="n.id"
      class="graph__node"
      :class="{
        'graph__node--query': n.id === 'query',
        'graph__node--selected': n.id === selectedId,
        'graph__node--dragging': n.id === dragging,
      }"
      :transform="`translate(${n.x} ${n.y})`"
      :role="n.id === 'query' ? 'img' : 'button'"
      :tabindex="n.id === 'query' ? undefined : 0"
      :aria-label="ariaLabel(n)"
      :aria-pressed="n.id === 'query' ? undefined : n.id === selectedId"
      :data-testid="`node-${n.id}`"
      @pointerdown.prevent="onDown($event, n.id)"
      @keydown="onKey($event, n.id)"
    >
      <rect class="graph__frame" :x="-n.width / 2 - 3" :y="-n.height / 2 - 3" :width="n.width + 6" :height="n.height + 6" rx="6" />
      <image
        :href="n.imageUrl"
        :x="-n.width / 2"
        :y="-n.height / 2"
        :width="n.width"
        :height="n.height"
        preserveAspectRatio="xMidYMid slice"
        :clip-path="`url(#${uid}-${n.id})`"
      />
      <text class="graph__label" :y="n.height / 2 + 18" text-anchor="middle">{{ shorten(n.label) }}</text>
      <text v-if="n.similarity !== null" class="graph__score" :y="n.height / 2 + 34" text-anchor="middle">{{ percent(n.similarity) }}</text>
    </g>
  </svg>
</template>

<style scoped>
.graph {
  display: block;
  width: 100%;
  height: 100%;
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

.graph__node--query .graph__frame {
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
