<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  /** What the button is for, said by a screen reader: « Définition du type Montant ». */
  label: string
  /** Which edge of the button the panel lines up with, so that it stays inside the page. */
  align?: 'start' | 'end'
}>()

const open = ref(false)
const root = ref<HTMLElement>()
const panel = ref<HTMLElement>()
// Where the panel lines up: as asked, unless that would take it out of the window.
const alignEnd = ref(false)
const panelId = `info-${Math.random().toString(36).slice(2, 8)}`

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}
const onOutside = (event: Event) => {
  if (!root.value?.contains(event.target as Node)) open.value = false
}

async function keepInWindow() {
  alignEnd.value = props.align === 'end'
  await nextTick()
  const rect = panel.value?.getBoundingClientRect()
  if (!rect) return
  // Past the right edge: line up with the button's right side instead. Past the left edge: the other way.
  if (!alignEnd.value && rect.right > window.innerWidth - 8) alignEnd.value = true
  else if (alignEnd.value && rect.left < 8) alignEnd.value = false
}

// Only listening while it is open.
watch(open, async (isOpen) => {
  if (isOpen) {
    window.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onOutside)
    await keepInWindow()
  } else {
    window.removeEventListener('keydown', onKey)
    document.removeEventListener('pointerdown', onOutside)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('pointerdown', onOutside)
})
</script>

<template>
  <span ref="root" class="info-tip">
    <button
      type="button"
      class="info-tip__button"
      :aria-label="label"
      :aria-expanded="open"
      :aria-controls="open ? panelId : undefined"
      @click="open = !open"
    >
      <span aria-hidden="true">i</span>
    </button>
    <span v-if="open" :id="panelId" ref="panel" class="info-tip__panel" :class="{ 'info-tip__panel--end': alignEnd }" role="note">
      <slot />
    </span>
  </span>
</template>

<style scoped>
.info-tip {
  position: relative;
  display: inline-flex;
  vertical-align: middle;
}

.info-tip__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  padding: 0;
  border: 1px solid var(--border-action-high-blue-france);
  border-radius: 50%;
  background: transparent;
  color: var(--text-action-high-blue-france);
  font: italic 700 0.8125rem/1 serif;
  cursor: pointer;
}

.info-tip__button:hover,
.info-tip__button[aria-expanded='true'] {
  background: var(--background-action-high-blue-france);
  color: #fff;
}

/* Over the page, not in it: opening it moves nothing. */
.info-tip__panel {
  position: absolute;
  top: calc(100% + 0.375rem);
  left: 0;
  z-index: 20;
  width: max-content;
  max-width: min(20rem, 80vw);
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
  box-shadow: 0 4px 12px rgb(0 0 18 / 16%);
  color: var(--text-default-grey);
  font-size: 0.875rem;
  font-weight: 400;
  line-height: 1.4;
  text-align: left;
  white-space: normal;
}

.info-tip__panel--end {
  right: 0;
  left: auto;
}
</style>
