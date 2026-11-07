<script setup lang="ts">
import { EXAMPLE, exampleFigures, METRICS, ORDER } from '../composables/qualityHelp'

/** How to read the figures of the quality, each in a few simple words, with an example to follow. */
const figures = exampleFigures()
</script>

<template>
  <details class="help" data-testid="quality-help">
    <summary class="help__summary">Comment lire ces chiffres ?</summary>
    <p class="fr-text--sm">
      Ces chiffres ne comparent pas l’analyse à une réponse connue d’avance : ils viennent de <strong>ce que vous décidez</strong> de ses prédictions
      (valider, invalider, corriger, ajouter un élément à la main). Plus il y a de décisions, plus ils sont fiables.
    </p>
    <dl class="help__terms">
      <div v-for="key in ORDER" :key="key" class="help__term" :data-testid="`help-${key}`">
        <dt>{{ METRICS[key].term }} <span class="help__question">— {{ METRICS[key].question }}</span></dt>
        <dd>{{ METRICS[key].text }}</dd>
      </div>
    </dl>
    <p class="help__example fr-text--sm fr-mb-0" data-testid="help-example">
      <strong>Un exemple.</strong> L’analyse propose {{ EXAMPLE.proposed }} éléments. Vous en validez {{ EXAMPLE.validated }} et en invalidez {{ EXAMPLE.invalidated }} ;
      vous en ajoutez {{ EXAMPLE.added }} à la main, qu’elle n’avait pas vus. La précision est de {{ EXAMPLE.validated }} ÷ {{ EXAMPLE.validated + EXAMPLE.invalidated }} = {{ figures.precision }},
      le rappel de {{ EXAMPLE.validated }} ÷ {{ EXAMPLE.validated + EXAMPLE.added }} = {{ figures.recall }}, et le F1 de {{ figures.f1 }}.
    </p>
  </details>
</template>

<style scoped>
.help {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-alt-grey);
}

.help__summary {
  font-weight: 700;
  cursor: pointer;
}

.help__terms {
  display: grid;
  gap: 0.5rem;
  margin: 0 0 0.75rem;
}

.help__term dt {
  font-weight: 700;
}

.help__question {
  font-weight: 400;
  color: var(--text-mention-grey);
}

.help__term dd {
  margin: 0.125rem 0 0;
  font-size: 0.875rem;
}
</style>
