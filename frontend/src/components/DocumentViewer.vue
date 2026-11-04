<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { canPreview } from '../composables/useCatalogue'
import { pageUrl } from '../data/api'
import { type Handle, pointsOf, type Rect, rectOf, resizeRect } from '../composables/zoneRect'
import type { Point, TemplateDocument, TemplateEntity, Zone } from '../data/mock'

const props = defineProps<{
  document: TemplateDocument
  /** Entities whose zone is outlined, numbered by their position. */
  entities?: TemplateEntity[]
  highlightId?: string
  /** When true, clicks on the image place the points of a zone, which is emitted once closed. */
  drawing?: boolean
  /** When true, the rectangle of the entity on show can be moved, resized (emitted as it goes) and deleted. */
  editable?: boolean
  /** When true, the image is shown whole inside the space its parent gives it (no scrolling), keeping its ratio. */
  fit?: boolean
}>()
const emit = defineEmits<{ draw: [zone: Zone]; cancel: []; update: [id: string, zone: Zone]; remove: [id: string] }>()

const MIN_ZOOM = 1
const MAX_ZOOM = 8
const ZOOM_STEP = 1.25
/** Below this many pixels of travel, a press is a click and not a drag. */
const CLICK_SLOP = 5
/** Within this many pixels of the first point, a click closes the polygon. */
const CLOSE_RADIUS = 12

const viewport = ref<HTMLElement>()
const stage = ref<HTMLElement>()

// ---------------------------------------------------------------- size and zoom
// The stage is the image at its fitted size times the zoom, inside a scrolling viewport: panning is scrolling.
// Zones are percentages of the stage, so they stay on the right spot whatever size it has.
const zoom = ref(1)
const available = ref({ width: 0, height: 0 })
const natural = ref<{ width: number; height: number } | null>(null)
let observer: ResizeObserver | undefined

onMounted(() => {
  if (!viewport.value || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    available.value = { width: entry.contentRect.width, height: entry.contentRect.height }
  })
  observer.observe(viewport.value)
})
onBeforeUnmount(() => observer?.disconnect())

function onLoad(event: Event) {
  const img = event.target as HTMLImageElement
  natural.value = { width: img.naturalWidth, height: img.naturalHeight }
}

// A document of several pages (a PDF's screenshots) is looked at one page at a time; the zones are of a page.
// The page shown (from 1): the parent can follow it, or take the viewer to a page.
const page = defineModel<number>('page', { default: 1 })
const pageCount = computed(() => props.document.pages ?? 1)
const imageUrl = computed(() => (props.document.id ? pageUrl(props.document.id, page.value) : props.document.url))

watch(
  () => props.document.url,
  () => {
    natural.value = null
    zoom.value = 1
    draft.value = []
    page.value = 1
  },
)

function goToPage(next: number) {
  const target = Math.min(Math.max(next, 1), pageCount.value)
  if (target === page.value) return
  natural.value = null
  draft.value = []
  page.value = target
}

// Looking at an entity brings its page up.
function showPageOf(id: string | undefined) {
  const zone = props.entities?.find((e) => e.id === id)?.zone
  if (zone) goToPage(zone.page)
}
watch(() => props.highlightId, showPageOf)
onMounted(() => showPageOf(props.highlightId)) // the one that is on show when the viewer opens too

const stageStyle = computed(() => {
  const size = natural.value
  const { width, height } = available.value
  if (!size || !size.width || !size.height || !width) return undefined
  // Fitted: the whole image in the space. Otherwise: the full width, the height following.
  const scale = props.fit && height ? Math.min(width / size.width, height / size.height) : width / size.width
  return { width: `${size.width * scale * zoom.value}px`, height: `${size.height * scale * zoom.value}px` }
})

const clampZoom = (value: number) => Math.min(Math.max(value, MIN_ZOOM), MAX_ZOOM)

