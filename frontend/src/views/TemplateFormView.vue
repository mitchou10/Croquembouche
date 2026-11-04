<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DocumentViewer from '../components/DocumentViewer.vue'
import EntitiesEditor from '../components/EntitiesEditor.vue'
import TemplateLayout from '../components/TemplateLayout.vue'
import TagsInput from '../components/TagsInput.vue'
import { useWideScreen } from '../composables/useWideScreen'
import { ACCEPTED_DOCUMENT_TYPES, documentError, newEntity, useCatalogue } from '../composables/useCatalogue'
import { ApiError, deleteDocument, fetchSuggestions, uploadDocument, type SuggestedEntity } from '../data/api'
import type { PageFields, TemplateDocument, TemplateEntity, Zone } from '../data/mock'

// One form, three uses: create a template, edit one you own, or suggest a change to someone else's.
const route = useRoute()
const router = useRouter()
const { find, isOwner, create, update, suggest, knownCategories } = useCatalogue()

// A new model can be a sub-model of another: « Ajouter un sous-modèle » on the page of a model brings its id here.
const parent = route.name === 'catalogue-new' && typeof route.query.parent === 'string' ? find(route.query.parent) : undefined

const existing = route.name === 'catalogue-new' ? undefined : find(String(route.params.id))
const missing = route.name !== 'catalogue-new' && !existing
const mode = computed<'create' | 'edit' | 'suggest'>(() =>
  !existing ? 'create' : isOwner(existing) ? 'edit' : 'suggest',
)

const titles = { create: parent ? 'Nouveau sous-modèle' : 'Nouveau modèle', edit: 'Modifier le modèle', suggest: 'Suggérer une modification' }
const submitLabels = { create: parent ? 'Créer le sous-modèle' : 'Créer le modèle', edit: 'Enregistrer', suggest: 'Envoyer la suggestion' }

const name = ref(existing?.name ?? '')
const description = ref(existing?.description ?? '')
const categories = ref<string[]>([...(existing?.categories ?? [])])
const message = ref('')
// A copy: the entities are edited in place and must not touch the catalogue until the form is submitted.
const entities = ref<TemplateEntity[]>(JSON.parse(JSON.stringify(existing?.entities ?? [])))
const errors = ref<{ name?: string; description?: string; form?: string }>({})
// What is missing, in one line: the messages under each field are kept for screen readers but take no room on screen.
const toComplete = ref<string[]>([])
const entitiesEditor = ref<InstanceType<typeof EntitiesEditor>>()
const drawingId = ref<string | null>(null)
const currentEntityId = ref<string | null>(null)
const fileInput = ref<HTMLInputElement>()

// On a wide screen the page is fixed to the window and the document is fitted whole into its half.
const wide = useWideScreen()

// The model's document is optional. Only its owner (or its creator) changes it: a suggestion keeps the current one.
const currentDocument = ref<TemplateDocument | null>(existing?.document ?? null)

// What is said of the pages of the document: a name and a description, for the ones that have them.
const pages = ref<PageFields[]>((existing?.pages ?? []).map(({ page, name, description }) => ({ page, name, description })))
const shownPage = ref(1)
const pageCount = computed(() => currentDocument.value?.pages ?? 1)
// Without a name a page is the model's name and its number: shown as the hint.
const pageHint = computed(() => `${name.value.trim() || 'Nom du modèle'} · page ${shownPage.value}`)

function editPage(change: Partial<PageFields>) {
  const current = pages.value.find((p) => p.page === shownPage.value)
  if (current) Object.assign(current, change)
  else pages.value = [...pages.value, { page: shownPage.value, name: '', description: '', ...change }]
}

/** The fields of the page shown: a page is made when something is typed in them. */
const pageName = computed({
  get: () => pages.value.find((p) => p.page === shownPage.value)?.name ?? '',
  set: (value: string) => editPage({ name: value }),
})
const pageDescription = computed({
  get: () => pages.value.find((p) => p.page === shownPage.value)?.description ?? '',
  set: (value: string) => editPage({ description: value }),
})
const documentChanged = ref(false)
const documentFault = ref('')
const zonesDropped = ref(false)
const uploading = ref(false)
// The documents uploaded in this form: one that is replaced, taken off, or never saved is deleted again.
const uploadedIds = new Set<string>()
let committed = false

