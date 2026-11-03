<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConfirmButton from '../components/ConfirmButton.vue'
import DocumentViewer from '../components/DocumentViewer.vue'
import EntitiesPane from '../components/EntitiesPane.vue'
import PagerControls from '../components/PagerControls.vue'
import TemplateLayout from '../components/TemplateLayout.vue'
import { changedFields, MAX_COMMENT_LENGTH, useCatalogue } from '../composables/useCatalogue'
import { useSession } from '../composables/useSession'
import { useWideScreen } from '../composables/useWideScreen'
import type { SuggestionStatus } from '../data/mock'

// The same page as the form, to look at: the owner changes the model from here, anyone else suggests a change.
const route = useRoute()
const router = useRouter()
const { userId } = useSession()
const { find, isOwner, canDecide, isStarred, toggleStar, toggleSuggestionStar, resolveSuggestion, addComment, actionError, remove } =
  useCatalogue()
const wide = useWideScreen()

const template = computed(() => find(String(route.params.id)))
const owner = computed(() => !!template.value && isOwner(template.value))
// The owner, or an administrator: they accept or refuse the suggestions.
const decides = computed(() => !!template.value && canDecide(template.value))

type Tab = 'entities' | 'suggestions'
const tab = ref<Tab>(route.query.onglet === 'suggestions' ? 'suggestions' : 'entities')
const entityIndex = ref(0)
// The page of the document shown (from 1): what is said of it is shown under the heading.
const shownPage = ref(1)
const pageNote = computed(() => (template.value && template.value.pages.length > 1 ? template.value.pages[shownPage.value - 1] : undefined))
const suggestionIndex = ref(0)
const commentText = ref('')
const commentList = ref<HTMLElement>()

watch(
  () => route.params.id,
  () => {
    entityIndex.value = 0
    suggestionIndex.value = 0
    shownPage.value = 1
  },
)
watch(suggestionIndex, () => (commentText.value = ''))

const entity = computed(() => template.value?.entities[entityIndex.value])
const suggestion = computed(() => template.value?.suggestions[suggestionIndex.value])
const pending = computed(() => template.value?.suggestions.filter((s) => s.status === 'pending').length ?? 0)
const suggestionStarred = computed(
  () => !!suggestion.value && userId.value !== null && suggestion.value.stars.includes(userId.value),
)

const statusBadges: Record<SuggestionStatus, { label: string; type: 'info' | 'success' | 'error' }> = {
  pending: { label: 'En attente', type: 'info' },
  accepted: { label: 'Acceptée', type: 'success' },
  rejected: { label: 'Refusée', type: 'error' },
}

/** Deletes the model, once the owner has said they are sure; the catalogue says why when it cannot (an analysis uses it). */
async function deleteTemplate() {
  if (template.value && (await remove(template.value.id))) await router.push({ name: 'catalogue' })
}

async function comment() {
  if (!template.value || !suggestion.value) return
  if (!(await addComment(template.value.id, suggestion.value.id, commentText.value))) return
  commentText.value = ''
  // The newest comment is the last: bring it into view.
  await nextTick()
  commentList.value?.scrollTo?.({ top: commentList.value.scrollHeight })
}
</script>

