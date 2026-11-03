<script setup lang="ts">
import type { ReviewedDetection } from '../data/mock'

/** An element the person drew by hand: nothing to be sure of, since it is their own annotation, and it can be taken away. */
defineProps<{ element: ReviewedDetection; position: number; modelName: (id: string) => string }>()
const emit = defineEmits<{ remove: [] }>()
</script>

<template>
  <div class="manual" data-testid="manual-element">
    <div class="manual__head">
      <h3 class="fr-h6 fr-mb-0">Élément {{ position }}</h3>
      <DsfrBadge label="Ajouté à la main" type="new" small />
    </div>
    <p class="fr-mb-0">
      Annoté avec <strong data-testid="manual-model">{{ element.review.templateId ? modelName(element.review.templateId) : '' }}</strong>.
    </p>
    <div>
      <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" data-testid="manual-remove" @click="emit('remove')">Supprimer cet élément</button>
    </div>
  </div>
</template>

<style scoped>
.manual {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
}

.manual__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
</style>
