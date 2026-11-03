<script setup lang="ts">
/**
 * The page of a model, to look at or to fill in: the document in one half, the rest in the other. On a wide screen the
 * page is fixed to the window (nothing to scroll to); on a narrow one the halves stack and the page scrolls as usual.
 */
</script>

<template>
  <div class="template-page">
    <header class="template-layout__header">
      <slot name="header" />
    </header>
    <div class="template-layout__grid">
      <aside class="template-layout__document">
        <slot name="document" />
      </aside>
      <div class="template-layout__side">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.template-layout__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

.template-layout__grid {
  display: grid;
  gap: 1.5rem;
  margin-top: 0.5rem;
}

.template-layout__document,
.template-layout__side {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

@media (min-width: 64em) {
  .template-page {
    display: flex;
    flex-direction: column;
    /* The content area has 1.5rem of padding all round: take back half of it, above and below. */
    height: calc(100dvh - 2rem);
    margin-block: -0.5rem;
  }

  .template-layout__header {
    flex-shrink: 0;
  }

  /* Two equal halves. */
  .template-layout__grid {
    flex: 1;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }

  .template-layout__document,
  .template-layout__side {
    min-height: 0;
  }

  /* Only as a last resort, on a window too short for it, does the side scroll. Positioned, so the visually hidden texts
     inside stay clipped by it instead of stretching the page. */
  .template-layout__side {
    position: relative;
    overflow-y: auto;
    padding-right: 0.25rem;
  }
}
</style>