<template>
  <p v-if="!template" role="status">
    Ce modèle n’existe pas. <RouterLink :to="{ name: 'catalogue' }">Retour au catalogue</RouterLink>
  </p>

  <TemplateLayout v-else>
    <template #header>
      <RouterLink class="fr-link fr-link--sm fr-icon-arrow-left-line fr-link--icon-left" :to="{ name: 'catalogue' }">Catalogue</RouterLink>
      <h1 class="template-view__title fr-h5 fr-mb-0">{{ template.name }}</h1>
      <div class="template-view__actions">
        <button
          type="button"
          class="fr-btn fr-btn--secondary fr-btn--icon-left"
          :class="isStarred(template) ? 'fr-icon-star-fill' : 'fr-icon-star-line'"
          data-testid="star"
          :aria-pressed="isStarred(template)"
          @click="toggleStar(template.id)"
        >
          {{ isStarred(template) ? 'Retirer des favoris' : 'Ajouter aux favoris' }} ({{ template.stars.length }})
        </button>
        <RouterLink class="fr-btn fr-icon-edit-line fr-btn--icon-left" :to="{ name: 'catalogue-edit', params: { id: template.id } }">
          {{ owner ? 'Modifier' : 'Suggérer une modification' }}
        </RouterLink>
        <ConfirmButton
          v-if="owner"
          label="Supprimer"
          question="Supprimer ce modèle ?"
          confirm-label="Oui, supprimer"
          @confirm="deleteTemplate"
        />
      </div>
    </template>

    <template #document>
      <div class="template-view__doc-head">
        <h2 class="fr-h6 fr-mb-0">Document d’exemple</h2>
        <p v-if="template.document" class="template-view__doc-name" data-testid="document-name">{{ template.document.name }}</p>
      </div>
      <p v-if="pageNote" class="template-view__page fr-mb-0" data-testid="page-note">
        <strong>{{ pageNote.label }}</strong>
        <span v-if="pageNote.description"> — {{ pageNote.description }}</span>
      </p>
      <div v-if="template.document" class="template-view__viewer">
        <DocumentViewer
          v-model:page="shownPage"
          :document="template.document"
          :entities="template.entities"
          :highlight-id="tab === 'entities' ? entity?.id : undefined"
          :fit="wide"
        />
      </div>
      <p v-else class="template-view__empty">Ce modèle n’a pas de document d’exemple.</p>
    </template>

    <div class="template-view__side">
      <p class="template-view__meta fr-mb-0">
        Par <strong data-testid="template-owner">{{ template.ownerName }}</strong>
        <DsfrTag v-for="category in template.categories" :key="category" :label="category" small />
      </p>
      <p class="template-view__description fr-mb-0" data-testid="description">{{ template.description }}</p>
      <p v-if="actionError" class="fr-error-text fr-mb-0" role="alert" data-testid="action-error">{{ actionError }}</p>

      <div class="template-view__tabs" role="tablist" aria-label="Entités et suggestions">
        <button
          type="button"
          role="tab"
          class="template-view__tab"
          :aria-selected="tab === 'entities'"
          @click="tab = 'entities'"
        >
          Entités ({{ template.entities.length }})
        </button>
        <button
          type="button"
          role="tab"
          class="template-view__tab"
          :aria-selected="tab === 'suggestions'"
          @click="tab = 'suggestions'"
        >
          Suggestions ({{ template.suggestions.length }})
          <DsfrBadge v-if="decides && pending" :label="`${pending} en attente`" type="new" small />
        </button>
      </div>

      <!-- Entities: one at a time, like the form. -->
      <div v-if="tab === 'entities'" role="tabpanel" class="template-view__panel">
        <EntitiesPane v-model:index="entityIndex" :template="template" />
      </div>

      <!-- Suggestions: one at a time too, with their discussion. -->
      <div v-else role="tabpanel" class="template-view__panel">
        <p v-if="!suggestion" role="status">Aucune suggestion pour ce modèle.</p>
        <template v-else>
          <PagerControls v-model="suggestionIndex" :count="template.suggestions.length" noun="Suggestion" />
          <div :key="suggestion.id" class="card" data-testid="suggestion">
            <div class="card__head">
              <p class="fr-mb-0">
                <strong>{{ suggestion.authorName }}</strong> · {{ suggestion.date }}
              </p>
              <DsfrBadge :label="statusBadges[suggestion.status].label" :type="statusBadges[suggestion.status].type" small />
              <button
                type="button"
                class="fr-btn fr-btn--sm fr-btn--tertiary fr-btn--icon-left card__star"
                :class="suggestionStarred ? 'fr-icon-star-fill' : 'fr-icon-star-line'"
                data-testid="suggestion-star"
                :aria-pressed="suggestionStarred"
                :title="suggestionStarred ? 'Retirer cette suggestion des favoris' : 'Ajouter cette suggestion aux favoris'"
                @click="toggleSuggestionStar(template.id, suggestion.id)"
              >
                {{ suggestion.stars.length }}<span class="fr-sr-only"> favori{{ suggestion.stars.length > 1 ? 's' : '' }}</span>
              </button>
            </div>
            <p v-if="suggestion.message" class="fr-mb-0">« {{ suggestion.message }} »</p>
            <ul class="card__changes fr-mb-0">
              <li v-for="change in changedFields(template, suggestion.fields)" :key="change.label">
                {{ change.label }} : <del>{{ change.before }}</del> → <ins>{{ change.after }}</ins>
              </li>
            </ul>
            <p v-if="!changedFields(template, suggestion.fields).length" class="fr-hint-text fr-mb-0">
              Plus aucune différence avec la version actuelle.
            </p>
            <div v-if="decides && suggestion.status === 'pending'" class="card__decision">
              <button type="button" class="fr-btn fr-btn--sm" @click="resolveSuggestion(template.id, suggestion.id, true)">Accepter</button>
              <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" @click="resolveSuggestion(template.id, suggestion.id, false)">
                Refuser
              </button>
            </div>

            <section class="comments" aria-labelledby="comments-title">
              <h4 id="comments-title" class="fr-text--sm fr-text--bold fr-mb-0">Commentaires ({{ suggestion.comments.length }})</h4>
              <ul v-if="suggestion.comments.length" ref="commentList" class="comments__list" data-testid="comments">
                <li v-for="c in suggestion.comments" :key="c.id" data-testid="comment">
                  <strong>{{ c.authorName }}</strong> <span class="comments__date">· {{ c.date }}</span>
                  <br />{{ c.text }}
                </li>
              </ul>
              <p v-else class="fr-hint-text fr-mb-0">Aucun commentaire.</p>
              <form class="comments__form" @submit.prevent="comment">
                <DsfrInput
                  v-model="commentText"
                  label="Ajouter un commentaire"
                  placeholder="Ajouter un commentaire…"
                  :maxlength="MAX_COMMENT_LENGTH"
                />
                <DsfrButton type="submit" label="Commenter" size="sm" :disabled="!commentText.trim()" />
              </form>
            </section>
          </div>
        </template>
      </div>
    </div>
  </TemplateLayout>
