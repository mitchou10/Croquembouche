<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConfirmButton from '../components/ConfirmButton.vue'
import DetectionCard from '../components/DetectionCard.vue'
import DocumentViewer from '../components/DocumentViewer.vue'
import FixedPage from '../components/FixedPage.vue'
import PagerControls from '../components/PagerControls.vue'
import ManualElementCard from '../components/ManualElementCard.vue'
import ReviewControls from '../components/ReviewControls.vue'
import RunsList from '../components/RunsList.vue'
import StatTile from '../components/StatTile.vue'
import TabList from '../components/TabList.vue'
import { describeShares } from '../composables/shares'
import { loadAnalyses, statsOf, useAnalyses } from '../composables/useAnalyses'
import { ACCEPTED_DOCUMENT_TYPES, documentError, useCatalogue } from '../composables/useCatalogue'
import { useSession } from '../composables/useSession'
import { useWideScreen } from '../composables/useWideScreen'
import { statusLabels, type AnalysisRun, type Review, type TemplateEntity, type Zone } from '../data/mock'

// The page of an analysis, for whoever can open it. What one comes to do is try it: a document is dropped, which is a use
// of the analysis, and what it finds is shown on the document itself, element by element, with what each could be and how
// sure it is. Each prediction can then be confirmed, rejected, or corrected with one of the models of the analysis, and the
// document kept or deleted. What a use found is private to the person who ran it, an administrator included.
const route = useRoute()
const router = useRouter()
const {
  find,
  findRun,
  canAccess,
  registerView,
  modelNames,
  canSeeResult,
  startRun,
  follow,
  reviewDetection,
  cancelRun,
  ownsRun,
  reviewPage,
  addElement,
  removeElement,
  reviewProgress,
  deleteScreenshot,
  keepScreenshot,
  actionError,
  remove: removeAnalysis,
  searchedIds,
} = useAnalyses()
const { userId } = useSession()
const { find: findTemplate, pageLabel } = useCatalogue()
const wide = useWideScreen()

const analysis = computed(() => find(String(route.params.id)))
const allowed = computed(() => !!analysis.value && canAccess(analysis.value))
const stats = computed(() => statsOf(analysis.value ? [analysis.value] : []))
// Only its owner deletes it.
const isOwner = computed(() => !!analysis.value && userId.value !== null && analysis.value.ownerId === userId.value)

async function deleteAnalysis() {
  if (analysis.value && (await removeAnalysis(analysis.value.id))) await router.push({ name: 'analyses' })
}

// ---------------------------------------------------------------- the use being looked at
const selectedRunId = ref<string | null>(null)
const current = ref(0)
const tab = ref<'page' | 'elements' | 'runs'>('page')
// Adding an element by hand: which model it is, and whether the zone is being drawn.
const adding = ref(false)
const newModel = ref('')
// The entity of that model it is, when the person knows: what the recall of each entity is measured on.
const newEntity = ref('')
// Whether to keep a capture of the document tried: yes unless said otherwise.
const saveScreenshot = ref(true)
const fault = ref('')
const dragging = ref(false)
// The page of the document looked at: the viewer and the classification of the page follow each other.
const viewerPage = ref(1)
// While the document is sent and tried.
const uploading = ref(false)

/** The use shown, if it is one whose result the person can see: never someone else's. */
const run = computed(() => {
  const found = analysis.value && selectedRunId.value ? findRun(analysis.value.id, selectedRunId.value) : undefined
  return found && canSeeResult(found) ? found : undefined
})
const detections = computed(() => run.value?.detections ?? [])
// What the analysis makes of the page being looked at, and how many pages the document has.
const pageCount = computed(() => run.value?.pages?.length ?? 0)
const pageResult = computed(() => run.value?.pages?.find((p) => p.page === viewerPage.value))
const pageIndex = computed({
  get: () => viewerPage.value - 1,
  set: (index: number) => (viewerPage.value = index + 1),
})
const shown = computed(() => detections.value[current.value])
const progress = computed(() => (run.value ? reviewProgress(run.value) : { total: 0, reviewed: 0 }))
const allReviewed = computed(() => progress.value.total > 0 && progress.value.reviewed === progress.value.total)
// Once everything is looked at, the person is asked what to do with the document: unless they said already, or none was kept.
const askAboutFile = computed(() => allReviewed.value && !!run.value?.screenshot && !run.value.fileDecision)

