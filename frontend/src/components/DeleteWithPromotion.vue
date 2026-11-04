<script setup lang="ts">
import { ref } from 'vue'

/**
 * Deleting a model that has sub-models: one of them takes its place, and has to be chosen. It becomes a model of its
 * own and the others go under it.
 */
const props = defineProps<{ children: { id: string; name: string }[] }>()
const emit = defineEmits<{ confirm: [promote: string] }>()

const asking = ref(false)
const chosen = ref(props.children[0]?.id ?? '')

function open() {
  chosen.value = props.children.some((c) => c.id === chosen.value) ? chosen.value : (props.children[0]?.id ?? '')
  asking.value = true
}
</script>

<template>
  <div v-if="asking" class="promotion" role="group" aria-label="Supprimer ce modèle" data-testid="promotion">
    <label class="fr-label promotion__label" for="promote">Quel sous-modèle prend sa place ?</label>
    <select id="promote" v-model="chosen" class="fr-select promotion__select" data-testid="promote-select">
      <option v-for="child in children" :key="child.id" :value="child.id">{{ child.name }}</option>
    </select>
    <p class="fr-hint-text promotion__hint fr-mb-0">
      Il devient un modèle à part entière{{ children.length > 1 ? ', et les autres passent dessous' : '' }}.
    </p>
    <button type="button" class="fr-btn fr-btn--sm" data-testid="promote-confirm" @click="(asking = false), emit('confirm', chosen)">
      Oui, supprimer
    </button>
    <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" data-testid="promote-cancel" @click="asking = false">Annuler</button>
  </div>
  <button v-else type="button" class="fr-btn fr-btn--tertiary fr-icon-delete-line fr-btn--icon-left" data-testid="delete" @click="open">
    Supprimer
  </button>
</template>

<style scoped>
.promotion {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.promotion__label {
  font-weight: 700;
}

.promotion__select {
  width: auto;
  max-width: 16rem;
}

.promotion__hint {
  flex-basis: 100%;
}
</style>
