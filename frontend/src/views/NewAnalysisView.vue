<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import FixedPage from '../components/FixedPage.vue'
import ListTile from '../components/ListTile.vue'
import PagedList from '../components/PagedList.vue'
import ShareInput from '../components/ShareInput.vue'
import TemplatePreview from '../components/TemplatePreview.vue'
import { useAnalyses } from '../composables/useAnalyses'
import { useCatalogue } from '../composables/useCatalogue'
import { useGroups } from '../composables/useGroups'
import type { Share, Template } from '../data/mock'

const MAX_DESCRIPTION = 300

const router = useRouter()
const { createAnalysis } = useAnalyses()
const { filter } = useCatalogue()
const { groups } = useGroups()

const name = ref('')
const description = ref('')
// Who can see the analysis: everyone, or only the people and the groups named. What was named is kept when it is made
// public, in case it is not after all.
const isPublic = ref(false)
const shares = ref<Share[]>([])
const shareInput = ref<InstanceType<typeof ShareInput>>()
// What is picked stays picked, whatever is searched for or shown meanwhile.
const selected = ref<string[]>([])
const query = ref('')
const mine = ref(false)
const preview = ref<Template | null>(null)
const nameError = ref('')
const templatesError = ref('')
const sharesError = ref(false)

const results = computed(() => filter(query.value, mine.value))
const toComplete = computed(() => [
  ...(nameError.value ? ['le nom'] : []),
  ...(templatesError.value ? ['au moins un modèle'] : []),
  ...(sharesError.value ? ['le destinataire à corriger'] : []),
])
const selectedLabel = computed(() => ` · ${selected.value.length} sélectionné${selected.value.length > 1 ? 's' : ''}`)

function toggle(id: string) {
  selected.value = selected.value.includes(id) ? selected.value.filter((s) => s !== id) : [...selected.value, id]
}

// A click anywhere on a card picks it, except on what has its own job: the box, its label, the detail button, a link.
function onTileClick(event: MouseEvent, id: string) {
  if ((event.target as Element).closest('button, input, label, a')) return
  toggle(id)
}

async function submit() {
  nameError.value = name.value.trim() ? '' : 'Donnez un nom à l’analyse.'
  templatesError.value = selected.value.length ? '' : 'Choisissez au moins un modèle du catalogue.'
  // What was typed in the recipients' field and not yet taken (a click on the button comes before the field's own blur).
  sharesError.value = !isPublic.value && shareInput.value?.commit() === false
  if (nameError.value || templatesError.value || sharesError.value) return
  // In the order of the catalogue, not of the clicks.
  const order = filter('').map((t) => t.id)
  createAnalysis({
    name: name.value,
    description: description.value,
    templateIds: [...selected.value].sort((a, b) => order.indexOf(a) - order.indexOf(b)),
    isPublic: isPublic.value,
    shares: shares.value,
  })
  await router.push({ name: 'analyses' })
}
</script>