// Only its person stops a use, and only while it runs.
const canCancel = (r: AnalysisRun) => r.status === 'running' && ownsRun(r)
const cancel = (runId: string) => analysis.value && cancelRun(analysis.value.id, runId)

// The cards at the top filter the uses: a click on one lists those uses, and on the same one again, or on « Utilisations »,
// lists them all.
type RunFilter = 'done' | 'running' | 'failed'
const statusFilter = ref<RunFilter | null>(null)
const shownRuns = computed(() => (analysis.value?.runs ?? []).filter((r) => !statusFilter.value || r.status === statusFilter.value))
function filterRuns(status: RunFilter | null) {
  statusFilter.value = status === statusFilter.value ? null : status
  tab.value = 'runs'
}
watch(() => route.params.id, () => (statusFilter.value = null))

// A zone clicked on the document is the element on show, in its tab.
function selectElement(id: string) {
  const index = detections.value.findIndex((d) => d.id === id)
  if (index < 0 || adding.value) return
  current.value = index
  tab.value = 'elements'
}

function open(runId: string) {
  selectedRunId.value = runId
  // A use that is still running is asked for until the worker has answered.
  if (analysis.value && findRun(analysis.value.id, runId)?.status === 'running') follow(analysis.value.id, runId)
  viewerPage.value = 1
  current.value = 0
  adding.value = false
  tab.value = 'page'
}

/** Takes the document, and tries the analysis on it at once: nothing more to press. */
async function setFile(file: File | null) {
  fault.value = file ? (documentError(file) ?? '') : ''
  if (!file || fault.value || !analysis.value) return
  uploading.value = true
  const started = await startRun(analysis.value.id, file, { saveScreenshot: saveScreenshot.value })
  uploading.value = false
  if (started) open(started.id)
}

function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  setFile(input.files?.[0] ?? null)
  input.value = '' // so that the same document can be chosen again
}

function onDrop(event: DragEvent) {
  dragging.value = false
  const dropped = event.dataTransfer?.files?.[0]
  if (dropped) setFile(dropped)
}

function newTest() {
  selectedRunId.value = null
  fault.value = ''
  adding.value = false
  tab.value = 'page'
}

function review(detectionId: string, decision: Review) {
  if (analysis.value && run.value) reviewDetection(analysis.value.id, run.value.id, detectionId, decision)
}

function reviewPageDecision(decision: Review) {
  if (analysis.value && run.value) reviewPage(analysis.value.id, run.value.id, viewerPage.value, decision)
}

const entitiesOfNewModel = computed(() => findTemplate(newModel.value)?.entities ?? [])
watch(newModel, () => (newEntity.value = ''))

// A zone drawn on the document becomes an element, annotated with the model chosen.
function startAdding() {
  newModel.value = newModel.value || models.value[0]?.id || ''
  newEntity.value = ''
  adding.value = true
}

async function onDraw(zone: Zone) {
  if (!analysis.value || !run.value || !adding.value) return
  adding.value = false
  if (await addElement(analysis.value.id, run.value.id, { zone, templateId: newModel.value, ...(newEntity.value && { entityId: newEntity.value }) })) current.value = detections.value.length - 1
}

async function remove(elementId: string) {
  if (!analysis.value || !run.value || !(await removeElement(analysis.value.id, run.value.id, elementId))) return
  current.value = Math.max(0, Math.min(current.value, detections.value.length - 1))
}

const removeFile = () => analysis.value && run.value && deleteScreenshot(analysis.value.id, run.value.id)
const keepFile = () => analysis.value && run.value && keepScreenshot(analysis.value.id, run.value.id)

// ---------------------------------------------------------------- opening the page
// The analyses are loaded first: otherwise the page would say, for a moment, that this one does not exist.
const ready = ref(false)
async function load(id: string) {
  selectedRunId.value = null
  fault.value = ''
  adding.value = false
  tab.value = 'page'
  await loadAnalyses()
  ready.value = true
  const opened = find(id)
  if (opened?.canOpen) await registerView(id)
}
watch(() => String(route.params.id), load, { immediate: true })

// ---------------------------------------------------------------- what is shown
const NO_MODEL = 'Autre, non reconnu'
/** What a class is called: a model, a page of a model (« Formulaire X · page 3 »), or « other ». */
const nameOf = (templateId: string | null, templatePage?: number | null) =>
  templateId === null ? NO_MODEL : pageLabel(templateId, templatePage)
