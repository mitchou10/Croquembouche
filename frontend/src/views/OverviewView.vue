<script setup lang="ts">
import { computed } from 'vue'
import FixedPage from '../components/FixedPage.vue'
import ConsumptionSummary from '../components/ConsumptionSummary.vue'
import ReindexPanel from '../components/ReindexPanel.vue'
import StatTile from '../components/StatTile.vue'
import { hasConsumption, totalConsumption } from '../composables/consumption'
import { statsOf, useAnalyses } from '../composables/useAnalyses'
import { statusLabels, type Analysis } from '../data/mock'

const LIST_SIZE = 5

// The administrator's view of everything: how analyses are seen and used across the whole service, which are the most
// used, and which need a look.
const { analyses } = useAnalyses()

const stats = computed(() => statsOf(analyses.value))
const consumption = computed(() => totalConsumption(analyses.value))
const visibility = computed(() => ({
  public: analyses.value.filter((a) => a.isPublic).length,
  shared: analyses.value.filter((a) => !a.isPublic && a.shares.length).length,
  private: analyses.value.filter((a) => !a.isPublic && !a.shares.length).length,
}))

// How the uses are spread across the three states, as parts of a bar.
const bar = computed(() => {
  const total = stats.value.uses || 1
  return [
    { key: 'done', label: 'Terminées', n: stats.value.done, tone: 'success' },
    { key: 'running', label: 'En cours', n: stats.value.running, tone: 'info' },
    { key: 'failed', label: 'En erreur', n: stats.value.failed, tone: 'error' },
  ].map((part) => ({ ...part, percent: Math.round((part.n / total) * 100) }))
})

const mostUsed = computed(() => [...analyses.value].sort((a, b) => b.runs.length - a.runs.length || b.views - a.views).slice(0, LIST_SIZE))
// What is not going well or not finished: failed first, then the ones still running.
const toWatch = computed(() =>
  analyses.value
    .filter((a) => a.status !== 'done')
    .sort((a, b) => (a.status === b.status ? b.date.localeCompare(a.date) : a.status === 'failed' ? -1 : 1))
    .slice(0, LIST_SIZE),
)
const route = (a: Analysis) => ({ name: 'analysis-detail', params: { id: a.id } })
</script>

<template>
  <FixedPage :from="64">
    <template #header>
      <h1 class="overview__title fr-h3 fr-mb-0">Vue d’ensemble</h1>
      <DsfrBadge label="Administrateur" type="info" small />
    </template>

    <section class="overview__stats" aria-label="Chiffres de l’ensemble des analyses">
      <StatTile :value="analyses.length" label="Analyses" />
      <StatTile :value="stats.views" label="Vues" />
      <StatTile :value="stats.uses" label="Utilisations" />
      <StatTile :value="stats.done" label="Terminées" tone="success" />
      <StatTile :value="stats.running" label="En cours" tone="info" />
      <StatTile :value="stats.failed" label="En erreur" tone="error" />
    </section>

    <section class="overview__spread" aria-label="Répartition des utilisations">
      <div class="bar" role="img" :aria-label="bar.map((p) => `${p.label} : ${p.n}`).join(', ')">
        <span v-for="part in bar" :key="part.key" class="bar__part" :class="`bar__part--${part.tone}`" :style="{ width: `${part.percent}%` }" />
      </div>
      <p class="overview__visibility fr-mb-0" data-testid="visibility">
        {{ visibility.public }} publique{{ visibility.public > 1 ? 's' : '' }} · {{ visibility.shared }} partagée{{ visibility.shared > 1 ? 's' : '' }} ·
        {{ visibility.private }} privée{{ visibility.private > 1 ? 's' : '' }}
      </p>
    </section>

    <ConsumptionSummary
      v-if="hasConsumption(consumption)"
      :consumption="consumption"
      heading="Consommation de l’ensemble des utilisations mesurées"
      data-testid="overview-consumption"
    />

    <div class="overview__lists">
      <section class="overview__panel" aria-labelledby="top-title">
        <h2 id="top-title" class="fr-h6 fr-mb-0">Les plus utilisées</h2>
        <ol class="overview__list">
          <li v-for="a in mostUsed" :key="a.id" data-testid="most-used">
            <RouterLink :to="route(a)">{{ a.name }}</RouterLink>
            <span class="overview__count">{{ a.runs.length }} utilisation{{ a.runs.length > 1 ? 's' : '' }} · {{ a.views }} vue{{ a.views > 1 ? 's' : '' }}</span>
          </li>
        </ol>
      </section>

      <section class="overview__panel" aria-labelledby="watch-title">
        <h2 id="watch-title" class="fr-h6 fr-mb-0">À surveiller</h2>
        <p v-if="!toWatch.length" role="status">Rien à signaler : toutes les analyses sont terminées.</p>
        <ul v-else class="overview__list">
          <li v-for="a in toWatch" :key="a.id" data-testid="to-watch">
            <RouterLink :to="route(a)">{{ a.name }}</RouterLink>
            <DsfrBadge :label="statusLabels[a.status].label" :type="statusLabels[a.status].type" small />
            <span class="overview__count">{{ a.date }} · par {{ a.ownerName }}</span>
          </li>
        </ul>
      </section>
    </div>

    <ReindexPanel />
  </FixedPage>
</template>

<style scoped>
.overview__title {
  margin-right: auto;
}

.overview__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.75rem;
}

.overview__spread {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

.bar {
  display: flex;
  flex: 1 1 16rem;
  height: 0.75rem;
  overflow: hidden;
  background: var(--background-contrast-grey);
}

.bar__part--success {
  background: var(--background-action-high-success);
}

.bar__part--info {
  background: var(--background-action-high-blue-france);
}

.bar__part--error {
  background: var(--background-action-high-error);
}

.overview__visibility {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.overview__lists {
  display: grid;
  gap: 1rem;
  min-height: 0;
}

.overview__panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
}

.overview__list {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.overview__list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  padding: 0.375rem 0;
  border-bottom: 1px solid var(--border-default-grey);
}

.overview__count {
  margin-left: auto;
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

@media (min-width: 64em) {
  .overview__lists {
    flex: 1;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }

  .overview__panel {
    overflow-y: auto;
  }
}
</style>
