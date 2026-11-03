<script setup lang="ts">
import { ref } from 'vue'

/**
 * A button for what cannot be undone: the first click asks « sure? », and only the second does it. Leaving the question
 * puts the button back as it was.
 */
defineProps<{ label: string; question: string; confirmLabel?: string }>()
const emit = defineEmits<{ confirm: [] }>()

const asking = ref(false)
</script>

<template>
  <div v-if="asking" class="confirm" role="group" :aria-label="question" data-testid="confirm">
    <span class="confirm__question">{{ question }}</span>
    <button type="button" class="fr-btn fr-btn--sm" data-testid="confirm-yes" @click="(asking = false), emit('confirm')">
      {{ confirmLabel ?? label }}
    </button>
    <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" data-testid="confirm-no" @click="asking = false">Annuler</button>
  </div>
  <button v-else type="button" class="fr-btn fr-btn--tertiary fr-icon-delete-line fr-btn--icon-left" data-testid="delete" @click="asking = true">
    {{ label }}
  </button>
</template>

<style scoped>
.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.confirm__question {
  font-weight: 700;
}
</style>
