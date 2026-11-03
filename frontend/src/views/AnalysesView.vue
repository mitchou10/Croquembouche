<script setup lang="ts">
import FixedPage from '../components/FixedPage.vue'
import ListTile from '../components/ListTile.vue'
import PagedList from '../components/PagedList.vue'
import { useAnalyses } from '../composables/useAnalyses'
import { useCatalogue } from '../composables/useCatalogue'
import { describeShares } from '../composables/shares'
import { statusLabels, type Analysis } from '../data/mock'

const { analyses, canAccess } = useAnalyses()
const { templateName } = useCatalogue()

// What the card says about the analysis: what it is for, or else which models it looks for.
const summary = (a: Analysis) =>
  canAccess(a) ? a.description || a.templateIds.map(templateName).join(', ') : 'Vous n’avez pas accès à cette analyse.'
const sharing = (a: Analysis) =>
  a.isPublic ? { label: 'Publique', title: 'Visible par tous les utilisateurs' } : a.shares.length ? { label: `Partagée · ${a.shares.length}`, title: `Partagée avec ${describeShares(a.shares)} : ${a.shares.map((s) => s.value).join(', ')}` } : null
</script>

<template>
  <FixedPage>
    <template #header>
      <div class="analyses__title">
        <h1 class="fr-h3 fr-mb-0">Analyses</h1>
        <p class="fr-mb-0">Les recherches lancées sur vos documents.</p>
      </div>
      <RouterLink class="fr-btn fr-icon-add-line fr-btn--icon-left" :to="{ name: 'analysis-new' }">Nouvelle analyse</RouterLink>
    </template>

    <PagedList :items="analyses" :item-key="(a) => a.id" noun="analyse" suffix=" au total">
      <template #empty>
        <p role="status">Aucune analyse pour l’instant.</p>
      </template>
      <template #item="{ item: analysis }">
        <!-- One can open the analyses one has access to; the others are named, and say so. -->
        <ListTile
          :title="analysis.name"
          :description="summary(analysis)"
          :to="canAccess(analysis) ? { name: 'analysis-detail', params: { id: analysis.id } } : undefined"
        >
          <template #tags>
            <DsfrBadge :label="statusLabels[analysis.status].label" :type="statusLabels[analysis.status].type" small />
            <DsfrTag v-if="!canAccess(analysis)" label="Accès restreint" small data-testid="restricted" />
            <DsfrTag v-else-if="sharing(analysis)" :label="sharing(analysis)!.label" :title="sharing(analysis)!.title" small data-testid="sharing" />
          </template>
          <template #foot>
            <span class="analysis__details">
              {{ analysis.date }}<template v-if="canAccess(analysis)"> · {{ analysis.matches }} correspondance{{ analysis.matches > 1 ? 's' : '' }}</template>
            </span>
          </template>
        </ListTile>
      </template>
    </PagedList>
  </FixedPage>
</template>

<style scoped>
.analyses__title {
  margin-right: auto;
}

.analysis__details {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}
</style>