// The models the analysis looks for: its own and their sub-models.
const searched = computed(() => (analysis.value ? searchedIds(analysis.value) : []))
const models = computed(() => searched.value.map((id) => ({ id, name: nameOf(id) })))
// What a page of the document can be annotated with: the pages of the models that have several, else the model.
const pageModels = computed(() =>
  searched.value.flatMap((id) => {
    const pages = findTemplate(id)?.pages ?? []
    return pages.length > 1 ? pages.map((p) => ({ id, name: p.label, page: p.page })) : [{ id, name: nameOf(id) }]
  }),
)
const percent = (confidence: number) => Math.round(confidence * 100)

// The entity an element is, when known: looked for in the models of the analysis and their sub-models.
const entityOf = (d: NonNullable<typeof shown.value>) =>
  d.entityId ? searched.value.flatMap((id) => findTemplate(id)?.entities ?? []).find((e) => e.id === d.entityId) : undefined
const entityName = (d: NonNullable<typeof shown.value>) => entityOf(d)?.name

// What is said on the document of each element: what it is called (its entity, else its number) and what has been decided
// of it. The model it matches is not written there, the card beside says it.
const labelOf = (d: NonNullable<typeof shown.value>, index: number) => {
  const name = entityName(d) ?? `Élément ${index + 1}`
  if (d.source === 'manual') return `✎ ${name}`
  switch (d.review.status) {
    case 'validated':
      return `✓ ${name}`
    case 'invalidated':
      return `✗ ${name} (invalidée)`
    case 'annotated':
      return `✎ ${name}`
    default:
      return `${name} · ${percent(d.classifications[0].confidence)} %`
  }
}
// The viewer outlines the zones of « entities »: each element found is one.
const outlined = computed<TemplateEntity[]>(() =>
  detections.value.map((d, index) => ({ id: d.id, name: labelOf(d, index), definition: '', type: 'text', examples: [], tags: [], stars: [], zone: d.zone })),
)

const foundModels = computed(() => new Set(detections.value.map((d) => d.classifications[0].templateId).filter((t) => t !== null)).size)
// With a use shown, its page and its elements have a tab each; before, one tab says how it works.
const tabs = computed(() => [
  ...(run.value
    ? [
        { id: 'page', label: 'Page' },
        { id: 'elements', label: `Éléments (${detections.value.length})` },
      ]
    : [{ id: 'page', label: 'Résultat' }]),
  { id: 'runs', label: `Utilisations (${analysis.value?.runs.length ?? 0})` },
])
// Drawing needs the document: its capture, which a PDF or a deleted file does not have.
const canDraw = computed(() => !!run.value?.screenshot)

const sharing = computed(() => {
  const a = analysis.value
  if (!a) return null
  if (a.isPublic) return { label: 'Publique', title: 'Visible par tous les utilisateurs' }
  if (a.shares.length) return { label: `Partagée · ${a.shares.length}`, title: `Partagée avec ${describeShares(a.shares)}` }
  return { label: 'Privée', title: 'Visible par son propriétaire seulement' }
})
</script>

