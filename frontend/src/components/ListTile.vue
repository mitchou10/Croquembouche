<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

/**
 * A compact card for a page of cards: tags, a title, a description of two lines, and a line of details. Everything fits
 * the height of a row, so the description is never squeezed out. With a `to`, the whole card is the link.
 */
defineProps<{ title: string; description: string; to?: RouteLocationRaw; selected?: boolean }>()
</script>

<template>
  <article class="tile" :class="{ 'tile--link': to, 'tile--selected': selected }">
    <div v-if="$slots.tags" class="tile__tags"><slot name="tags" /></div>
    <h2 class="tile__title fr-h6 fr-mb-0">
      <!-- The title is what the tile is called: a link, text, or something of the caller's own (a check box). -->
      <slot name="title">
        <RouterLink v-if="to" class="tile__link" :to="to">{{ title }}</RouterLink>
        <template v-else>{{ title }}</template>
      </slot>
    </h2>
    <p class="tile__description fr-mb-0">{{ description }}</p>
    <div class="tile__foot"><slot name="foot" /></div>
  </article>
</template>

<style scoped>
.tile {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  height: 100%;
  padding: 0.75rem 1rem;
  overflow: hidden;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
}

.tile--link:hover {
  background: var(--background-default-grey-hover);
}

/* Chosen (on a page where cards are picked). */
.tile--selected {
  border-color: var(--border-action-high-blue-france);
  background: var(--background-contrast-info);
  box-shadow: inset 0 0 0 1px var(--border-action-high-blue-france);
}

.tile__tags {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-height: 1.5rem;
  overflow: hidden;
}

.tile__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile__link {
  background-image: none;
  color: var(--text-action-high-blue-france);
}

/* The click area: the whole card. */
.tile__link::after {
  content: '';
  position: absolute;
  inset: 0;
}

.tile__link:focus-visible::after {
  outline: 2px solid #0a76f6;
  outline-offset: 2px;
}

.tile__description {
  display: -webkit-box;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  font-size: 0.875rem;
  line-height: 1.25rem;
}

.tile__foot {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 1.5rem;
}
</style>