function discard(document: TemplateDocument | null) {
  if (!document?.id || !uploadedIds.delete(document.id)) return
  deleteDocument(document.id).catch(() => {
    // Left behind, harmlessly: nothing points to it.
  })
}

function setDocument(next: TemplateDocument | null) {
  discard(currentDocument.value)
  drawingId.value = null
  if (next?.id) uploadedIds.add(next.id)
  currentDocument.value = next
  suggestions.value = []
  // What was said of the pages of another document means nothing for this one.
  pages.value = []
  shownPage.value = 1
  documentChanged.value = true
  // Zones are positions on a given document: they mean nothing on another one.
  zonesDropped.value = entities.value.some((e) => e.zone)
  for (const entity of entities.value) delete entity.zone
}

// What a PDF suggests by itself (its form fields, boxes and blanks): offered once, to be taken or left.
const suggestions = ref<SuggestedEntity[]>([])

async function suggestFrom(document: TemplateDocument) {
  suggestions.value = []
  if (!document.id || document.type !== 'application/pdf') return
  try {
    const found = await fetchSuggestions(document.id)
    // Only if it is still the document of the form: another may have been chosen while this one was read.
    if (currentDocument.value?.id === document.id) suggestions.value = found
  } catch {
    // Nothing is suggested: the entities are filled in by hand, as ever.
  }
}

/** Adds the suggested entities after the ones already there, each found by its zone; the definition is theirs to improve. */
function addSuggestions() {
  entities.value = [
    ...entities.value,
    ...suggestions.value.map((s) => ({
      ...newEntity(),
      name: s.name,
      definition: `Le champ « ${s.name} » du document.`,
      type: s.type,
      zone: s.zone,
    })),
  ]
  suggestions.value = []
}

function onUpdateZone(id: string, zone: Zone) {
  const entity = entities.value.find((e) => e.id === id)
  if (entity) entity.zone = zone
}

function onRemoveZone(id: string) {
  const entity = entities.value.find((e) => e.id === id)
  if (entity) delete entity.zone
}

function onDraw(zone: Zone) {
  const entity = entities.value.find((e) => e.id === drawingId.value)
  if (entity) entity.zone = zone
  drawingId.value = null
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const fault = documentError(file)
  documentFault.value = fault ?? ''
  if (fault) {
    input.value = ''
    return
  }
  uploading.value = true
  try {
    const uploaded = await uploadDocument(file)
    setDocument(uploaded)
    void suggestFrom(uploaded)
  } catch (error) {
    documentFault.value = error instanceof ApiError ? error.message : 'Le document n’a pas pu être envoyé.'
    input.value = ''
  } finally {
    uploading.value = false
  }
}

function removeDocument() {
  documentFault.value = ''
  setDocument(null)
}

onBeforeUnmount(() => {
  if (!committed) discard(currentDocument.value)
})

async function submit() {
  const fields = {
    name: name.value,
    description: description.value,
    categories: categories.value,
    entities: entities.value,
    pages: pages.value,
  }
  toComplete.value = []
  errors.value = {
    name: fields.name.trim() ? undefined : 'Donnez un nom au modèle.',
    description: fields.description.trim() ? undefined : 'Ajoutez une description.',
  }
  // Both are checked, so every missing field is flagged at once.
  const entitiesValid = entitiesEditor.value?.validate() ?? true
  const incomplete = entitiesEditor.value?.incomplete ?? []
  toComplete.value = [
    ...(errors.value.name ? ['le nom'] : []),
    ...(errors.value.description ? ['la description'] : []),
    ...(incomplete.length ? [`${incomplete.length > 1 ? 'les entités' : 'l’entité'} ${incomplete.join(', ')}`] : []),
  ]
  if (errors.value.name || errors.value.description || !entitiesValid) return

  try {
    if (mode.value === 'create') {
      const created = await create(fields, currentDocument.value ?? undefined, parent?.id)
      committed = true
      await router.push({ name: 'catalogue-detail', params: { id: created.id } })
      return
    }
    if (mode.value === 'edit') {
      await update(existing!.id, fields, documentChanged.value ? currentDocument.value : undefined)
      committed = true
    } else {
      await suggest(existing!.id, fields, message.value)
    }
  } catch (error) {
    // What the backend refuses, with its reason: who may do this, what is not valid.
    errors.value = { form: error instanceof ApiError ? error.message : 'Le serveur est injoignable.' }
    return
  }
  await router.push({
    name: 'catalogue-detail',
    params: { id: existing!.id },
    // A suggestion is sent to be seen: the page opens on the suggestions.
    query: mode.value === 'suggest' ? { onglet: 'suggestions' } : {},
  })
}
</script>

