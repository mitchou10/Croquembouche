<script setup lang="ts">
import { computed } from 'vue'
import type { Review } from '../data/mock'

/**
 * What the person decides of a prediction: it is right, it is wrong, or it is something else, and then which of the models of
 * the analysis (the only ones offered). A decision can be taken back.
 */
const props = defineProps<{
  review: Review
  /** What an element can be annotated with: the models of the analysis, or the pages of them for a page of a document. */
  models: { id: string; name: string; page?: number }[]
  modelName: (id: string, page?: number | null) => string
}>()
const emit = defineEmits<{ review: [review: Review] }>()

const selectId = `annotate-${Math.random().toString(36).slice(2, 8)}`

const states = {
  pending: { label: 'À vérifier', tone: 'info' },
  validated: { label: 'Prédiction validée', tone: 'success' },
  invalidated: { label: 'Prédiction invalidée', tone: 'error' },
  annotated: { label: 'Annotée', tone: 'new' },
} as const

// An option is a model, or a page of one: « id » or « id#page ».
const optionValue = (model: { id: string; page?: number }) => (model.page ? `${model.id}#${model.page}` : model.id)
const chosen = computed(() =>
  props.review.status === 'annotated' && props.review.templateId
    ? optionValue({ id: props.review.templateId, page: props.review.templatePage })
    : '',
)

function annotate(event: Event) {
  const [templateId, page] = (event.target as HTMLSelectElement).value.split('#')
  if (templateId) emit('review', { status: 'annotated', templateId, ...(page && { templatePage: Number(page) }) })
}
</script>

<template>
  <div class="review" data-testid="review">
    <p class="review__state fr-mb-0">
      <DsfrBadge
        :label="review.status === 'annotated' && review.templateId ? `Annotée : ${modelName(review.templateId, review.templatePage)}` : states[review.status].label"
        :type="states[review.status].tone"
        small
        data-testid="review-state"
      />
      <button v-if="review.status !== 'pending'" type="button" class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline" data-testid="review-reset" @click="emit('review', { status: 'pending' })">
        Annuler ma décision
      </button>
    </p>
    <div class="review__actions">
      <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--secondary': review.status !== 'validated' }" :aria-pressed="review.status === 'validated'" data-testid="review-validate" @click="emit('review', { status: 'validated' })">
        Valider
      </button>
      <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--secondary': review.status !== 'invalidated' }" :aria-pressed="review.status === 'invalidated'" data-testid="review-invalidate" @click="emit('review', { status: 'invalidated' })">
        Invalider
      </button>
      <label class="fr-sr-only" :for="selectId">Annoter avec un modèle de l’analyse</label>
      <select :id="selectId" class="fr-select review__select" :value="chosen" data-testid="review-annotate" @change="annotate">
        <option value="" disabled>Annoter avec…</option>
        <option v-for="model in models" :key="optionValue(model)" :value="optionValue(model)">{{ model.name }}</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.review {
  display: grid;
  gap: 0.375rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-default-grey);
}

.review__state {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
}

.review__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.review__select {
  flex: 1 1 10rem;
  max-width: 16rem;
  margin-top: 0;
}
</style>
