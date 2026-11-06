<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { canPreview, MAX_EXAMPLE_LENGTH, MAX_EXAMPLES, MAX_TAG_LENGTH, MAX_TAGS, newEntity } from '../composables/useCatalogue'
import { entityTypeDefinition, entityTypeLabel, useEntityTypes } from '../composables/useEntityTypes'
import type { TemplateDocument, TemplateEntity } from '../data/mock'
import InfoTip from './InfoTip.vue'
import PagerControls from './PagerControls.vue'
import TagsInput from './TagsInput.vue'

defineProps<{ document: TemplateDocument | null }>()
const { optionsFor } = useEntityTypes()
const entities = defineModel<TemplateEntity[]>({ required: true })
/** The entity whose zone is being drawn: the document next to the form is then ready to take points. */
const drawingId = defineModel<string | null>('drawingId', { default: null })
/** The entity on show, so the document can outline its zone. */
const currentId = defineModel<string | null>('currentId', { default: null })

interface EntityErrors {
  name?: string
  definition?: string
  zone?: string
}

// One entity at a time, so the form keeps the same height however many there are.
const index = ref(0)
// How an entity is found: by what it is (its definition), or by where it appears on the document.
const zoneIds = ref<string[]>(entities.value.filter((e) => e.zone).map((e) => e.id))
const errors = ref<Record<string, EntityErrors>>({})
/** Positions (1-based) of the entities that are not complete, as of the last `validate()`. */
const incomplete = ref<number[]>([])

const entity = computed(() => entities.value[index.value])
// An entity that comes with its zone (one a PDF suggested) is found by it, whoever put it there.
const inZoneMode = computed(() => !!entity.value && (zoneIds.value.includes(entity.value.id) || !!entity.value.zone))
const entityErrors = computed<EntityErrors>(() => (entity.value && errors.value[entity.value.id]) || {})

watch(
  entity,
  (current) => {
    currentId.value = current?.id ?? null
  },
  { immediate: true },
)

// Moving to another entity ends a drawing under way for this one.
watch(index, () => (drawingId.value = null))

function go(to: number) {
  index.value = Math.min(Math.max(to, 0), entities.value.length - 1)
}

// The model only reflects an assignment once the parent has re-rendered: the new list is worked out first, not read back.
function add() {
  drawingId.value = null
  const next = [...entities.value, newEntity()]
  entities.value = next
  index.value = next.length - 1
}

function remove() {
  const gone = entity.value
  if (!gone) return
  drawingId.value = null
  zoneIds.value = zoneIds.value.filter((id) => id !== gone.id)
  const next = entities.value.filter((e) => e.id !== gone.id)
  entities.value = next
  delete errors.value[gone.id]
  index.value = Math.max(0, Math.min(index.value, next.length - 1))
}

function setMode(mode: 'definition' | 'zone') {
  const current = entity.value
  if (!current) return
  if (mode === 'zone') {
    zoneIds.value = [...zoneIds.value, current.id]
    // Choosing a zone is choosing to draw it: the document is ready at once, no second click needed.
    drawingId.value = current.id
    return
  }
  zoneIds.value = zoneIds.value.filter((id) => id !== current.id)
  delete current.zone
  if (drawingId.value === current.id) drawingId.value = null
}

/** Marks what is missing on each entity and returns whether all of them are complete. */
function validate(): boolean {
  errors.value = Object.fromEntries(
    entities.value.map((e) => [
      e.id,
      {
        name: e.name.trim() ? undefined : 'Donnez un nom à l’entité.',
        definition: e.definition.trim() ? undefined : 'Ajoutez une définition.',
        zone: zoneIds.value.includes(e.id) && !e.zone ? 'Dessinez la zone sur le document.' : undefined,
      },
    ]),
  )
  incomplete.value = entities.value.flatMap((e, i) => (Object.values(errors.value[e.id]).some(Boolean) ? [i + 1] : []))
  // Show the first entity that is not complete.
  if (incomplete.value.length) go(incomplete.value[0] - 1)
  return incomplete.value.length === 0
}

defineExpose({ validate, incomplete })
</script>