<template>
  <p v-if="ready && !analysis" role="status">
    Cette analyse n’existe pas. <RouterLink :to="{ name: 'analyses' }">Retour aux analyses</RouterLink>
  </p>
  <p v-else-if="ready && !allowed" role="status" data-testid="no-access">
    Vous n’avez pas accès à cette analyse. <RouterLink :to="{ name: 'analyses' }">Retour aux analyses</RouterLink>
  </p>

  <FixedPage v-else-if="ready && analysis" :from="64">
    <template #header>
      <RouterLink class="fr-link fr-link--sm fr-icon-arrow-left-line fr-link--icon-left" :to="{ name: 'analyses' }">Analyses</RouterLink>
      <h1 class="dashboard__title fr-h4 fr-mb-0">{{ analysis.name }}</h1>
      <DsfrBadge :label="statusLabels[analysis.status].label" :type="statusLabels[analysis.status].type" small />
      <DsfrTag v-if="sharing" :label="sharing.label" :title="sharing.title" small data-testid="sharing" />
      <div v-if="isOwner" class="dashboard__delete">
        <ConfirmButton
          label="Supprimer"
          question="Supprimer cette analyse et ses résultats ?"
          confirm-label="Oui, supprimer"
          @confirm="deleteAnalysis"
        />
      </div>
    </template>

    <p class="dashboard__meta fr-mb-0" data-testid="meta">
      Par <strong>{{ analysis.ownerName }}</strong> · {{ modelNames(analysis).join(', ') }}
      <span v-if="analysis.description"> — {{ analysis.description }}</span>
    </p>

    <section class="dashboard__stats" aria-label="Chiffres de l’analyse">
      <StatTile compact :value="stats.views" label="Vues" />
      <StatTile compact selectable :value="stats.uses" label="Utilisations" @select="filterRuns(null)" />
      <StatTile compact selectable :selected="statusFilter === 'done'" :value="stats.done" label="Terminées" tone="success" @select="filterRuns('done')" />
      <StatTile compact selectable :selected="statusFilter === 'running'" :value="stats.running" label="En cours" tone="info" @select="filterRuns('running')" />
      <StatTile compact selectable :selected="statusFilter === 'failed'" :value="stats.failed" label="En erreur" tone="error" @select="filterRuns('failed')" />
    </section>

    <div class="dashboard__main">
      <!-- Left: the document to try, or the one that was tried. -->
      <section class="tester" aria-labelledby="tester-title">
        <div class="tester__bar">
          <h2 id="tester-title" class="fr-h6 fr-mb-0">{{ run ? 'Document testé' : 'Tester l’analyse' }}</h2>
          <template v-if="run">
            <span class="tester__name" data-testid="tested-name" :title="run.fileName">{{ run.fileName }}</span>
            <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" data-testid="another" @click="newTest">Nouveau test</button>
          </template>
        </div>

        <input
          id="test-file"
          class="fr-sr-only tester__input"
          type="file"
          aria-label="Document à tester"
          :accept="ACCEPTED_DOCUMENT_TYPES.join(',')"
          @change="onFile"
        />
        <template v-if="!run">
          <div class="fr-checkbox-group fr-checkbox-group--sm tester__keep">
            <input id="save-screenshot" v-model="saveScreenshot" type="checkbox" data-testid="save-screenshot" />
            <label class="fr-label" for="save-screenshot">
              Enregistrer une capture du document testé
              <span class="fr-hint-text">Vous pourrez la supprimer ensuite.</span>
            </label>
          </div>
          <label
            class="dropzone"
            :class="{ 'dropzone--over': dragging }"
            for="test-file"
            data-testid="dropzone"
            @dragover.prevent="dragging = true"
            @dragleave="dragging = false"
            @drop.prevent="onDrop"
          >
            <span class="dropzone__title">Déposez un document ici</span>
            <span class="dropzone__hint">ou cliquez pour en choisir un · image ou PDF, 20 Mo au plus</span>
          </label>
        </template>
        <p v-if="uploading" class="fr-hint-text fr-mb-0" role="status">Analyse du document…</p>
        <p v-if="fault" class="fr-error-text fr-mb-0" role="alert">{{ fault }}</p>
        <p v-if="actionError" class="fr-error-text fr-mb-0" role="alert" data-testid="action-error">{{ actionError }}</p>

        <div v-if="run?.screenshot" class="tester__viewer">
          <DocumentViewer
            v-model:page="viewerPage"
            :document="run.screenshot"
            :entities="outlined"
            :highlight-id="shown?.id"
            :drawing="adding && tab === 'elements'"
            :fit="wide"
            @draw="onDraw"
            @cancel="adding = false"
            @select="selectElement"
          />
        </div>
        <p v-else-if="run" class="tester__nofile" data-testid="no-screenshot">
          <template v-if="run.fileDecision === 'deleted'">La capture de ce document a été supprimée : les résultats et vos décisions sont conservés.</template>
          <template v-else>Aucune capture n’a été enregistrée pour ce test : les éléments trouvés sont listés à droite, sans le document.</template>
        </p>
        <!-- The document: asked about once everything is looked at, and deletable at any time. -->
        <template v-if="run">
          <div v-if="askAboutFile" class="file file--ask" role="group" aria-label="Fichier de test" data-testid="file-question">
            <p class="fr-mb-0"><strong>Toutes les prédictions sont vérifiées.</strong> Supprimer le fichier de test ?</p>
            <div class="file__actions">
              <button type="button" class="fr-btn fr-btn--sm" data-testid="file-delete" @click="removeFile">Supprimer le fichier</button>
              <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" data-testid="file-keep" @click="keepFile">Le conserver</button>
            </div>
          </div>
          <p v-else-if="run.screenshot" class="file fr-mb-0" data-testid="file-state">
            Capture enregistrée{{ run.fileDecision === 'kept' ? ' (conservée)' : '' }}.
            <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline" data-testid="file-delete" @click="removeFile">Supprimer le fichier</button>
          </p>
          <p v-else class="file fr-mb-0" data-testid="file-state">
            {{ run.fileDecision === 'deleted' ? 'Fichier supprimé.' : 'Capture non enregistrée.' }}
          </p>
        </template>
      </section>

      <!-- Right: what was found and decided (the page, then its elements), and the uses. -->
      <section class="side" aria-label="Résultat et utilisations">
        <TabList v-model="tab" :tabs="tabs" label="Résultat et utilisations" />

        <div v-if="tab === 'runs'" role="tabpanel" class="side__panel" data-testid="runs">
          <p v-if="statusFilter" class="fr-text--sm fr-mb-0" data-testid="runs-filter">
            Utilisations « {{ statusLabels[statusFilter].label }} » :
            <button type="button" class="fr-link fr-link--sm" data-testid="runs-filter-clear" @click="statusFilter = null">Tout afficher</button>
          </p>
          <RunsList
            :runs="shownRuns"
            :can-see="canSeeResult"
            :can-cancel="canCancel"
            :selected-id="run?.id"
            :empty-text="statusFilter ? `Aucune utilisation « ${statusLabels[statusFilter].label} ».` : undefined"
            @open="open"
            @cancel="cancel"
          />
        </div>

        <div v-else-if="!run" role="tabpanel" class="side__panel" data-testid="results">
          <div class="steps" data-testid="steps">
            <p class="fr-mb-0"><strong>Comment ça marche</strong></p>
            <ol class="steps__list">
              <li>Déposez un document à gauche : une image ou un PDF. Un test est une utilisation de l’analyse.</li>
              <li>L’analyse y cherche {{ modelNames(analysis).join(', ') }}.</li>
              <li>Vous voyez à quel modèle correspond la page, et chaque élément trouvé sur le document, avec la confiance de chaque réponse.</li>
              <li>Validez ou invalidez chaque prédiction, annotez-la avec un modèle de l’analyse, ou ajoutez à la main un élément manqué.</li>
            </ol>
            <p class="fr-hint-text fr-mb-0">Le résultat d’un test n’est visible que par vous, même pour un administrateur.</p>
          </div>
        </div>

        <div v-else-if="run.status === 'running'" role="tabpanel" class="side__panel" data-testid="results">
          <p class="fr-mb-0" role="status" data-testid="run-running">
            <strong>Analyse en cours…</strong> Le résultat s’affichera ici dès qu’il sera prêt.
          </p>
          <div>
            <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" data-testid="cancel-run" @click="cancel(run.id)">Annuler l’analyse</button>
          </div>
        </div>

        <div v-else-if="run.status === 'cancelled'" role="tabpanel" class="side__panel" data-testid="results">
          <p class="fr-mb-0" role="status" data-testid="run-cancelled">
            Cette analyse a été annulée. Vous pouvez recommencer avec « Nouveau test ».
          </p>
        </div>

        <div v-else-if="run.status === 'failed'" role="tabpanel" class="side__panel" data-testid="results">
          <p class="fr-error-text fr-mb-0" role="alert" data-testid="run-failed">
            L’analyse de ce document a échoué. Vous pouvez réessayer avec « Nouveau test ».
          </p>
        </div>

        <div v-else role="tabpanel" class="side__panel" data-testid="results">
          <p class="side__summary fr-mb-0" data-testid="test-summary">
            <template v-if="detections.length">
              <strong>{{ detections.length }} élément{{ detections.length > 1 ? 's' : '' }}</strong>
              · {{ foundModels }} modèle{{ foundModels > 1 ? 's' : '' }} sur {{ searched.length }}
            </template>
            <strong v-else data-testid="nothing-found">Aucun élément trouvé dans ce document.</strong>
            · <span data-testid="progress">{{ progress.reviewed }} / {{ progress.total }} vérifiée{{ progress.reviewed > 1 ? 's' : '' }}</span>
          </p>

          <!-- The page: which model it corresponds to. -->
          <template v-if="tab === 'page' && pageResult">
            <PagerControls v-if="pageCount > 1" v-model="pageIndex" :count="pageCount" noun="Page" data-testid="page-pager" />
            <DetectionCard
              :detection="{ id: 'page', zone: { page: pageResult.page, points: [] }, classifications: pageResult.classifications }"
              :title="pageCount > 1 ? `Classification de la page ${pageResult.page}` : 'Classification de la page'"
              :name-of="nameOf"
              data-testid="page-card"
            >
              <ReviewControls :review="pageResult.review" :models="pageModels" :model-name="nameOf" @review="reviewPageDecision" />
            </DetectionCard>
          </template>

          <!-- The elements: found by the analysis, or drawn by hand. -->
          <template v-if="tab === 'elements'">
            <div v-if="adding" class="adding" data-testid="adding">
              <label class="fr-label" for="new-element-model">Modèle de l’élément à ajouter</label>
              <div class="adding__row">
                <select id="new-element-model" v-model="newModel" class="fr-select adding__select" data-testid="new-element-model">
                  <option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</option>
                </select>
                <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" data-testid="add-cancel" @click="adding = false">Annuler</button>
              </div>
              <template v-if="entitiesOfNewModel.length">
                <label class="fr-label" for="new-element-entity">Entité <span class="fr-hint-text">(facultatif)</span></label>
                <select id="new-element-entity" v-model="newEntity" class="fr-select adding__select" data-testid="new-element-entity">
                  <option value="">Je ne sais pas</option>
                  <option v-for="entity in entitiesOfNewModel" :key="entity.id" :value="entity.id">{{ entity.name }}</option>
                </select>
              </template>
              <p class="fr-hint-text fr-mb-0" data-testid="adding-hint">Dessinez la zone sur le document : un polygone, ou un rectangle.</p>
            </div>
            <div v-else class="elements__bar">
              <PagerControls v-if="shown" v-model="current" :count="detections.length" noun="Élément" masculine />
              <button
                type="button"
                class="fr-btn fr-btn--sm fr-btn--secondary fr-icon-add-line fr-btn--icon-left"
                :disabled="!canDraw"
                :title="canDraw ? undefined : 'Il faut une capture du document pour dessiner une zone.'"
                data-testid="add-element"
                @click="startAdding"
              >
                Ajouter un élément
              </button>
            </div>
            <p v-if="!canDraw && !adding" class="fr-hint-text fr-mb-0" data-testid="cannot-draw">Pour ajouter un élément, gardez une capture du document.</p>

            <template v-if="shown && !adding">
              <ManualElementCard v-if="shown.source === 'manual'" :key="shown.id" :element="shown" :position="current + 1" :model-name="nameOf" @remove="remove(shown.id)" />
              <DetectionCard v-else :key="shown.id" :detection="shown" :position="current + 1" :name-of="nameOf" :entity-name="entityName(shown)" :document="run?.screenshot">
                <ReviewControls :review="shown.review" :models="models" :model-name="nameOf" @review="review(shown.id, $event)" />
              </DetectionCard>
            </template>
          </template>
        </div>
      </section>
    </div>
  </FixedPage>
