<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DocumentViewer from '../components/DocumentViewer.vue'
import EntitiesEditor from '../components/EntitiesEditor.vue'
import TemplateLayout from '../components/TemplateLayout.vue'
import TagsInput from '../components/TagsInput.vue'
import { useWideScreen } from '../composables/useWideScreen'
import { ACCEPTED_DOCUMENT_TYPES, documentError, toDocument, useCatalogue } from '../composables/useCatalogue'
import type { TemplateDocument, TemplateEntity, Zone } from '../data/mock'

// One form, three uses: create a template, edit one you own, or suggest a change to someone else's.
const route = useRoute()
const router = useRouter()
const { find, isOwner, create, update, suggest, knownCategories } = useCatalogue()

const existing = route.name === 'catalogue-new' ? undefined : find(String(route.params.id))
const missing = route.name !== 'catalogue-new' && !existing
const mode = computed<'create' | 'edit' | 'suggest'>(() =>
  !existing ? 'create' : isOwner(existing) ? 'edit' : 'suggest',
)

const titles = { create: 'Nouveau modèle', edit: 'Modifier le modèle', suggest: 'Suggérer une modification' }
const submitLabels = { create: 'Créer le modèle', edit: 'Enregistrer', suggest: 'Envoyer la suggestion' }

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
const documentChanged = ref(false)
const documentFault = ref('')
const zonesDropped = ref(false)
// A blob: URL made here is released if the form is left without saving, and when it is replaced.
let uploadedUrl: string | null = null
let committed = false

function releaseUpload() {
  if (uploadedUrl) URL.revokeObjectURL(uploadedUrl)
  uploadedUrl = null
}

function setDocument(next: TemplateDocument | null) {
  releaseUpload()
  drawingId.value = null
  if (next) uploadedUrl = next.url
  currentDocument.value = next
  documentChanged.value = true
  // Zones are positions on a given document: they mean nothing on another one.
  zonesDropped.value = entities.value.some((e) => e.zone)
  for (const entity of entities.value) delete entity.zone
}

function onDraw(zone: Zone) {
  const entity = entities.value.find((e) => e.id === drawingId.value)
  if (entity) entity.zone = zone
  drawingId.value = null
}

function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const fault = documentError(file)
  documentFault.value = fault ?? ''
  if (fault) {
    input.value = ''
    return
  }
  setDocument(toDocument(file))
}

function removeDocument() {
  documentFault.value = ''
  setDocument(null)
}

onBeforeUnmount(() => {
  if (!committed) releaseUpload()
})

async function submit() {
  const fields = {
    name: name.value,
    description: description.value,
    categories: categories.value,
    entities: entities.value,
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

  if (mode.value === 'create') {
    const created = create(fields, currentDocument.value ?? undefined)
    if (!created) return
    committed = true
    await router.push({ name: 'catalogue-detail', params: { id: created.id } })
    return
  }
  if (mode.value === 'edit') {
    update(existing!.id, fields, documentChanged.value ? currentDocument.value : undefined)
    committed = true
  } else if (!suggest(existing!.id, fields, message.value)) {
    errors.value = { form: 'Modifiez au moins un champ pour envoyer une suggestion.' }
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
          <DsfrButton type="submit" :label="submitLabels[mode]" />
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

        <p v-if="documentFault" id="document-error" class="fr-error-text fr-mb-0" role="alert">{{ documentFault }}</p>
        <p v-if="!currentDocument && mode === 'suggest'" class="fr-hint-text fr-mb-0">Ce modèle n’a pas de document d’exemple.</p>
        <p v-if="currentDocument && mode === 'suggest'" class="fr-hint-text fr-mb-0">Seul le propriétaire peut changer le document d’exemple.</p>

        <DsfrAlert
          v-if="zonesDropped"
          type="warning"
          small
          description="Les zones dessinées ont été retirées : elles se rapportaient à l’ancien document."
        />

        <div v-if="currentDocument" class="template-form__viewer">
          <DocumentViewer
            :document="currentDocument"
            :entities="entities"
            :highlight-id="drawingId ?? currentEntityId ?? undefined"
            :drawing="drawingId !== null"
            :fit="wide"
            @draw="onDraw"
            @cancel="drawingId = null"
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