<template>
  <form novalidate @submit.prevent="submit">
    <FixedPage :from="64">
      <template #header>
        <h1 class="new-analysis__title fr-h4 fr-mb-0">Nouvelle analyse</h1>
        <!-- What is missing, on the title's line: it takes no height of its own. -->
        <p v-if="toComplete.length" class="new-analysis__alert fr-error-text fr-mb-0" role="alert" data-testid="missing">
          À compléter : {{ toComplete.join(', ') }}.
        </p>
        <div class="new-analysis__actions">
          <RouterLink class="fr-btn fr-btn--secondary" :to="{ name: 'analyses' }">Annuler</RouterLink>
          <DsfrButton type="submit" label="Lancer l’analyse" />
        </div>
      </template>

      <div class="new-analysis__layout">
        <section class="new-analysis__form" aria-label="Informations sur l’analyse">
          <DsfrInputGroup
            v-model="name"
            label="Nom de l’analyse"
            :label-visible="true"
            :error-message="nameError"
            :is-invalid="!!nameError"
          />
          <DsfrInputGroup
            v-model="description"
            label="Description"
            :label-visible="true"
            is-textarea
            :rows="3"
            :maxlength="MAX_DESCRIPTION"
            hint="Facultative : à quoi sert cette analyse ?"
          />
          <div class="new-analysis__sharing">
            <DsfrToggleSwitch v-model="isPublic" label="Analyse publique" hint="Visible par tous les utilisateurs" data-testid="public" />
            <ShareInput ref="shareInput" v-model="shares" :groups="groups" :disabled="isPublic" />
          </div>
        </section>

        <section class="new-analysis__models" aria-label="Modèles à rechercher">
          <div class="new-analysis__filters">
            <div class="new-analysis__search">
              <DsfrInput v-model="query" label="Rechercher un modèle" placeholder="Rechercher un modèle" type="search" />
            </div>
            <div class="new-analysis__scope" role="group" aria-label="Afficher">
              <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--tertiary': mine }" :aria-pressed="!mine" @click="mine = false">
                Tous
              </button>
              <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--tertiary': !mine }" :aria-pressed="mine" @click="mine = true">
                Mes modèles
              </button>
            </div>
          </div>

          <PagedList
            :items="results"
            :item-key="(t) => t.id"
            noun="modèle"
            :suffix="selectedLabel"
            :reset-key="`${query}|${mine}`"
            :fixed-from="64"
            min-card="15rem"
          >
            <template #empty>
              <p v-if="mine && !query.trim()" role="status">Vous n’avez pas encore de modèle.</p>
              <p v-else role="status">Aucun modèle ne correspond à « {{ query }} ».</p>
            </template>
            <template #item="{ item: template }">
              <ListTile
                :title="template.name"
                :description="template.description"
                :selected="selected.includes(template.id)"
                class="new-analysis__tile"
                @click="onTileClick($event, template.id)"
              >
                <template #title>
                  <div class="fr-checkbox-group fr-checkbox-group--sm">
                    <input :id="`template-${template.id}`" v-model="selected" type="checkbox" :value="template.id" />
                    <label class="fr-label" :for="`template-${template.id}`" :title="template.name">
                      <span class="new-analysis__model-name">{{ template.name }}</span>
                    </label>
                  </div>
                </template>
                <template v-if="template.categories.length" #tags>
                  <DsfrTag v-for="category in template.categories" :key="category" :label="category" small />
                </template>
                <template #foot>
                  <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary new-analysis__detail" @click="preview = template">
                    Voir le détail<span class="fr-sr-only"> de {{ template.name }}</span>
                  </button>
                  <span class="new-analysis__owner">Par {{ template.ownerId }}</span>
                </template>
              </ListTile>
            </template>
          </PagedList>
        </section>
      </div>
    </FixedPage>
  </form>

  <TemplatePreview :template="preview" @close="preview = null" />
</template>

<style scoped>
.new-analysis__title {
  margin-right: auto;
}

.new-analysis__alert {
  flex: 1 1 12rem;
  min-width: 0;
}

.new-analysis__actions {
  display: flex;
  gap: 0.5rem;
}

/* The form on the left, the models on the right; one above the other on a narrow screen. */
.new-analysis__layout {
  display: grid;
  gap: 1.5rem;
}

.new-analysis__form,
.new-analysis__models {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.new-analysis__sharing {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.new-analysis__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

.new-analysis__search {
  flex: 1 1 12rem;
  max-width: 22rem;
}

.new-analysis__scope {
  display: flex;
  gap: 0.25rem;
}

/* Each error message sits under its field and would push the form down by a line: they stay in the page, for screen
   readers, but only the summary above shows. */
.new-analysis__form :deep(.fr-messages-group) {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.new-analysis__tile {
  cursor: pointer;
}

/* The tile's own title is the check box and its name. */
.new-analysis__tile :deep(.fr-checkbox-group) {
  margin: 0;
}

/* A long name is cut with « … » on the text, not on the label: the box is drawn outside the label, and would be cut too. */
.new-analysis__tile :deep(.fr-checkbox-group label) {
  display: block;
  font-weight: 700;
}

.new-analysis__model-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.new-analysis__owner {
  margin-left: auto;
  overflow: hidden;
  color: var(--text-mention-grey);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (min-width: 64em) {
  .new-analysis__layout {
    flex: 1;
    min-height: 0;
    grid-template-columns: 21rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }

  .new-analysis__form {
    overflow-y: auto;
    padding-right: 0.25rem;
  }

  .new-analysis__models {
    min-height: 0;
  }
}
</style>
