<script setup lang="ts">
/** Tabs to switch between two or three panels of a page. The panel is the caller's: it shows what `modelValue` says. */
defineProps<{ tabs: { id: string; label: string }[]; label: string }>()
const selected = defineModel<string>({ required: true })

const ids = `tabs-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <div class="tabs" role="tablist" :aria-label="label">
    <button
      v-for="tab in tabs"
      :id="`${ids}-${tab.id}`"
      :key="tab.id"
      type="button"
      role="tab"
      class="tabs__tab"
      :aria-selected="selected === tab.id"
      :tabindex="selected === tab.id ? 0 : -1"
      @click="selected = tab.id"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.tabs__tab {
  padding: 0.5rem 0.75rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text-action-high-grey);
  font: inherit;
  cursor: pointer;
}

.tabs__tab[aria-selected='true'] {
  border-bottom-color: var(--border-action-high-blue-france);
  color: var(--text-action-high-blue-france);
  font-weight: 700;
}
</style>