<template>
  <p v-if="missing" role="status">
    Ce modèle n’existe pas. <RouterLink :to="{ name: 'catalogue' }">Retour au catalogue</RouterLink>
  </p>

  <form v-else class="template-form" novalidate @submit.prevent="submit">
    <TemplateLayout>
      <template #header>
        <h1 class="template-form__title fr-h5 fr-mb-0">{{ titles[mode] }}</h1>
        <p v-if="parent" class="fr-mb-0" data-testid="parent-model">Sous-modèle de <strong>{{ parent.name }}</strong></p>
        <!-- What is wrong, on the title's line: it takes no height of its own. -->
        <p v-if="errors.form" class="template-form__alert fr-error-text fr-mb-0" role="alert">{{ errors.form }}</p>
        <p v-if="toComplete.length" class="template-form__alert fr-error-text fr-mb-0" role="alert" data-testid="missing">
          À compléter : {{ toComplete.join(', ') }}.
        </p>
        <div class="template-form__actions">
          <RouterLink
            class="fr-btn fr-btn--secondary"
            :to="existing ? { name: 'catalogue-detail', params: { id: existing.id } } : { name: 'catalogue' }"
          >
            Annuler
          </RouterLink>
          <DsfrButton type="submit" :label="submitLabels[mode]" :disabled="uploading" />
        </div>
      </template>

      <template #document>
        <template v-if="mode === 'suggest'">
          <p class="fr-hint-text fr-mb-0">
            Vous n’êtes pas propriétaire de ce modèle : votre proposition sera appliquée si son propriétaire l’accepte.
          </p>
          <DsfrInput v-model="message" label="Message pour le propriétaire (facultatif)" label-visible />
        </template>
        <div class="template-form__doc-head">
          <h2 id="document-title" class="fr-h6 fr-mb-0">Document d’exemple</h2>
          <p v-if="currentDocument" class="template-form__doc-name" data-testid="document-name">{{ currentDocument.name }}</p>

          <div v-if="mode !== 'suggest'" class="template-form__doc-actions">
            <!-- Always in the page (a test, or a script, sets a file on it); out of sight once there is a document. -->
            <div class="fr-upload-group" :class="{ 'fr-upload-group--error': documentFault, 'fr-sr-only': currentDocument }">
              <label class="fr-label" for="document">
                Ajouter un document (facultatif)
                <span class="fr-hint-text">Image (PNG, JPEG, WebP, GIF) ou PDF, 20 Mo maximum.</span>
              </label>
              <input
                id="document"
                ref="fileInput"
                class="fr-upload"
                type="file"
                :accept="ACCEPTED_DOCUMENT_TYPES.join(',')"
                :aria-describedby="documentFault ? 'document-error' : undefined"
                @change="onFile"
              />
            </div>
            <template v-if="currentDocument">
              <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" @click="fileInput?.click()">Remplacer</button>
              <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" title="Retirer le document" @click="removeDocument">
                Retirer<span class="fr-sr-only"> le document</span>
              </button>
            </template>
          </div>
        </div>

        <p v-if="uploading" class="fr-hint-text fr-mb-0" role="status">Envoi du document…</p>
        <p v-if="documentFault" id="document-error" class="fr-error-text fr-mb-0" role="alert">{{ documentFault }}</p>
        <p v-if="!currentDocument && mode === 'suggest'" class="fr-hint-text fr-mb-0">Ce modèle n’a pas de document d’exemple.</p>
        <p v-if="currentDocument && mode === 'suggest'" class="fr-hint-text fr-mb-0">Seul le propriétaire peut changer le document d’exemple.</p>

        <DsfrAlert
          v-if="zonesDropped"
          type="warning"
          small
          description="Les zones dessinées ont été retirées : elles se rapportaient à l’ancien document."
        />

        <div v-if="currentDocument && pageCount > 1" class="template-form__page" data-testid="page-fields">
          <div><DsfrInput v-model="pageName" :label="`Nom de la page ${shownPage}`" label-visible :placeholder="pageHint" /></div>
          <div><DsfrInput v-model="pageDescription" :label="`Description de la page ${shownPage}`" label-visible /></div>
        </div>

        <div v-if="currentDocument" class="template-form__viewer">
          <DocumentViewer
            v-model:page="shownPage"
            :document="currentDocument"
            :entities="entities"
            :highlight-id="drawingId ?? currentEntityId ?? undefined"
            :drawing="drawingId !== null"
            editable
            :fit="wide"
            @draw="onDraw"
            @cancel="drawingId = null"
            @update="onUpdateZone"
            @remove="onRemoveZone"
          />
        </div>
        <p v-else-if="mode !== 'suggest'" class="template-form__empty">Aucun document : le modèle se définira par ses entités seulement.</p>
      </template>

      <div class="template-form__body">
        <div class="template-form__row">
          <DsfrInputGroup v-model="name" label="Nom" :label-visible="true" :error-message="errors.name" :is-invalid="!!errors.name" />
          <TagsInput v-model="categories" class="categories" label="Catégories" placeholder="Choisir ou saisir…" ignore-case :suggestions="knownCategories" />
        </div>
        <DsfrInputGroup
          v-model="description"
          label="Description"
          :label-visible="true"
          is-textarea
          :rows="2"
          :error-message="errors.description"
          :is-invalid="!!errors.description"
        />

        <p v-if="suggestions.length" class="template-form__suggest fr-mb-0" role="status" data-testid="suggestions">
          <span>{{ suggestions.length }} entité{{ suggestions.length > 1 ? 's' : '' }} détectée{{ suggestions.length > 1 ? 's' : '' }} dans ce PDF.</span>
          <button type="button" class="fr-btn fr-btn--sm" data-testid="suggestions-add" @click="addSuggestions">Les ajouter</button>
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" data-testid="suggestions-ignore" @click="suggestions = []">Ignorer</button>
        </p>

        <EntitiesEditor
          :key="currentDocument?.url ?? 'no-document'"
          ref="entitiesEditor"
          v-model="entities"
          v-model:drawing-id="drawingId"
          v-model:current-id="currentEntityId"
          :document="currentDocument"
        />
      </div>
    </TemplateLayout>
  </form>
