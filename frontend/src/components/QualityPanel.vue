<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { fetchQuality } from '../data/api'
import type { TemplateQuality } from '../data/mock'
import QualityBlocks from './QualityBlocks.vue'
import QualityHelp from './QualityHelp.vue'

/**
 * How right the analysis has been on a model, from what people decided of its predictions (validated, invalidated,
 * annotated): no set of documents is needed, the figures grow with every decision. Counts only: what a use found stays
 * private to whoever ran it.
 */
const props = defineProps<{ templateId: string }>()

const quality = ref<TemplateQuality | null>(null)
const failed = ref(false)

watch(
  () => props.templateId,
  async (id) => {
    quality.value = null
    failed.value = false
    try {
      quality.value = await fetchQuality(id)
    } catch {
      failed.value = true
    }
  },
  { immediate: true },
)

const percent = (value: number | null) => (value === null ? '—' : `${Math.round(value * 100)} %`)

/** Whether anyone has decided anything yet, on a page or on an element. */
const nothingDecided = computed(
  () => !!quality.value && quality.value.pages.reviewed + quality.value.elements.reviewed + quality.value.pages.missed + quality.value.elements.missed === 0,
)
</script>

<template>
  <div class="quality" data-testid="quality">
    <p v-if="failed" class="fr-error-text fr-mb-0" role="alert">La qualité de ce modèle n’a pas pu être chargée.</p>
    <p v-else-if="!quality" role="status" class="fr-mb-0">Chargement…</p>
    <template v-else>
      <p class="quality__intro fr-hint-text fr-mb-0">
        Mesurée à partir de ce que les utilisateurs valident, invalident ou corrigent dans leurs tests : elle se précise à chaque décision.
        La <strong>précision</strong> est la part des prédictions justes, le <strong>rappel</strong> la part de ce qui existait que l’analyse a trouvé.
      </p>
      <QualityHelp />
      <p v-if="nothingDecided" role="status" class="fr-mb-0" data-testid="quality-empty">
        Personne n’a encore validé ni corrigé de prédiction pour ce modèle.
      </p>

      <QualityBlocks :pages="quality.pages" :elements="quality.elements" />

      <section class="quality__block" aria-labelledby="quality-entities" data-testid="quality-entities">
        <h3 id="quality-entities" class="fr-h6 fr-mb-0">Entités</h3>
        <p v-if="!quality.entities.length" class="fr-hint-text fr-mb-0">Ce modèle n’a pas d’entité.</p>
        <div v-else class="scroll">
        <table class="quality__table">
          <caption class="fr-sr-only">Qualité de chaque entité du modèle</caption>
          <thead>
            <tr>
              <th scope="col">Entité</th>
              <th scope="col">Justes</th>
              <th scope="col">Fausses</th>
              <th scope="col">Manquées</th>
              <th scope="col">En attente</th>
              <th scope="col">Précision</th>
              <th scope="col">Rappel</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entity in quality.entities" :key="entity.id" data-testid="quality-entity">
              <th scope="row">{{ entity.name }}</th>
              <td>{{ entity.correct }}</td>
              <td>{{ entity.wrong }}</td>
              <td>{{ entity.missed }}</td>
              <td>{{ entity.pending }}</td>
              <td data-testid="entity-precision">{{ percent(entity.precision) }}</td>
              <td data-testid="entity-recall">{{ percent(entity.recall) }}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.scroll {
  overflow-x: auto;
}

.quality {
  display: grid;
  gap: 0.75rem;
}

.quality__block {
  display: grid;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem 0.625rem;
  border: 1px solid var(--border-default-grey);
}

.quality__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.quality__table th,
.quality__table td {
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid var(--border-default-grey);
  text-align: right;
}

.quality__table th:first-child {
  text-align: left;
}
</style>
