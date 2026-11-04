<script setup lang="ts">
import { computed } from 'vue'
import type { Detection } from '../composables/useAnalyses'

/** One element an analysis found: what it is most likely, and every class it could be with how sure the analysis is. */
const props = defineProps<{
  detection: Detection
  /** Its place among the elements found, from 1. */
  position?: number
  /** What it is called, when it is not « Élément n »: the page, for instance. */
  title?: string
  /** The name of a class: a model's, or « other » for null. */
  nameOf: (templateId: string | null, templatePage?: number | null) => string
}>()

/** The most classes shown: the likeliest ones, the rest being too unlikely to be worth a line. */
const SHOWN = 4

const percent = (confidence: number) => Math.round(confidence * 100)
const best = computed(() => props.detection.classifications[0])
const shown = computed(() => props.detection.classifications.slice(0, SHOWN))
const hidden = computed(() => props.detection.classifications.length - shown.value.length)
</script>

<template>
  <div class="detection" data-testid="detection">
    <div class="detection__head">
      <h3 class="fr-h6 fr-mb-0">{{ title ?? `Élément ${position}` }}</h3>
      <DsfrBadge :label="nameOf(best.templateId, best.templatePage)" :type="best.templateId === null ? 'warning' : 'success'" small data-testid="detection-best" />
      <span class="detection__confidence" data-testid="detection-confidence">{{ percent(best.confidence) }} %</span>
    </div>

    <p class="fr-text--sm fr-mb-0">Classes possibles, de la plus à la moins probable :</p>
    <ul class="classes">
      <li v-for="(c, index) in shown" :key="`${c.templateId ?? 'other'}#${c.templatePage ?? 0}`" class="classes__row" :class="{ 'classes__row--best': index === 0 }" data-testid="classification">
        <span class="classes__name" :title="nameOf(c.templateId, c.templatePage)">
          {{ nameOf(c.templateId, c.templatePage) }}<template v-if="c.templateVersion"> · v{{ c.templateVersion }}</template>
        </span>
        <span
          class="classes__bar"
          role="meter"
          :aria-label="`${nameOf(c.templateId, c.templatePage)} : ${percent(c.confidence)} %`"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="percent(c.confidence)"
        >
          <span class="classes__fill" :style="{ width: `${percent(c.confidence)}%` }" />
        </span>
        <span class="classes__percent">{{ percent(c.confidence) }} %</span>
      </li>
    </ul>
    <p v-if="hidden > 0" class="fr-hint-text fr-mb-0" data-testid="classifications-hidden">
      + {{ hidden }} autre{{ hidden > 1 ? 's' : '' }} classe{{ hidden > 1 ? 's' : '' }} encore moins probable{{ hidden > 1 ? 's' : '' }}
    </p>
    <slot />
  </div>
</template>

<style scoped>
.detection {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
}

.detection__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.detection__confidence {
  margin-left: auto;
  font-size: 1.25rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.classes {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.classes__row {
  display: grid;
  grid-template-columns: minmax(9rem, 1.6fr) minmax(3rem, 1fr) 2.75rem;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
}

.classes__row--best {
  font-weight: 700;
}

.classes__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.classes__bar {
  display: block;
  height: 0.5rem;
  background: var(--background-contrast-grey);
}

.classes__fill {
  display: block;
  height: 100%;
  background: var(--background-action-low-blue-france);
}

.classes__row--best .classes__fill {
  background: var(--background-action-high-blue-france);
}

.classes__percent {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