<template>
  <section class="entities" aria-labelledby="entities-title">
    <div class="entities__head">
      <h2 id="entities-title" class="fr-h6 fr-mb-0">Entités<span class="fr-sr-only"> à rechercher</span></h2>
      <PagerControls v-model="index" :count="entities.length" noun="Entité">
        <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary fr-icon-add-line fr-btn--icon-left" @click="add">Ajouter</button>
        <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline" :disabled="!entity" title="Supprimer cette entité" @click="remove">
          Supprimer<span class="fr-sr-only"> cette entité</span>
        </button>
      </PagerControls>
    </div>

    <p v-if="!entity" class="entities__empty" role="status">
      Aucune entité : ajoutez-en une pour dire ce qu’il faut retrouver dans les documents.
    </p>

    <div v-else :key="entity.id" class="entity" data-testid="entity">
      <div class="entity__identity">
        <DsfrInputGroup
          v-model="entity.name"
          label="Nom"
          :label-visible="true"
          :error-message="entityErrors.name"
          :is-invalid="!!entityErrors.name"
        />
        <div class="fr-select-group entity__type">
          <!-- The label and the « i » side by side: a button inside a label would take the click meant for the field. -->
          <div class="entity__type-label">
            <label class="fr-label" :for="`type-${entity.id}`">Type</label>
            <InfoTip :label="`Définition du type ${entityTypeLabel(entity.type)}`" align="end">
              <strong>{{ entityTypeLabel(entity.type) }}</strong>
              <br />
              {{ entityTypeDefinition(entity.type) || 'Aucune définition pour ce type.' }}
            </InfoTip>
          </div>
          <select :id="`type-${entity.id}`" v-model="entity.type" class="fr-select">
            <option v-for="option in optionsFor(entity.type)" :key="option.value" :value="option.value">{{ option.text }}</option>
          </select>
        </div>
      </div>

      <!-- How to find it, and the zone controls right here: reachable without scrolling, whatever the entity holds. -->
      <div class="entity__how">
        <fieldset class="entity__modes" :aria-labelledby="`mode-${entity.id}`">
          <legend :id="`mode-${entity.id}`" class="fr-sr-only">Comment la repérer ?</legend>
          <div class="fr-radio-group fr-radio-group--sm">
            <input :id="`mode-${entity.id}-definition`" type="radio" :name="`mode-${entity.id}`" :checked="!inZoneMode" @change="setMode('definition')" />
            <label class="fr-label" :for="`mode-${entity.id}-definition`">Par définition</label>
          </div>
          <div class="fr-radio-group fr-radio-group--sm">
            <input
              :id="`mode-${entity.id}-zone`"
              type="radio"
              :name="`mode-${entity.id}`"
              :checked="inZoneMode"
              :disabled="!canPreview(document)"
              @change="setMode('zone')"
            />
            <label class="fr-label" :for="`mode-${entity.id}-zone`">Par zone</label>
          </div>
        </fieldset>

        <div v-if="inZoneMode" class="entity__zone">
          <template v-if="drawingId === entity.id">
            <span class="entity__drawing" data-testid="draw-hint">Dessin en cours…</span>
            <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" @click="drawingId = null">Annuler</button>
          </template>
          <button v-else type="button" class="fr-btn fr-btn--sm fr-btn--secondary" @click="drawingId = entity.id">
            {{ entity.zone ? 'Redessiner' : 'Dessiner la zone' }}
          </button>
          <button
            v-if="entity.zone && drawingId !== entity.id"
            type="button"
            class="fr-btn fr-btn--sm fr-btn--tertiary"
            data-testid="delete-zone"
            @click="delete entity.zone"
          >
            Supprimer la zone
          </button>
        </div>
      </div>
      <p v-if="inZoneMode && entityErrors.zone" class="fr-error-text fr-mb-0" role="alert">{{ entityErrors.zone }}</p>
      <p v-if="!document" class="fr-hint-text fr-mb-0">Ajoutez un document d’exemple pour pouvoir dessiner une zone.</p>

      <div class="entity__meaning">
        <DsfrInputGroup
          v-model="entity.definition"
          label="Définition"
          :label-visible="true"
          is-textarea
          :rows="2"
          :error-message="entityErrors.definition"
          :is-invalid="!!entityErrors.definition"
        />
        <TagsInput
          v-model="entity.examples"
          class="entity__examples"
          multiline
          label="Exemples"
          placeholder="Ex. 12/03/2026"
          :max-length="MAX_EXAMPLE_LENGTH"
          :max-items="MAX_EXAMPLES"
        />
      </div>
      <TagsInput
        v-model="entity.tags"
        class="entity__tags"
        ignore-case
        label="Détails (facultatif)"
        placeholder="Ex. verso, écrit à la main"
        :max-length="MAX_TAG_LENGTH"
        :max-items="MAX_TAGS"
      />
    </div>
  </section>
</template>

<style scoped>
.entities__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.entities__empty {
  margin: 0;
  padding: 1rem;
  border: 1px dashed var(--border-default-grey);
}

.entity {
  display: grid;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem 0.625rem;
  border: 1px solid var(--border-default-grey);
}

/* The name and its type share a line; the definition and the examples of it too: the card keeps its height. */
.entity__identity,
.entity__meaning {
  display: grid;
  gap: 0.75rem;
  align-items: start;
}

.entity__type-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.entity__type select {
  /* DSFR spaces a field from its label only when the two sit side by side: here the label has its « i » beside it. */
  margin-top: 0.5rem;
}

/* The definition and the examples have the same height, so they stand level top and bottom. */
.entity__meaning :deep(textarea) {
  height: 4rem;
  min-height: 4rem;
  resize: none;
}

.entity__identity {
  grid-template-columns: minmax(0, 1fr) 9.5rem;
}

.entity__meaning {
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
}

/* One line: the two ways to find the entity, and what to do about the zone. */
.entity__how {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem 1rem;
}

.entity__modes {
  display: flex;
  flex-wrap: wrap;
  gap: 0 1rem;
  margin: 0;
  padding: 0;
  border: 0;
}

.entity__zone {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.entity__drawing {
  font-weight: 700;
}
</style>
