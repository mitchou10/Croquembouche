<script setup lang="ts">
import { formatCo2, formatEnergy, hasConsumption } from '../composables/consumption'
import { searchPageUrl } from '../data/api'
import type { SearchSummary } from '../data/search'
import ConfirmButton from './ConfirmButton.vue'

/** The searches the person has made, the newest first: each opens again, and can be deleted. */
defineProps<{ searches: SearchSummary[] }>()
const emit = defineEmits<{ remove: [id: string] }>()

const date = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
const STATUS = { running: 'En cours', failed: 'Échec', done: '' } as const
const scopeText = (s: SearchSummary) =>
  s.templateIds === null ? 'tous les modèles' : `${s.templateIds.length} modèle${s.templateIds.length > 1 ? 's' : ''}`
</script>

<template>
  <ul class="history" data-testid="history">
    <li v-for="s in searches" :key="s.id" class="history__item" :data-testid="`history-${s.id}`">
      <RouterLink class="history__link" :to="{ name: 'search-detail', params: { id: s.id } }">
        <img class="history__image" :src="searchPageUrl(s.id, 1)" alt="" />
        <span class="history__text">
          <span class="history__name">{{ s.fileName }}</span>
          <span class="history__meta">
            {{ date.format(new Date(s.createdAt)) }} · {{ s.pages }} page{{ s.pages > 1 ? 's' : '' }} · {{ s.k }} voisin{{ s.k > 1 ? 's' : '' }}
            par page · {{ scopeText(s) }}
          </span>
          <span v-if="hasConsumption(s.consumption)" class="history__meta" data-testid="history-consumption">
            {{ formatEnergy(s.consumption.energyWh) }} · {{ formatCo2(s.consumption.co2G) }}
          </span>
        </span>
        <span v-if="STATUS[s.status]" class="fr-badge fr-badge--sm" :class="s.status === 'failed' ? 'fr-badge--error' : 'fr-badge--info'">
          {{ STATUS[s.status] }}
        </span>
      </RouterLink>
      <ConfirmButton label="Supprimer" question="Supprimer cette recherche ?" confirm-label="Supprimer" @confirm="emit('remove', s.id)" />
    </li>
  </ul>
</template>

<style scoped>
.history {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.history__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
}

/* « Sure? » takes the place of the row instead of squeezing it: the list does not move when it is asked. */
.history__item :deep(.confirm) {
  position: absolute;
  inset: 0;
  flex-wrap: nowrap;
  justify-content: flex-end;
  padding: 0 0.5rem;
  background: var(--background-default-grey);
}

.history__item :deep(.confirm__question) {
  min-width: 0;
  margin-right: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history__link {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  background-image: none;
  color: var(--text-default-grey);
}

.history__image {
  width: 2.25rem;
  height: 3rem;
  object-fit: cover;
  border: 1px solid var(--border-default-grey);
}

.history__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.history__name {
  overflow: hidden;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history__meta {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}
</style>
