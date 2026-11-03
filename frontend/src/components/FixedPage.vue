<script setup lang="ts">
/**
 * A page that is the size of the window: a header, then what is left of the window. Nothing to scroll to. Below 48 em
 * (where the sidebar stops sitting beside the content) it is an ordinary page that scrolls; a page that needs two
 * columns can ask for 64 em instead.
 */
withDefaults(defineProps<{ from?: 48 | 64 }>(), { from: 48 })
</script>

<template>
  <div class="fixed-page" :class="{ 'fixed-page--from-64': from === 64 }">
    <header v-if="$slots.header" class="fixed-page__header">
      <slot name="header" />
    </header>
    <slot />
  </div>
</template>

<style scoped>
.fixed-page {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.fixed-page__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

@media (min-width: 48em) {
  .fixed-page:not(.fixed-page--from-64) {
    /* The content area has 1.5rem of padding all round: take back half of it, above and below. */
    height: calc(100dvh - 2rem);
    margin-block: -0.5rem;
  }

  .fixed-page:not(.fixed-page--from-64) .fixed-page__header {
    flex-shrink: 0;
  }
}

@media (min-width: 64em) {
  .fixed-page--from-64 {
    height: calc(100dvh - 2rem);
    margin-block: -0.5rem;
  }

  .fixed-page--from-64 .fixed-page__header {
    flex-shrink: 0;
  }
}
</style>