</template>

<style scoped>
/* The form only groups the fields for submission: the layout is the page's. */
.template-form {
  display: contents;
}

.template-form__title {
  margin-right: auto;
}

.template-form__alert {
  flex: 1 1 12rem;
  min-width: 0;
}

.template-form__actions {
  display: flex;
  gap: 0.5rem;
}

.template-form__suggest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: var(--background-contrast-info);
  font-size: 0.875rem;
}

.template-form__page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.5rem;
}

.template-form__body {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.template-form__doc-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.template-form__doc-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.template-form__doc-name {
  flex: 1;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-size: 0.875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-form__empty {
  margin: 0;
  padding: 2rem 1rem;
  border: 1px dashed var(--border-default-grey);
  color: var(--text-mention-grey);
  text-align: center;
}

/* The name and the categories share a line. */
.template-form__row {
  display: grid;
  gap: 1rem;
}

/* Each error message sits under its field and would push the form down by a line apiece: they stay in the page, for
   screen readers and for what the fields point to, but only the summary above the form shows. */
.template-form__body :deep(.fr-messages-group) {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (min-width: 40em) {
  .template-form__row {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

@media (min-width: 64em) {
  /* The document takes what is left of its half, under its heading. */
  .template-form__viewer {
    flex: 1;
    min-height: 0;
  }
}
</style>