/** Zooms keeping the point under (clientX, clientY) where it is; the centre of the viewport when none is given. */
async function setZoom(next: number, clientX?: number, clientY?: number) {
  const target = clampZoom(next)
  if (target === zoom.value) return
  const vp = viewport.value
  const st = stage.value
  if (!vp || !st) {
    zoom.value = target
    return
  }
  const view = vp.getBoundingClientRect()
  const ax = clientX ?? view.left + view.width / 2
  const ay = clientY ?? view.top + view.height / 2
  const before = st.getBoundingClientRect()
  const fx = before.width ? (ax - before.left) / before.width : 0.5
  const fy = before.height ? (ay - before.top) / before.height : 0.5
  zoom.value = target
  await nextTick()
  const after = st.getBoundingClientRect()
  vp.scrollLeft += after.left + fx * after.width - ax
  vp.scrollTop += after.top + fy * after.height - ay
}

const zoomIn = () => setZoom(zoom.value * ZOOM_STEP)
const zoomOut = () => setZoom(zoom.value / ZOOM_STEP)
const resetZoom = () => setZoom(1)

// Ctrl + wheel (and a trackpad pinch, which browsers report the same way) zooms; a plain wheel scrolls.
function onWheel(event: WheelEvent) {
  if (!event.ctrlKey) return
  event.preventDefault()
  setZoom(zoom.value * Math.exp(-event.deltaY * 0.0018), event.clientX, event.clientY)
}

// ---------------------------------------------------------------- zones shown
const topLeftOf = (points: Point[]) => ({
  x: Math.min(...points.map((p) => p.x)),
  y: Math.min(...points.map((p) => p.y)),
})

const shapes = computed(() =>
  (props.entities ?? [])
    .map((entity, index) => ({ entity, index }))
    .filter(({ entity }) => entity.zone && entity.zone.points.length >= 3 && entity.zone.page === page.value)
    .map(({ entity, index }) => {
      const points = entity.zone!.points
      const corner = topLeftOf(points)
      return {
        id: entity.id,
        // The name as it is typed (the zone follows the form); a number until there is one.
        label: entity.name.trim() || `Entité ${index + 1}`,
        highlighted: entity.id === props.highlightId,
        rect: rectOf(points),
        polygon: points.map((p) => `${p.x * 100},${p.y * 100}`).join(' '),
        labelStyle: { left: `${corner.x * 100}%`, top: `${corner.y * 100}%` },
      }
    }),
)

