<script setup lang="ts">
import { computed, ref } from 'vue'
import { statusLabels, type AnalysisRun } from '../data/mock'
import PagerControls from './PagerControls.vue'

/**
 * The uses of an analysis, newest first, a few at a time. What a use found is private to the person who ran it: for that
 * person the row has a button to see it, for anyone else (an administrator too) it says the result is private.
 */
const props = defineProps<{
  runs: AnalysisRun[]
  /** Whether the result of a use can be opened by the person looking. */
  canSee: (run: AnalysisRun) => boolean
  selectedId?: string | null
}>()
const emit = defineEmits<{ open: [runId: string] }>()

const PER_PAGE = 4
const page = ref(0)
const pageCount = computed(() => Math.max(1, Math.ceil(props.runs.length / PER_PAGE)))
const visible = computed(() => props.runs.slice(page.value * PER_PAGE, (page.value + 1) * PER_PAGE))
</script>

<template>
  <p v-if="!runs.length" role="status">Cette analyse n’a pas encore été utilisée.</p>
  <div v-else class="runs">
    <ul class="runs__list">
      <li v-for="run in visible" :key="run.id" class="runs__row" :class="{ 'runs__row--selected': run.id === selectedId }" data-testid="run">
        <span class="runs__date">{{ run.date }}</span>
        <span class="runs__user">{{ run.userId }}</span>
        <DsfrBadge :label="statusLabels[run.status].label" :type="statusLabels[run.status].type" small />
        <span class="runs__matches">{{ run.matches }} correspondance{{ run.matches > 1 ? 's' : '' }}</span>
        <template v-if="run.detections">
          <button
            v-if="canSee(run)"
            type="button"
            class="fr-btn fr-btn--sm fr-btn--secondary"
            :aria-pressed="run.id === selectedId"
            data-testid="run-open"
            @click="emit('open', run.id)"
          >
            Voir le résultat<span class="fr-sr-only"> du {{ run.date }}</span>
          </button>
          <span v-else class="runs__private" data-testid="run-private" title="Seule la personne qui a lancé l’analyse voit son résultat">Résultat privé</span>
        </template>
      </li>
    </ul>
    <PagerControls v-if="pageCount > 1" v-model="page" :count="pageCount" noun="Page" />
  </div>
</template>

<style scoped>
.runs {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.runs__list {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.runs__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  padding: 0.375rem 0.5rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.runs__row--selected {
  background: var(--background-contrast-info);
}

.runs__date {
  font-variant-numeric: tabular-nums;
}

.runs__user {
  font-weight: 700;
}

.runs__matches {
  margin-left: auto;
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.runs__private {
  color: var(--text-mention-grey);
  font-size: 0.8125rem;
  font-style: italic;
}
</style>
