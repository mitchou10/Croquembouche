<script setup lang="ts">
/** One figure of a dashboard, with what it counts. `tone` colours it when it says something good or bad. */
defineProps<{ value: number | string; label: string; tone?: 'success' | 'error' | 'info'; compact?: boolean }>()
</script>

<template>
  <div class="stat" :class="[tone && `stat--${tone}`, { 'stat--compact': compact }]" data-testid="stat">
    <p class="stat__value fr-mb-0" data-testid="stat-value">{{ value }}</p>
    <p class="stat__label fr-mb-0" data-testid="stat-label">{{ label }}</p>
  </div>
</template>

<style scoped>
.stat {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-default-grey);
  border-left-width: 4px;
  border-left-color: var(--border-action-high-blue-france);
  background: var(--background-default-grey);
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