// ---------------------------------------------------------------- editing a rectangle
const HANDLES: Handle[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

/** The rectangle that can be edited: the one of the entity on show, when nothing is being drawn. */
const editing = computed(() => {
  if (!props.editable || props.drawing) return null
  const shape = shapes.value.find((s) => s.highlighted && s.rect)
  if (!shape) return null
  const r = shape.rect!
  return {
    id: shape.id,
    label: shape.label,
    style: {
      left: `${r.x0 * 100}%`,
      top: `${r.y0 * 100}%`,
      width: `${(r.x1 - r.x0) * 100}%`,
      height: `${(r.y1 - r.y0) * 100}%`,
    },
  }
})

let grab: { id: string; handle: Handle; from: Point; start: Rect } | null = null

function onGrab(event: PointerEvent, handle: Handle) {
  const shape = shapes.value.find((s) => s.id === editing.value?.id)
  if (!shape?.rect || event.button !== 0) return
  event.stopPropagation() // not the pan of the stage
  event.preventDefault()
  ;(event.currentTarget as HTMLElement).closest<HTMLElement>('.doc-viewer__edit')?.focus()
  viewport.value!.setPointerCapture?.(event.pointerId)
  grab = { id: shape.id, handle, from: toPoint(event), start: shape.rect }
}

function onGrabMove(event: PointerEvent) {
  if (!grab) return false
  const here = toPoint(event)
  const next = resizeRect(grab.start, grab.handle, here.x - grab.from.x, here.y - grab.from.y)
  emit('update', grab.id, { page: page.value, points: pointsOf(next) })
  return true
}

function onEditKey(event: KeyboardEvent) {
  if (!editing.value || (event.key !== 'Delete' && event.key !== 'Backspace')) return
  event.preventDefault()
  emit('remove', editing.value.id)
}

// ---------------------------------------------------------------- drawing
type Tool = 'polygon' | 'rectangle'
const tool = ref<Tool>('polygon')
const draft = ref<Point[]>([]) // polygon: the points placed so far
const cursor = ref<Point | null>(null) // polygon: where the next segment would end
const dragRect = ref<{ from: Point; to: Point } | null>(null) // rectangle: the corner pressed and the one dragged to
const spaceHeld = ref(false)

const clamp01 = (n: number) => Math.min(Math.max(n, 0), 1)

function toPoint(event: { clientX: number; clientY: number }): Point {
  const rect = stage.value!.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return { x: 0, y: 0 }
  return { x: clamp01((event.clientX - rect.left) / rect.width), y: clamp01((event.clientY - rect.top) / rect.height) }
}

function distancePx(a: Point, b: Point) {
  const rect = stage.value!.getBoundingClientRect()
  return Math.hypot((a.x - b.x) * rect.width, (a.y - b.y) * rect.height)
}

function finish(points: Point[]) {
  draft.value = []
  cursor.value = null
  dragRect.value = null
  if (points.length >= 3) emit('draw', { page: page.value, points })
}

const closeDraft = () => draft.value.length >= 3 && finish(draft.value)
const undoPoint = () => (draft.value = draft.value.slice(0, -1))
function cancelDrawing() {
  draft.value = []
  cursor.value = null
  dragRect.value = null
  emit('cancel')
}

// Pointer: a drag pans (always without a drawing tool, or with the middle button / Space held while drawing), and a
// short press is a click that places a point; with the rectangle tool, a drag draws.
let press: { x: number; y: number; scrollLeft: number; scrollTop: number; pan: boolean; at: Point } | null = null

function onPointerDown(event: PointerEvent) {
  if (event.button > 1) return
  const vp = viewport.value!
  const pan = !props.drawing || event.button === 1 || spaceHeld.value
  press = { x: event.clientX, y: event.clientY, scrollLeft: vp.scrollLeft, scrollTop: vp.scrollTop, pan, at: toPoint(event) }
  event.preventDefault()
  vp.setPointerCapture?.(event.pointerId)
  if (!pan && tool.value === 'rectangle') dragRect.value = { from: press.at, to: press.at }
}

function onPointerMove(event: PointerEvent) {
  if (onGrabMove(event)) return
  const vp = viewport.value!
  if (press?.pan) {
    vp.scrollLeft = press.scrollLeft - (event.clientX - press.x)
    vp.scrollTop = press.scrollTop - (event.clientY - press.y)
    return
  }
  if (!props.drawing || !stage.value) return
  const point = toPoint(event)
  if (dragRect.value) dragRect.value = { ...dragRect.value, to: point }
  else if (draft.value.length) cursor.value = point
}

function onPointerUp(event: PointerEvent) {
  grab = null
  const current = press
  press = null
  if (!current || current.pan || !props.drawing) return
  const travelled = Math.hypot(event.clientX - current.x, event.clientY - current.y)

  if (tool.value === 'rectangle') {
    const r = dragRect.value
    dragRect.value = null
    if (!r || travelled < CLICK_SLOP) return
    const [x0, x1] = [Math.min(r.from.x, r.to.x), Math.max(r.from.x, r.to.x)]
    const [y0, y1] = [Math.min(r.from.y, r.to.y), Math.max(r.from.y, r.to.y)]
    finish([
      { x: x0, y: y0 },
      { x: x1, y: y0 },
      { x: x1, y: y1 },
      { x: x0, y: y1 },
    ])
    return
  }

  if (travelled >= CLICK_SLOP) return
  const point = toPoint(event)
  // Clicking the first point closes the polygon, once it has enough of them to be one.
  if (draft.value.length >= 3 && distancePx(point, draft.value[0]) <= CLOSE_RADIUS) {
    closeDraft()
    return
  }
  draft.value = [...draft.value, point]
}

function isTyping(event: KeyboardEvent) {
  const el = event.target as HTMLElement | null
  return !!el && (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || el.isContentEditable)
}

function onKeyDown(event: KeyboardEvent) {
  if (isTyping(event)) return
  if (event.key === 'Escape') cancelDrawing()
  else if (event.key === 'Enter') closeDraft()
  else if (event.key === 'Backspace') undoPoint()
  else if (event.key === ' ') {
    spaceHeld.value = true
    event.preventDefault() // not a page scroll
  }
}
const onKeyUp = (event: KeyboardEvent) => event.key === ' ' && (spaceHeld.value = false)

watch(
  () => props.drawing,
  (on) => {
    if (on) {
      window.addEventListener('keydown', onKeyDown)
      window.addEventListener('keyup', onKeyUp)
    } else {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      draft.value = []
      cursor.value = null
      dragRect.value = null
      spaceHeld.value = false
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
})

const draftLine = computed(() => {
  const points = cursor.value && draft.value.length ? [...draft.value, cursor.value] : draft.value
  return points.map((p) => `${p.x * 100},${p.y * 100}`).join(' ')
})

const dragRectStyle = computed(() => {
  const r = dragRect.value
  if (!r) return undefined
  return {
    left: `${Math.min(r.from.x, r.to.x) * 100}%`,
    top: `${Math.min(r.from.y, r.to.y) * 100}%`,
    width: `${Math.abs(r.to.x - r.from.x) * 100}%`,
    height: `${Math.abs(r.to.y - r.from.y) * 100}%`,
  }
})

const hint = computed(() =>
  tool.value === 'rectangle'
    ? 'Faites glisser pour tracer un rectangle.'
    : draft.value.length >= 3
      ? 'Cliquez sur le premier point ou appuyez sur Entrée pour fermer la zone.'
      : 'Cliquez pour placer les points de la zone.',
)
</script>

<template>
  <div class="doc-viewer" :class="{ 'doc-viewer--fit': fit }">
    <template v-if="canPreview(document)">
      <div class="doc-viewer__bar">
        <div class="doc-viewer__group" role="group" aria-label="Zoom">
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" :disabled="zoom <= MIN_ZOOM" title="Dézoomer" @click="zoomOut">
            −<span class="fr-sr-only"> Dézoomer</span>
          </button>
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" title="Ajuster à la zone" data-testid="zoom-level" @click="resetZoom">
            {{ Math.round(zoom * 100) }} %
          </button>
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" :disabled="zoom >= MAX_ZOOM" title="Zoomer" @click="zoomIn">
            +<span class="fr-sr-only"> Zoomer</span>
          </button>
        </div>

        <div v-if="pageCount > 1" class="doc-viewer__group" role="group" aria-label="Pages">
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" :disabled="page <= 1" title="Page précédente" @click="goToPage(page - 1)">
            ‹<span class="fr-sr-only"> Page précédente</span>
          </button>
          <span class="doc-viewer__page" data-testid="page-number">Page {{ page }} / {{ pageCount }}</span>
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" :disabled="page >= pageCount" title="Page suivante" @click="goToPage(page + 1)">
            ›<span class="fr-sr-only"> Page suivante</span>
          </button>
        </div>

        <div v-if="drawing" class="doc-viewer__group" role="group" aria-label="Outil de dessin">
          <button
            type="button"
            class="fr-btn fr-btn--sm"
            :class="tool === 'polygon' ? '' : 'fr-btn--tertiary'"
            :aria-pressed="tool === 'polygon'"
            @click="tool = 'polygon'"
          >
            Polygone
          </button>
          <button
            type="button"
            class="fr-btn fr-btn--sm"
            :class="tool === 'rectangle' ? '' : 'fr-btn--tertiary'"
            :aria-pressed="tool === 'rectangle'"
            @click="tool = 'rectangle'"
          >
            Rectangle
          </button>
          <template v-if="tool === 'polygon'">
            <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" title="Retirer le dernier point" :disabled="!draft.length" @click="undoPoint">
              Défaire
            </button>
            <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" title="Fermer la zone" :disabled="draft.length < 3" @click="closeDraft">
              Fermer
            </button>
          </template>
        </div>
      </div>

      <!-- The pointer is captured by this element, so it is the one that receives the moves and the release. -->
      <div
        ref="viewport"
        class="doc-viewer__viewport"
        data-testid="document-viewport"
        @wheel="onWheel"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="((press = null), (grab = null))"
      >
        <div
          ref="stage"
          class="doc-viewer__stage"
          :class="{ 'doc-viewer__stage--drawing': drawing && !spaceHeld, 'doc-viewer__stage--zoomed': zoom > 1 }"
          :style="stageStyle"
          data-testid="document-stage"
          @pointerdown="onPointerDown"
        >
          <img :src="imageUrl" :alt="`Aperçu de ${document.name}`" draggable="false" @load="onLoad" />

          <svg class="doc-viewer__shapes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <polygon
              v-for="shape in shapes"
              :key="shape.id"
              :points="shape.polygon"
              class="doc-viewer__polygon"
              :class="{ 'doc-viewer__polygon--highlight': shape.highlighted }"
              data-testid="entity-zone"
            />
            <polyline v-if="draftLine" :points="draftLine" class="doc-viewer__draft" />
          </svg>

          <div
            v-if="editing"
            class="doc-viewer__edit"
            :style="editing.style"
            tabindex="0"
            role="group"
            :aria-label="`Zone de ${editing.label} : Suppr pour la supprimer`"
            data-testid="rect-edit"
            @pointerdown="onGrab($event, 'move')"
            @keydown="onEditKey"
          >
            <span
              v-for="handle in HANDLES"
              :key="handle"
              class="doc-viewer__handle"
              :class="`doc-viewer__handle--${handle}`"
              :data-testid="`rect-handle-${handle}`"
              @pointerdown="onGrab($event, handle)"
            />
          </div>

          <span
            v-for="shape in shapes"
            :key="shape.id"
            class="doc-viewer__label"
            :class="{ 'doc-viewer__label--highlight': shape.highlighted }"
            :style="shape.labelStyle"
            :title="shape.label"
            data-testid="entity-label"
          >
            {{ shape.label }}
          </span>

          <span
            v-for="(point, index) in draft"
            :key="index"
            class="doc-viewer__vertex"
            :class="{ 'doc-viewer__vertex--first': index === 0 }"
            :style="{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }"
            data-testid="draft-point"
          />
          <div v-if="dragRectStyle" class="doc-viewer__rect" :style="dragRectStyle" />
        </div>
      </div>

      <p v-if="drawing" class="doc-viewer__hint" role="status">
        {{ hint }} <span class="doc-viewer__keys">Ctrl + molette : zoom · Espace + glisser : déplacer</span>
      </p>
    </template>

    <p v-else class="doc-viewer__nopreview" data-testid="no-preview">
      Aperçu indisponible pour ce type de document ({{ document.name }}).
    </p>
  </div>
</template>

<style scoped>
.doc-viewer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 100%;
}

.doc-viewer--fit {
  height: 100%;
  min-height: 0;
}

.doc-viewer__bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.75rem;
}

