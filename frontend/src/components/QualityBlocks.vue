<script setup lang="ts">
import { computed } from 'vue'
import type { Quality } from '../data/mock'

/** The figures of a quality: precision, recall, F1, what was right, wrong, missed and still to be decided. */
const props = defineProps<{ pages: Quality & { exact: number | null }; elements: Quality }>()

const percent = (value: number | null) => (value === null ? '—' : `${Math.round(value * 100)} %`)

interface Block {
  id: string
  title: string
  quality: Quality
  extra?: { label: string; value: string }
}
const blocks = computed<Block[]>(() => [
  { id: 'pages', title: 'Classification des pages', quality: props.pages, extra: { label: 'Page du modèle exacte', value: percent(props.pages.exact) } },
  { id: 'elements', title: 'Éléments trouvés', quality: props.elements },
])
</script>

<template>
  <section v-for="block in blocks" :key="block.id" class="block" :aria-labelledby="`quality-${block.id}`" :data-testid="`quality-${block.id}`">
    <h3 :id="`quality-${block.id}`" class="fr-h6 fr-mb-0">{{ block.title }}</h3>
    <dl class="block__figures">
      <div><dt>Précision</dt><dd data-testid="precision">{{ percent(block.quality.precision) }}</dd></div>
      <div><dt>Rappel</dt><dd data-testid="recall">{{ percent(block.quality.recall) }}</dd></div>
      <div><dt>F1</dt><dd data-testid="f1">{{ percent(block.quality.f1) }}</dd></div>
      <div v-if="block.extra"><dt>{{ block.extra.label }}</dt><dd data-testid="exact">{{ block.extra.value }}</dd></div>
    </dl>
    <p class="fr-mb-0" data-testid="counts">
      {{ block.quality.correct }} juste{{ block.quality.correct > 1 ? 's' : '' }} ·
      {{ block.quality.wrong }} fausse{{ block.quality.wrong > 1 ? 's' : '' }} ·
      {{ block.quality.missed }} manquée{{ block.quality.missed > 1 ? 's' : '' }} ·
      {{ block.quality.pending }} en attente
    </p>
    <p v-if="block.quality.meanConfidenceCorrect !== null || block.quality.meanConfidenceWrong !== null" class="fr-hint-text fr-mb-0" data-testid="confidence">
      Confiance moyenne : {{ percent(block.quality.meanConfidenceCorrect) }} quand c’était juste, {{ percent(block.quality.meanConfidenceWrong) }} quand c’était faux.
    </p>
  </section>
</template>

<style scoped>
.block {
  display: grid;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem 0.625rem;
  border: 1px solid var(--border-default-grey);
}

.block__figures {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  margin: 0;
}

.block__figures dt {
  font-size: 0.75rem;
  color: var(--text-mention-grey);
}

.block__figures dd {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
}
</style>
