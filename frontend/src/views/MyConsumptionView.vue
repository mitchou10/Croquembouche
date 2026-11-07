<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ConsumptionSummary from '../components/ConsumptionSummary.vue'
import { formatCo2, formatDuration, formatEnergy, formatWater, hasConsumption } from '../composables/consumption'
import { fetchMyConsumption } from '../data/api'
import type { MyConsumption } from '../data/mock'

// What the person's own uses consumed: all of them, and the detail by analysis. It is theirs alone: the figures of
// someone else's uses are not told.
const mine = ref<MyConsumption | null>(null)
const failed = ref(false)

onMounted(async () => {
  try {
    mine.value = await fetchMyConsumption()
  } catch {
    failed.value = true
  }
})

const plural = (n: number, one: string, many: string) => `${n} ${n > 1 ? many : one}`
</script>

<template>
  <h1 class="fr-h3">Ma consommation</h1>
  <p class="fr-mb-3w">
    <RouterLink :to="{ name: 'settings' }" class="fr-link fr-icon-arrow-left-line fr-link--icon-left">Mon profil</RouterLink>
  </p>

  <p v-if="failed" class="fr-error-text" role="alert" data-testid="consumption-failed">Votre consommation n’a pas pu être chargée.</p>
  <p v-else-if="!mine" role="status" data-testid="consumption-loading">Chargement…</p>

  <template v-else>
    <p v-if="!mine.uses" class="fr-mb-0" data-testid="consumption-none">Vous n’avez pas encore testé d’analyse sur un document.</p>

    <template v-else>
      <p class="fr-text--sm" data-testid="consumption-uses">
        {{ plural(mine.uses, 'utilisation', 'utilisations') }}, dont {{ plural(mine.measured, 'mesurée', 'mesurées') }}.
        Une utilisation qui n’a pas été mesurée (avant cette fonction, ou une mesure qui a échoué) ne compte pour rien.
      </p>
      <ConsumptionSummary
        v-if="hasConsumption(mine.consumption)"
        :consumption="mine.consumption"
        heading="Toutes mes utilisations"
        data-testid="my-consumption-total"
        class="fr-mb-4w"
      />

      <h2 class="fr-h5">Détail par analyse</h2>
      <div class="fr-table fr-table--no-caption" data-testid="consumption-by-analysis">
        <div class="fr-table__wrapper">
          <div class="fr-table__container">
            <div class="fr-table__content">
              <table>
                <caption>Consommation de mes utilisations, par analyse</caption>
                <thead>
                  <tr>
                    <th scope="col">Analyse</th>
                    <th scope="col">Utilisations</th>
                    <th scope="col">Électricité</th>
                    <th scope="col">CO₂</th>
                    <th scope="col">Eau</th>
                    <th scope="col">Calcul</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="analysis in mine.analyses" :key="analysis.id" data-testid="consumption-row">
                    <td>
                      <RouterLink :to="{ name: 'analysis-detail', params: { id: analysis.id } }" class="fr-link" data-testid="consumption-analysis">{{ analysis.name }}</RouterLink>
                    </td>
                    <td data-testid="consumption-row-uses">
                      {{ analysis.uses }}<span v-if="analysis.measured < analysis.uses" class="fr-hint-text"> ({{ analysis.measured }} mesurée{{ analysis.measured > 1 ? 's' : '' }})</span>
                    </td>
                    <template v-if="analysis.measured">
                      <td data-testid="consumption-row-energy">{{ formatEnergy(analysis.consumption.energyWh) }}</td>
                      <td>{{ formatCo2(analysis.consumption.co2G) }}</td>
                      <td>{{ formatWater(analysis.consumption.waterMl) }}</td>
                      <td>{{ formatDuration(analysis.consumption.durationS) }}</td>
                    </template>
                    <td v-else colspan="4" class="fr-hint-text">Pas de mesure</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </template>
  </template>
</template>
