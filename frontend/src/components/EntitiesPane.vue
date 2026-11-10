<script setup lang="ts">
import { computed } from 'vue'
import { useCatalogue } from '../composables/useCatalogue'
import { entityTypeDefinition, entityTypeLabel, useEntityTypes } from '../composables/useEntityTypes'
import { useSession } from '../composables/useSession'
import type { Template } from '../data/mock'
import InfoTip from './InfoTip.vue'
import PagerControls from './PagerControls.vue'

/** The entities of a model, one at a time, for looking at: what each is, its type, its examples, its stars. */
const props = defineProps<{ template: Template }>()
/** Which entity is on show, so that a document next to it can outline its zone. */
const index = defineModel<number>('index', { default: 0 })

const { userId } = useSession()
const { toggleEntityStar } = useCatalogue()
useEntityTypes() // loads the types, whose labels and definitions are shown below

const entity = computed(() => props.template.entities[index.value])
/** How the entity is found: by its definition, or by its zone (its zones, when it has several). */
const zoneKind = computed(() => {
  const zones = entity.value?.zones ?? []
  if (!zones.length) return 'Définition'
  if (zones.length > 1) return `${zones.length} zones`
  return props.template.pages.length > 1 ? `Zone · page ${zones[0].page}` : 'Zone'
})
const starred = computed(() => !!entity.value && userId.value !== null && entity.value.stars.includes(userId.value))
</script>

<template>
  <p v-if="!entity" role="status">Aucune entité définie pour ce modèle.</p>
  <div v-else class="entities-pane">
    <PagerControls v-model="index" :count="template.entities.length" noun="Entité" />
    <div :key="entity.id" class="entity-card" data-testid="entity">
      <div class="entity-card__head">
        <h3 class="fr-h6 fr-mb-0">{{ entity.name }}</h3>
        <DsfrBadge
          :label="zoneKind"
          :type="entity.zones.length ? 'info' : 'new'"
          small
          data-testid="entity-kind"
        />
        <DsfrTag :label="entityTypeLabel(entity.type)" small data-testid="entity-type" />
        <InfoTip :label="`Définition du type ${entityTypeLabel(entity.type)}`">
          <strong>{{ entityTypeLabel(entity.type) }}</strong>
          <br />
          {{ entityTypeDefinition(entity.type) || 'Aucune définition pour ce type.' }}
        </InfoTip>
        <button
          type="button"
          class="fr-btn fr-btn--sm fr-btn--tertiary fr-btn--icon-left entity-card__star"
          :class="starred ? 'fr-icon-star-fill' : 'fr-icon-star-line'"
          data-testid="entity-star"
          :aria-pressed="starred"
          :title="starred ? 'Retirer cette entité des favoris' : 'Ajouter cette entité aux favoris'"
          @click="toggleEntityStar(template.id, entity.id)"
        >
          {{ entity.stars.length }}<span class="fr-sr-only"> favori{{ entity.stars.length > 1 ? 's' : '' }}</span>
        </button>
      </div>
      <p class="entity-card__text fr-mb-0">{{ entity.definition }}</p>
      <p v-if="entity.examples.length" class="entity-card__examples fr-mb-0" data-testid="entity-examples">
        <span class="fr-text--sm">Exemples :</span>
        <DsfrTag v-for="example in entity.examples" :key="example" :label="example" small />
      </p>
      <p v-if="entity.tags.length" class="entity-card__examples fr-mb-0" data-testid="entity-tags">
        <span class="fr-text--sm">Détails :</span>
        <DsfrTag v-for="tag in entity.tags" :key="tag" :label="tag" small />
      </p>
    </div>
  </div>
</template>

<style scoped>
.entities-pane {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-card {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
}

.entity-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.entity-card__star {
  margin-left: auto;
}

/* A long definition scrolls in its own box rather than pushing the page down. */
.entity-card__text {
  max-height: 6rem;
  overflow-y: auto;
}

.entity-card__examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
}
</style>
