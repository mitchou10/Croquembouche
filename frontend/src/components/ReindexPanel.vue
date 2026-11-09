<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, postDropOldIndexes, postReindex } from '../data/api'

// The search for similar documents looks in an index the worker keeps. Another embedding model starts an empty one: the
// administrator has the catalogue sent to the worker again, and it is computed in the background.
const asking = ref(false)
const done = ref<{ templates: number; versions: number } | null>(null)
const fault = ref('')

async function reindex() {
  asking.value = true
  done.value = null
  fault.value = ''
  try {
    done.value = await postReindex()
  } catch (error) {
    fault.value = error instanceof ApiError ? error.message : 'Le serveur est injoignable.'
  } finally {
    asking.value = false
  }
}

// Deleting is for good (the old index is the way back to the previous model): it is asked twice.
const confirming = ref(false)
const dropped = ref(false)
const dropFault = ref('')

async function dropOld() {
  confirming.value = false
  dropped.value = false
  dropFault.value = ''
  try {
    await postDropOldIndexes()
    dropped.value = true
  } catch (error) {
    dropFault.value = error instanceof ApiError ? error.message : 'Le serveur est injoignable.'
  }
}

const plural = (n: number, word: string) => `${n} ${word}${n > 1 ? 's' : ''}`
</script>

<template>
  <section class="reindex" aria-labelledby="reindex-title">
    <h2 id="reindex-title" class="fr-h6 fr-mb-0">Index de recherche</h2>
    <p class="fr-mb-0">
      Les modèles sont comparés aux documents grâce à un index. Relancez-le après un changement du modèle d’indexation : les pages sont recalculées par le
      worker, en arrière-plan.
    </p>
    <div class="reindex__action">
      <button type="button" class="fr-btn fr-btn--secondary" :disabled="asking" data-testid="reindex" @click="reindex">
        {{ asking ? 'Envoi…' : 'Relancer l’indexation' }}
      </button>
      <p v-if="done" class="fr-mb-0" role="status" data-testid="reindex-done">
        Indexation demandée pour {{ plural(done.templates, 'modèle') }}<template v-if="done.versions"> et {{ plural(done.versions, 'ancienne version') }}</template>.
      </p>
      <p v-if="fault" class="fr-error-text fr-mb-0" role="alert" data-testid="reindex-fault">{{ fault }}</p>
    </div>
    <div class="reindex__action">
      <template v-if="!confirming">
        <button type="button" class="fr-btn fr-btn--tertiary" data-testid="drop-old" @click="confirming = true">Supprimer les anciens index</button>
      </template>
      <template v-else>
        <p class="fr-mb-0" role="alert" data-testid="drop-old-warning">
          Les index des anciens modèles seront supprimés pour de bon. Ne le faites qu’une fois l’indexation terminée : tant que le nouvel index est vide, rien n’est supprimé.
        </p>
        <button type="button" class="fr-btn fr-btn--secondary" data-testid="drop-old-confirm" @click="dropOld">Supprimer</button>
        <button type="button" class="fr-btn fr-btn--tertiary" data-testid="drop-old-cancel" @click="confirming = false">Annuler</button>
      </template>
      <p v-if="dropped" class="fr-mb-0" role="status" data-testid="drop-old-done">Suppression demandée.</p>
      <p v-if="dropFault" class="fr-error-text fr-mb-0" role="alert" data-testid="drop-old-fault">{{ dropFault }}</p>
    </div>
  </section>
</template>

<style scoped>
.reindex {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
}

.reindex__action {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}
</style>