</template>

<style scoped>
.dashboard__delete {
  margin-left: auto;
}

.dashboard__title {
  margin-right: auto;
}

.dashboard__meta {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.dashboard__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
  gap: 0.5rem;
}

.dashboard__main {
  display: grid;
  gap: 1rem;
  min-height: 0;
}

.tester,
.side {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  min-height: 0;
}

.tester__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}

.tester__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 0.875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tester__keep {
  margin: 0;
}

.tester__nofile {
  margin: 0;
  padding: 1.5rem 1rem;
  border: 1px dashed var(--border-default-grey);
  color: var(--text-mention-grey);
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

.tester__input:focus-visible ~ .dropzone {
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

.side__panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.steps {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: 1px dashed var(--border-default-grey);
}

.steps__list {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding-left: 1.25rem;
}

.file {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  font-size: 0.875rem;
}

.elements__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.adding {
  display: grid;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-action-high-blue-france);
  background: var(--background-contrast-info);
}

.adding__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.adding__select {
  flex: 1 1 12rem;
  max-width: 20rem;
  margin-top: 0;
}

.file--ask {
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-action-high-blue-france);
  background: var(--background-contrast-info);
  font-size: 1rem;
}

.file__actions {
  display: flex;
  gap: 0.5rem;
}

@media (min-width: 64em) {
  .dashboard__main {
    flex: 1;
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }

  .tester__viewer {
    flex: 1;
    min-height: 0;
  }

  /* Only as a last resort, on a window too short for it, does the side scroll. */
  .side {
    overflow-y: auto;
  }
}
</style>
