<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ConsumptionSummary from '../components/ConsumptionSummary.vue'
import FixedPage from '../components/FixedPage.vue'
import NeighbourGraph from '../components/NeighbourGraph.vue'
import { hasConsumption } from '../composables/consumption'
import { useCatalogue } from '../composables/useCatalogue'
import { useSearches } from '../composables/useSearches'
import { ApiError, searchPageUrl, templatePageUrl } from '../data/api'
import { pageNodeId } from '../data/search'

// What a search found: the pages of the document in a row, the pages of models that look like them around. It is opened
// from its address, so it can be opened again later; it is followed while the worker computes it.
const route = useRoute()
const { opened, open, reason } = useSearches()
const { pageLabel } = useCatalogue()

const id = computed(() => String(route.params.id))
const search = computed(() => (opened.value?.id === id.value ? opened.value : null))
const fault = ref('')
const selectedId = ref<string | null>(null)

watch(
  id,
  async (value) => {
    fault.value = ''
    selectedId.value = null
    try {
      await open(value)
    } catch (error) {
      fault.value = error instanceof ApiError && error.status === 404 ? 'Cette recherche n’existe pas ou a été supprimée.' : reason(error)
    }
  },
  { immediate: true },
)

const date = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long', timeStyle: 'short' })
const percent = (similarity: number) => `${Math.round(similarity * 100)} %`

const pages = computed(() =>
  search.value
    ? Array.from({ length: search.value.pages }, (_, i) => ({
        id: pageNodeId(i + 1),
        label: search.value!.pages > 1 ? `Page ${i + 1}` : search.value!.fileName,
        imageUrl: searchPageUrl(search.value!.id, i + 1),
      }))
    : [],
)

const neighbours = computed(() =>
  (search.value?.neighbours ?? []).map((n) => ({
    id: n.id,
    templateId: n.templateId,
    label: pageLabel(n.templateId, n.templatePage),
    similarity: n.similarity,
    imageUrl: templatePageUrl(n.templateId, n.templatePage, n.documentId),
    // The pages of the document it looks like, in order.
    onPages: (search.value?.links ?? [])
      .filter((l) => l.target === n.id && l.source.startsWith('page-'))
      .map((l) => Number(l.source.slice('page-'.length)))
      .sort((a, b) => a - b),
  })),
)
const selected = computed(() => neighbours.value.find((n) => n.id === selectedId.value) ?? null)

const scopeText = computed(() =>
  search.value?.templateIds == null
    ? 'tous les modèles'
    : `${search.value.templateIds.length} modèle${search.value.templateIds.length > 1 ? 's' : ''} choisi${search.value.templateIds.length > 1 ? 's' : ''}`,
)
</script>

