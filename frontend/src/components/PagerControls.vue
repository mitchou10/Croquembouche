<script setup lang="ts">
/** Previous / « 2 / 5 » / next, for showing one item of a list at a time (the page then keeps the same height). */
withDefaults(defineProps<{ count: number; noun: string; /** The noun is masculine: « élément suivant », not « suivante ». */ masculine?: boolean }>(), { masculine: false })
const index = defineModel<number>({ required: true })
</script>

<template>
  <div class="pager" role="group" :aria-label="`Parcourir : ${noun}`">
    <button
      type="button"
      class="fr-btn fr-btn--sm fr-btn--tertiary"
      :disabled="index <= 0"
      :title="`${noun} ${masculine ? 'précédent' : 'précédente'}`"
      @click="index--"
    >
      ‹<span class="fr-sr-only"> {{ noun }} {{ masculine ? 'précédent' : 'précédente' }}</span>
    </button>
    <span class="pager__count" aria-live="polite" data-testid="pager-count">{{ count ? `${index + 1} / ${count}` : '0' }}</span>
    <button
      type="button"
      class="fr-btn fr-btn--sm fr-btn--tertiary"
      :disabled="index >= count - 1"
      :title="`${noun} ${masculine ? 'suivant' : 'suivante'}`"
      @click="index++"
    >
      ›<span class="fr-sr-only"> {{ noun }} {{ masculine ? 'suivant' : 'suivante' }}</span>
    </button>
    <slot />
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.pager__count {
  min-width: 3.25rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
</style>