.doc-viewer__group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.doc-viewer__page {
  padding: 0 0.25rem;
  font-size: 0.875rem;
  white-space: nowrap;
}

/* The scroller. Centres the image while it is smaller than the space, and scrolls once it is larger. */
.doc-viewer__viewport {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--border-default-grey);
  background: var(--background-alt-grey);
  line-height: 0;
}

.doc-viewer:not(.doc-viewer--fit) .doc-viewer__viewport {
  max-height: 70vh;
}

.doc-viewer__stage {
  position: relative;
  flex: none;
  margin: auto;
  max-width: 100%;
  user-select: none;
  cursor: grab;
  touch-action: none;
}

.doc-viewer__stage--zoomed {
  max-width: none;
}

.doc-viewer__stage--drawing {
  cursor: crosshair;
}

.doc-viewer__stage img {
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.doc-viewer__shapes {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.doc-viewer__polygon {
  fill: rgb(0 0 145 / 14%);
  stroke: var(--border-action-high-blue-france);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.doc-viewer__polygon--highlight {
  fill: rgb(206 5 0 / 16%);
  stroke: var(--border-plain-error);
}

.doc-viewer__draft {
  fill: rgb(206 5 0 / 10%);
  stroke: var(--border-plain-error);
  stroke-width: 2;
  stroke-dasharray: 6 4;
  vector-effect: non-scaling-stroke;
}

.doc-viewer__rect {
  position: absolute;
  border: 2px dashed var(--border-plain-error);
  background: rgb(206 5 0 / 10%);
  pointer-events: none;
}

.doc-viewer__edit {
  position: absolute;
  cursor: move;
  outline: none;
}

.doc-viewer__edit:focus-visible {
  outline: 2px solid var(--border-active-blue-france);
  outline-offset: 2px;
}

/* Fixed size whatever the zoom, like the vertices. */
.doc-viewer__handle {
  position: absolute;
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid #fff;
  background: var(--background-action-high-blue-france);
  transform: translate(-50%, -50%);
}

.doc-viewer__handle--nw,
.doc-viewer__handle--n,
.doc-viewer__handle--ne {
  top: 0;
}
.doc-viewer__handle--sw,
.doc-viewer__handle--s,
.doc-viewer__handle--se {
  top: 100%;
}
.doc-viewer__handle--e,
.doc-viewer__handle--w {
  top: 50%;
}
.doc-viewer__handle--nw,
.doc-viewer__handle--w,
.doc-viewer__handle--sw {
  left: 0;
}
.doc-viewer__handle--n,
.doc-viewer__handle--s {
  left: 50%;
}
.doc-viewer__handle--ne,
.doc-viewer__handle--e,
.doc-viewer__handle--se {
  left: 100%;
}
.doc-viewer__handle--nw,
.doc-viewer__handle--se {
  cursor: nwse-resize;
}
.doc-viewer__handle--ne,
.doc-viewer__handle--sw {
  cursor: nesw-resize;
}
.doc-viewer__handle--n,
.doc-viewer__handle--s {
  cursor: ns-resize;
}
.doc-viewer__handle--e,
.doc-viewer__handle--w {
  cursor: ew-resize;
}

.doc-viewer__label {
  position: absolute;
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 0.375rem;
  background: var(--background-action-high-blue-france);
  color: #fff;
  font-size: 0.75rem;
  line-height: 1.25rem;
  pointer-events: none;
}

.doc-viewer__label--highlight {
  background: var(--background-action-high-error);
}

/* Fixed size whatever the zoom: a handle that grew with the image would hide what it points at. */
.doc-viewer__vertex {
  position: absolute;
  width: 0.625rem;
  height: 0.625rem;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--background-action-high-error);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.doc-viewer__vertex--first {
  width: 0.875rem;
  height: 0.875rem;
  box-shadow: 0 0 0 2px var(--border-plain-error);
}

.doc-viewer__hint {
  margin: 0;
  /* Always two lines of room, whatever is said: a message that grew a line would shrink the image and move it under the
     pointer, in the middle of a drawing. */
  min-height: 2.5rem;
  font-size: 0.8125rem;
  line-height: 1.25rem;
}

.doc-viewer__keys {
  color: var(--text-mention-grey);
}

.doc-viewer__nopreview {
  margin: 0;
  padding: 1rem;
  border: 1px dashed var(--border-default-grey);
  color: var(--text-mention-grey);
}
</style>