<template>
  <FixedPage :from="64">
    <template #header>
      <div class="result__title">
        <p class="fr-mb-0">
          <RouterLink :to="{ name: 'search' }" class="fr-link fr-icon-arrow-left-line fr-link--icon-left" data-testid="back">Mes recherches</RouterLink>
        </p>
        <h1 class="fr-h4 fr-mb-0" data-testid="title">{{ search?.fileName ?? 'Recherche' }}</h1>
        <p v-if="search" class="fr-mb-0 fr-text--sm" data-testid="meta">
          {{ date.format(new Date(search.createdAt)) }} · {{ search.pages }} page{{ search.pages > 1 ? 's' : '' }} · {{ search.k }} voisin{{ search.k > 1 ? 's' : '' }} par
          page · {{ scopeText }}
        </p>
      </div>
      <RouterLink class="fr-btn fr-btn--secondary" :to="{ name: 'search' }" data-testid="again">Nouvelle recherche</RouterLink>
    </template>

    <p v-if="fault" class="fr-error-text fr-mb-0" role="alert" data-testid="fault">{{ fault }}</p>
    <p v-else-if="!search" role="status" class="fr-hint-text fr-mb-0" data-testid="loading">Chargement…</p>
    <p v-else-if="search.status === 'running'" role="status" class="fr-hint-text fr-mb-0" data-testid="running">Recherche des documents proches…</p>
    <p v-else-if="search.status === 'failed'" class="fr-error-text fr-mb-0" role="alert" data-testid="failed">
      La recherche a échoué. Relancez-la avec le même document.
    </p>

    <div v-else class="result">
      <section class="result__graph" aria-label="Graphe des voisins">
        <NeighbourGraph :pages="pages" :neighbours="neighbours" :links="search.links" :selected-id="selectedId" @select="selectedId = $event" />
      </section>

      <section class="result__side" aria-label="Documents proches">
        <h2 class="fr-h6 fr-mb-1w">{{ neighbours.length }} page{{ neighbours.length > 1 ? 's' : '' }} de modèles proche{{ neighbours.length > 1 ? 's' : '' }}</h2>
        <p v-if="!neighbours.length" class="fr-hint-text" data-testid="none">Aucun modèle avec un document d’exemple ne ressemble à celui-ci.</p>
        <ol class="result__list" data-testid="neighbours">
          <li v-for="n in neighbours" :key="n.id">
            <button
              type="button"
              class="neighbour"
              :class="{ 'neighbour--selected': n.id === selectedId }"
              :aria-pressed="n.id === selectedId"
              :data-testid="`neighbour-${n.id}`"
              @click="selectedId = n.id === selectedId ? null : n.id"
            >
              <img class="neighbour__image" :src="n.imageUrl" alt="" />
              <span class="neighbour__name">
                {{ n.label }}
                <span v-if="pages.length > 1 && n.onPages.length" class="neighbour__pages" data-testid="neighbour-pages">
                  · page{{ n.onPages.length > 1 ? 's' : '' }} {{ n.onPages.join(', ') }}
                </span>
              </span>
              <span class="neighbour__score">{{ percent(n.similarity) }}</span>
            </button>
          </li>
        </ol>
        <p v-if="selected" class="result__selected fr-mb-0" role="status" data-testid="selected">
          <strong>{{ selected.label }}</strong> ressemble à {{ percent(selected.similarity) }} au document envoyé.
          <RouterLink class="fr-link" :to="{ name: 'catalogue-detail', params: { id: selected.templateId } }" data-testid="open-model">Voir le modèle</RouterLink>
        </p>
        <ConsumptionSummary
          v-if="hasConsumption(search.consumption)"
          :consumption="search.consumption"
          heading="Ce que cette recherche a consommé"
          compact
          class="result__consumption"
          data-testid="search-consumption"
        />
      </section>
    </div>
  </FixedPage>
</template>

<style scoped>
.result__title {
  margin-right: auto;
}

.result {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

.result__graph {
  flex: 1;
  min-width: 0;
  min-height: 22rem;
  overflow: hidden;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
}

.result__side {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.result__list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.neighbour {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
  color: var(--text-default-grey);
  text-align: left;
  cursor: pointer;
}

.neighbour:hover {
  background: var(--background-default-grey-hover);
}

.neighbour--selected {
  border-color: var(--border-action-high-blue-france);
  background: var(--background-contrast-info);
  box-shadow: inset 0 0 0 1px var(--border-action-high-blue-france);
}

.neighbour__image {
  width: 2rem;
  height: 2.75rem;
  object-fit: cover;
  border: 1px solid var(--border-default-grey);
}

.neighbour__name {
  flex: 1;
  min-width: 0;
}

.neighbour__pages {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.neighbour__score {
  color: var(--text-action-high-blue-france);
  font-weight: 700;
}

.result__selected,
.result__consumption {
  margin-top: 0.75rem;
}

@media (min-width: 64em) {
  .result {
    flex-direction: row;
  }

  .result__side {
    flex: 0 0 24rem;
    overflow-y: auto;
  }
}
</style>
