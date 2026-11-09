<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import FixedPage from '../components/FixedPage.vue'
import SearchHistory from '../components/SearchHistory.vue'
import SearchScope from '../components/SearchScope.vue'
import { ACCEPTED_DOCUMENT_TYPES } from '../composables/useCatalogue'
import { useSearches } from '../composables/useSearches'
import { DEFAULT_NEIGHBOURS, MAX_NEIGHBOURS, MIN_NEIGHBOURS } from '../data/search'

// Send a document: the pages of the models that look the most like each of its pages are looked for by a worker, and the
// search is kept to be opened again. What it consumed is told with its result.
const router = useRouter()
const { searches, loaded, failed, load, start, remove, reason } = useSearches()

const MAX_BYTES = 20 * 1024 * 1024
const k = ref(DEFAULT_NEIGHBOURS)
// Null: every model the person can see.
const scope = ref<string[] | null>(null)
const dragging = ref(false)
const sending = ref(false)
const fault = ref('')
const removeFault = ref('')

onMounted(load)

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
  if (scope.value !== null && !scope.value.length) {
    fault.value = 'Choisissez au moins un modèle, ou cherchez dans tous.'
    return
  }
  sending.value = true
  try {
    const search = await start(candidate, k.value, scope.value)
    await router.push({ name: 'search-detail', params: { id: search.id } })
  } catch (error) {
    fault.value = reason(error)
  } finally {
    sending.value = false
  }
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

const setK = (event: Event) => {
  const value = Math.round(Number((event.target as HTMLInputElement).value))
  k.value = Number.isFinite(value) ? Math.max(MIN_NEIGHBOURS, Math.min(MAX_NEIGHBOURS, value)) : DEFAULT_NEIGHBOURS
}

async function onRemove(id: string) {
  removeFault.value = await remove(id)
}
</script>

<template>
  <FixedPage>
    <template #header>
      <div class="search__title">
        <h1 class="fr-h3 fr-mb-0">Recherche</h1>
        <p class="fr-mb-0">Envoyez un document : les modèles qui lui ressemblent le plus s’affichent autour de lui.</p>
      </div>
    </template>

    <div class="search__layout">
      <div class="search__new">
        <div class="search__settings">
          <div class="fr-input-group search__k">
            <label class="fr-label" for="search-k">Voisins par page</label>
            <input id="search-k" class="fr-input" type="number" inputmode="numeric" :min="MIN_NEIGHBOURS" :max="MAX_NEIGHBOURS" :value="k" data-testid="k" @change="setK" />
          </div>
          <SearchScope v-model="scope" />
        </div>

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
        <p v-if="sending" class="fr-hint-text fr-mb-0" role="status" data-testid="sending">Envoi du document…</p>
        <p v-if="fault" class="fr-error-text fr-mb-0" role="alert" data-testid="fault">{{ fault }}</p>
      </div>

      <section class="search__past" aria-labelledby="past-title">
        <h2 id="past-title" class="fr-h6 fr-mb-1w">Mes recherches</h2>
        <p v-if="failed" class="fr-error-text" role="alert" data-testid="history-failed">Vos recherches n’ont pas pu être chargées.</p>
        <p v-else-if="!loaded" role="status" class="fr-hint-text">Chargement…</p>
        <p v-else-if="!searches.length" class="fr-hint-text" data-testid="history-empty">Vous n’avez pas encore fait de recherche.</p>
        <SearchHistory v-else :searches="searches" @remove="onRemove" />
        <p v-if="removeFault" class="fr-error-text" role="alert" data-testid="remove-fault">{{ removeFault }}</p>
      </section>
    </div>
  </FixedPage>
</template>

<style scoped>
.search__title {
  margin-right: auto;
}

.search__layout {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1.5rem;
  min-height: 0;
}

.search__new {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.75rem;
}

.search__settings {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 2rem;
}

.search__k {
  margin: 0;
}

.search__k .fr-input {
  width: 6rem;
}

.search__past {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}

.dropzone {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 10rem;
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

@media (min-width: 64em) {
  .search__layout {
    flex-direction: row;
  }

  .search__new {
    flex: 1 1 0;
  }

  .search__past {
    flex: 0 0 26rem;
  }
}
</style>
