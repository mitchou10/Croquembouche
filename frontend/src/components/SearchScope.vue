<script setup lang="ts">
import { computed, ref } from 'vue'
import { useCatalogue } from '../composables/useCatalogue'

/**
 * Where a search looks: in every model the person can see, or only in some they pick. `null` is « every model »; the
 * models picked are kept when it goes back to « every model », in case it was a slip.
 */
const scope = defineModel<string[] | null>({ required: true })
const { filter } = useCatalogue()

const picked = ref<string[]>([])
const query = ref('')
const all = computed(() => scope.value === null)
// Only models with a page to look like: a model with no document is not in the index.
const models = computed(() => filter(query.value).filter((t) => t.document))
const id = `scope-${Math.random().toString(36).slice(2, 8)}`

function choose(everything: boolean) {
  scope.value = everything ? null : [...picked.value]
}

function toggle(templateId: string) {
  picked.value = picked.value.includes(templateId) ? picked.value.filter((p) => p !== templateId) : [...picked.value, templateId]
  scope.value = [...picked.value]
}
</script>

<template>
  <fieldset class="fr-fieldset scope" :aria-labelledby="`${id}-legend`">
    <legend :id="`${id}-legend`" class="fr-fieldset__legend fr-text--regular">Où chercher</legend>
    <div class="fr-fieldset__element">
      <div class="fr-radio-group fr-radio-group--sm">
        <input :id="`${id}-all`" type="radio" :name="id" :checked="all" data-testid="scope-all" @change="choose(true)" />
        <label class="fr-label" :for="`${id}-all`">Tous les modèles que je peux voir</label>
      </div>
    </div>
    <div class="fr-fieldset__element">
      <div class="fr-radio-group fr-radio-group--sm">
        <input :id="`${id}-some`" type="radio" :name="id" :checked="!all" data-testid="scope-some" @change="choose(false)" />
        <label class="fr-label" :for="`${id}-some`">Seulement certains modèles</label>
      </div>
    </div>

    <div v-if="!all" class="scope__picker" data-testid="scope-picker">
      <input v-model="query" class="fr-input fr-input--sm" type="search" placeholder="Chercher un modèle" aria-label="Chercher un modèle" />
      <ul class="scope__list">
        <li v-for="model in models" :key="model.id" class="fr-checkbox-group fr-checkbox-group--sm">
          <input :id="`${id}-${model.id}`" type="checkbox" :checked="picked.includes(model.id)" :data-testid="`scope-model-${model.id}`" @change="toggle(model.id)" />
          <label class="fr-label" :for="`${id}-${model.id}`">{{ model.name }}</label>
        </li>
        <li v-if="!models.length" class="fr-hint-text">Aucun modèle avec un document d’exemple.</li>
      </ul>
      <p class="fr-hint-text fr-mb-0" data-testid="scope-count" role="status">
        {{ picked.length ? `${picked.length} modèle${picked.length > 1 ? 's' : ''} choisi${picked.length > 1 ? 's' : ''}` : 'Aucun modèle choisi' }}
      </p>
    </div>
  </fieldset>
</template>

<style scoped>
.scope {
  margin: 0;
  padding: 0;
}

.scope__picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.scope__list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 12rem;
  margin: 0;
  padding: 0.5rem;
  overflow-y: auto;
  border: 1px solid var(--border-default-grey);
  list-style: none;
}
</style>