</template>

<style scoped>
.template-view__title {
  margin-right: auto;
}

.template-view__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.template-view__doc-head {
  display: flex;
  align-items: center;
  gap: 0.5rem 1rem;
}

.template-view__doc-name {
  flex: 1;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-size: 0.875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-view__page {
  font-size: 0.875rem;
}

.template-view__empty {
  margin: 0;
  padding: 2rem 1rem;
  border: 1px dashed var(--border-default-grey);
  color: var(--text-mention-grey);
  text-align: center;
}

.template-view__side {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.template-view__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
}

/* A long description scrolls in its own box rather than pushing the rest of the page down. */
.template-view__description {
  max-height: 4.5rem;
  overflow-y: auto;
}

.template-view__tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.template-view__tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text-action-high-grey);
  font: inherit;
  cursor: pointer;
}

.template-view__tab[aria-selected='true'] {
  border-bottom-color: var(--border-action-high-blue-france);
  color: var(--text-action-high-blue-france);
  font-weight: 700;
}

.template-view__panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.card {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
}

.card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.card__star {
  margin-left: auto;
}

.card__changes {
  margin: 0;
  padding-left: 1.25rem;
}

.card__decision {
  display: flex;
  gap: 0.5rem;
}

.comments {
  display: grid;
  gap: 0.375rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-default-grey);
}

/* The discussion can be long: it scrolls in its own box, newest at the bottom. */
.comments__list {
  display: grid;
  gap: 0.375rem;
  max-height: 7rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  font-size: 0.875rem;
}

.comments__date {
  color: var(--text-mention-grey);
}

.comments__form {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.comments__form > :first-child {
  flex: 1;
  min-width: 0;
}

@media (min-width: 64em) {
  .template-view__viewer {
    flex: 1;
    min-height: 0;
  }
}
</style>
