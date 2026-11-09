<script setup lang="ts">
import { computed, ref } from 'vue'
import FixedPage from '../components/FixedPage.vue'
import NeighbourGraph from '../components/NeighbourGraph.vue'
import { useSimilarSearch } from '../composables/useSimilarSearch'
import { ACCEPTED_DOCUMENT_TYPES } from '../composables/useCatalogue'
import { MAX_NEIGHBOURS, MIN_NEIGHBOURS } from '../data/similar'

// Send a document, see the ones that look the most like it: the k nearest neighbours, drawn as a graph.
const { file, k, found, loading, error, previewUrl, search, setK, reset } = useSimilarSearch()

const MAX_BYTES = 20 * 1024 * 1024
const dragging = ref(false)
const fault = ref('')
const selectedId = ref<string | null>(null)

const selected = computed(() => found.value?.neighbours.find((n) => n.id === selectedId.value) ?? null)
const percent = (similarity: number) => `${Math.round(similarity * 100)} %`

async function take(candidate: File | undefined) {
  fault.value = ''
  if (!candidate) return
  if (!ACCEPTED_DOCUMENT_TYPES.includes(candidate.type)) {
    fault.value = 'Seuls les images (PNG, JPEG, WebP, GIF) et les PDF sont acceptés.'
    return
  }
  if (candidate.size > MAX_BYTES) {
    fault.value = 'Ce fichier est trop lourd (20 Mo au maximum).'
    return
  }
  selectedId.value = null
  await search(candidate)
}

function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const [chosen] = Array.from(input.files ?? [])
  input.value = '' // so that the same file can be chosen again
  return take(chosen)
}

function onDrop(event: DragEvent) {
  dragging.value = false
  return take(event.dataTransfer?.files?.[0])
}

function again() {
  selectedId.value = null
  fault.value = ''
  reset()
}

const onCount = (event: Event) => setK(Number((event.target as HTMLInputElement).value))
</script>

<template>
  <FixedPage :from="64">
    <template #header>
      <div class="search__title">
        <h1 class="fr-h3 fr-mb-0">Recherche</h1>
        <p class="fr-mb-0">Envoyez un document : les documents qui lui ressemblent le plus s’affichent autour de lui.</p>
      </div>
      <div class="fr-input-group search__k">
        <label class="fr-label" for="search-k">Voisins affichés</label>
        <input
          id="search-k"
          class="fr-input"
          type="number"
          inputmode="numeric"
          :min="MIN_NEIGHBOURS"
          :max="MAX_NEIGHBOURS"
          :value="k"
          data-testid="k"
          @change="onCount"
        />
      </div>
      <button v-if="file" type="button" class="fr-btn fr-btn--secondary" data-testid="again" @click="again">Nouvelle recherche</button>
    </template>

    <input
      id="search-file"
      class="fr-sr-only search__input"
      type="file"
      aria-label="Document à rechercher"
      :accept="ACCEPTED_DOCUMENT_TYPES.join(',')"
      data-testid="file"
      @change="onFile"
    />
    <label
      v-if="!file"
      class="dropzone"
      :class="{ 'dropzone--over': dragging }"
      for="search-file"
      data-testid="dropzone"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onDrop"
    >
      <span class="dropzone__title">Déposez un document ici</span>
      <span class="dropzone__hint">ou cliquez pour en choisir un · image ou PDF, 20 Mo au plus</span>
    </label>
    <p v-if="fault" class="fr-error-text fr-mb-0" role="alert" data-testid="fault">{{ fault }}</p>
    <p v-if="loading" class="fr-hint-text fr-mb-0" role="status" data-testid="loading">Recherche des documents proches…</p>
    <p v-if="error" class="fr-error-text fr-mb-0" role="alert" data-testid="error">{{ error }}</p>

    <div v-if="file && found" class="search__result">
      <section class="search__graph" aria-label="Graphe des voisins">
        <NeighbourGraph
          :query="{ name: file.name, imageUrl: previewUrl }"
          :neighbours="found.neighbours"
          :links="found.links"
          :selected-id="selectedId"
          @select="selectedId = $event"
        />
      </section>

      <section class="search__side" aria-label="Documents proches">
        <h2 class="fr-h6 fr-mb-1w">{{ found.neighbours.length }} documents proches de « {{ file.name }} »</h2>
        <ol class="search__list" data-testid="neighbours">
          <li v-for="n in found.neighbours" :key="n.id">
            <button
              type="button"
              class="neighbour"
              :class="{ 'neighbour--selected': n.id === selectedId }"
              :aria-pressed="n.id === selectedId"
              :data-testid="`neighbour-${n.id}`"
              @click="selectedId = n.id === selectedId ? null : n.id"
            >
              <img class="neighbour__image" :src="n.imageUrl" alt="" />
              <span class="neighbour__name">{{ n.name }}</span>
              <span class="neighbour__score">{{ percent(n.similarity) }}</span>
            </button>
          </li>
        </ol>
        <p v-if="selected" class="search__selected fr-mb-0" role="status" data-testid="selected">
          <strong>{{ selected.name }}</strong> ressemble à {{ percent(selected.similarity) }} au document envoyé.
        </p>
      </section>
    </div>
  </FixedPage>
</template>

<style scoped>
.search__title {
  margin-right: auto;
}

.search__k {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
}

.search__k .fr-input {
  width: 5rem;
  margin: 0;
}

.dropzone {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 14rem;
  padding: 1.5rem;
  border: 2px dashed var(--border-action-high-blue-france);
  background: var(--background-contrast-info);
  color: var(--text-action-high-blue-france);
  text-align: center;
  cursor: pointer;
}

.dropzone--over,
.dropzone:hover {
  background: var(--background-contrast-info-hover);
}

.search__input:focus-visible ~ .dropzone {
  outline: 2px solid #0a76f6;
  outline-offset: 2px;
}

.dropzone__title {
  font-size: 1.25rem;
  font-weight: 700;
}

.dropzone__hint {
  color: var(--text-default-grey);
  font-size: 0.875rem;
}

.search__result {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

.search__graph {
  flex: 1;
  min-height: 22rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
}

.search__side {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.search__list {
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.neighbour__score {
  color: var(--text-action-high-blue-france);
  font-weight: 700;
}

.search__selected {
  margin-top: 0.75rem;
}

@media (min-width: 64em) {
  .search__result {
    flex-direction: row;
  }

  .search__side {
    flex: 0 0 22rem;
  }
}
</style>
