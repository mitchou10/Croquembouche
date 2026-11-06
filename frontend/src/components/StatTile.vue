<script setup lang="ts">
/**
 * One figure of a dashboard, with what it counts. `tone` colours it when it says something good or bad. A `selectable`
 * one is a button that says it was chosen (`select`): `selected` is whether its choice is on, as a toggle.
 */
const props = withDefaults(
  defineProps<{ value: number | string; label: string; tone?: 'success' | 'error' | 'info'; compact?: boolean; selectable?: boolean; selected?: boolean }>(),
  // Not given is not « off »: a button with no choice to make is not a toggle.
  { selected: undefined },
)
const emit = defineEmits<{ select: [] }>()
</script>

<template>
  <component
    :is="selectable ? 'button' : 'div'"
    class="stat"
    :class="[tone && `stat--${tone}`, { 'stat--compact': compact, 'stat--selectable': selectable, 'stat--selected': selected }]"
    :type="selectable ? 'button' : undefined"
    :aria-pressed="selectable && props.selected !== undefined ? selected : undefined"
    data-testid="stat"
    @click="selectable && emit('select')"
  >
    <span class="stat__value" data-testid="stat-value">{{ value }}</span>
    <span class="stat__label" data-testid="stat-label">{{ label }}</span>
  </component>
</template>

<style scoped>
.stat {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
  border-left-width: 4px;
  border-left-color: var(--border-action-high-blue-france);
  background: var(--background-default-grey);
}

.stat {
  display: block;
  width: 100%;
  text-align: left;
}

.stat--selectable {
  cursor: pointer;
  font: inherit;
}

.stat--selectable:hover {
  background: var(--background-default-grey-hover);
}

.stat--selected {
  background: var(--background-contrast-info);
  box-shadow: inset 0 0 0 2px var(--border-action-high-blue-france);
}

.stat--success {
  border-left-color: var(--border-plain-success);
}

.stat--error {
  border-left-color: var(--border-plain-error);
}

.stat--info {
  border-left-color: var(--border-plain-info);
}

.stat__value,
.stat__label {
  display: block;
}

.stat__value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 2rem;
  font-variant-numeric: tabular-nums;
}

.stat--compact {
  padding: 0.375rem 0.75rem;
}

.stat--compact .stat__value {
  font-size: 1.25rem;
  line-height: 1.5rem;
}

.stat--compact .stat__label {
  font-size: 0.8125rem;
}

.stat__label {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}
</style>
