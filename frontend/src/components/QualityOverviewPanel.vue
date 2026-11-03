<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchAllQuality, fetchMyQuality } from '../data/api'
import type { QualityOverview } from '../data/mock'
import QualityBlocks from './QualityBlocks.vue'

/**
 * How right the analysis has been over every model, from what people decided of its predictions: those of the person
 * (their own tests), or those of everyone (for an administrator). Counts only: what a use found stays private.
 */
const props = defineProps<{ scope: 'mine' | 'everyone' }>()

const overview = ref<QualityOverview | null>(null)
const failed = ref(false)

watch(
  () => props.scope,
  async (scope) => {
    overview.value = null
    failed.value = false
    try {
      overview.value = await (scope === 'mine' ? fetchMyQuality() : fetchAllQuality())
    } catch {
      failed.value = true
    }
  },
  { immediate: true },
)

const percent = (value: number | null) => (value === null ? '—' : `${Math.round(value * 100)} %`)
</script>

<template>
  <div class="overview" :data-testid="`quality-${scope}`">
    <p v-if="failed" class="fr-error-text fr-mb-0" role="alert">Les chiffres n’ont pas pu être chargés.</p>
    <p v-else-if="!overview" role="status" class="fr-mb-0">Chargement…</p>
    <template v-else>
      <p class="fr-hint-text fr-mb-0">
        <template v-if="scope === 'mine'">Mesurée à partir de ce que vous avez validé, invalidé ou corrigé dans vos tests.</template>
        <template v-else>
          Mesurée à partir de ce que les utilisateurs ont validé, invalidé ou corrigé
          <span v-if="overview.reviewers != null" data-testid="reviewers">({{ overview.reviewers }} personne{{ overview.reviewers > 1 ? 's' : '' }})</span>.
        </template>
        La <strong>précision</strong> est la part des prédictions justes, le <strong>rappel</strong> la part de ce qui existait que l’analyse a trouvé.
      </p>
      <p v-if="!overview.models.length" role="status" class="fr-mb-0" data-testid="quality-empty">
        {{ scope === 'mine' ? 'Vous n’avez encore validé ni corrigé aucune prédiction.' : 'Personne n’a encore validé ni corrigé de prédiction.' }}
      </p>

      <QualityBlocks :pages="overview.pages" :elements="overview.elements" />

      <section v-if="overview.models.length" class="overview__models" aria-labelledby="quality-models" data-testid="quality-models">
        <h3 id="quality-models" class="fr-h6 fr-mb-0">Par modèle</h3>
        <div class="scroll">
          <table class="overview__table">
          <caption class="fr-sr-only">Qualité de l’analyse sur chaque modèle</caption>
          <thead>
            <tr>
              <th scope="col" rowspan="2">Modèle</th>
              <th scope="colgroup" colspan="3">Pages</th>
              <th scope="colgroup" colspan="3">Éléments</th>
            </tr>
            <tr>
              <th scope="col">Décisions</th>
              <th scope="col">Précision</th>
              <th scope="col">Rappel</th>
              <th scope="col">Décisions</th>
              <th scope="col">Précision</th>
              <th scope="col">Rappel</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in overview.models" :key="model.id" data-testid="quality-model">
              <th scope="row">
                <RouterLink :to="{ name: 'catalogue-detail', params: { id: model.id } }">{{ model.name }}</RouterLink>
              </th>
              <td>{{ model.pages.reviewed }}</td>
              <td>{{ percent(model.pages.precision) }}</td>
              <td>{{ percent(model.pages.recall) }}</td>
              <td>{{ model.elements.reviewed }}</td>
              <td>{{ percent(model.elements.precision) }}</td>
              <td>{{ percent(model.elements.recall) }}</td>
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

.overview {
  display: grid;
  gap: 0.75rem;
}

.overview__models {
  display: grid;
  gap: 0.375rem;
}

.overview__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.overview__table th,
.overview__table td {
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid var(--border-default-grey);
  text-align: right;
}

.overview__table th:first-child {
  text-align: left;
}
</style>
