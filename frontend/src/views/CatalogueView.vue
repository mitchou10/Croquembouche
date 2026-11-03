<script setup lang="ts">
import { computed, ref } from 'vue'
import FixedPage from '../components/FixedPage.vue'
import ListTile from '../components/ListTile.vue'
import PagedList from '../components/PagedList.vue'
import { useCatalogue } from '../composables/useCatalogue'

const { filter, pendingSuggestions, canDecide } = useCatalogue()

const query = ref('')
// All the models, or only the signed-in user's own.
const mine = ref(false)
const results = computed(() => filter(query.value, mine.value))
</script>

<template>
  <FixedPage>
    <template #header>
      <h1 class="catalogue__title fr-h3 fr-mb-0">Catalogue</h1>
      <div class="catalogue__search">
        <DsfrInput v-model="query" label="Rechercher un modèle" placeholder="Rechercher un modèle" type="search" />
      </div>
      <div class="catalogue__scope" role="group" aria-label="Afficher">
        <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--tertiary': mine }" :aria-pressed="!mine" @click="mine = false">
          Tous
        </button>
        <button type="button" class="fr-btn fr-btn--sm" :class="{ 'fr-btn--tertiary': !mine }" :aria-pressed="mine" @click="mine = true">
          Mes modèles
        </button>
      </div>
      <RouterLink class="fr-btn fr-icon-add-line fr-btn--icon-left" :to="{ name: 'catalogue-new' }">Nouveau modèle</RouterLink>
    </template>

    <PagedList :items="results" :item-key="(t) => t.id" noun="modèle" :reset-key="`${query}|${mine}`">
      <template #empty>
        <p v-if="mine && !query.trim()" role="status">Vous n’avez pas encore de modèle. Créez-en un avec « Nouveau modèle ».</p>
        <p v-else role="status">Aucun modèle ne correspond à « {{ query }} ».</p>
      </template>
      <template #item="{ item: template }">
        <ListTile :title="template.name" :description="template.description" :to="{ name: 'catalogue-detail', params: { id: template.id } }">
          <template v-if="template.categories.length" #tags>
            <DsfrTag v-for="category in template.categories" :key="category" :label="category" small />
          </template>
          <template #foot>
            <span class="tile__stars">
              <span class="fr-icon-star-fill fr-icon--sm" aria-hidden="true" />
              <span :aria-label="`${template.stars.length} favori${template.stars.length > 1 ? 's' : ''}`">{{ template.stars.length }}</span>
            </span>
            <DsfrBadge
              v-if="canDecide(template) && pendingSuggestions(template).length"
              :label="`${pendingSuggestions(template).length} suggestion${pendingSuggestions(template).length > 1 ? 's' : ''}`"
              type="new"
              small
            />
            <span class="tile__owner">Par {{ template.ownerId }}</span>
          </template>
        </ListTile>
      </template>
    </PagedList>
  </FixedPage>
</template>

<style scoped>
.catalogue__title {
  margin-right: auto;
}

.catalogue__search {
  flex: 1 1 12rem;
  max-width: 22rem;
}

.tile__stars {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.tile__owner {
  margin-left: auto;
  overflow: hidden;
  color: var(--text-mention-grey);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.catalogue__scope {
  display: flex;
  gap: 0.25rem;
}
</style>
