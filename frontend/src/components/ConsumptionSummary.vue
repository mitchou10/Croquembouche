<script setup lang="ts">
import { computed } from 'vue'
import {
  co2Equivalent,
  formatCo2,
  formatDuration,
  formatEnergy,
  formatWater,
  MAX_SHOWN,
  unitsOf,
} from '../composables/consumption'
import type { Consumption } from '../data/mock'
import ConsumptionGauge from './ConsumptionGauge.vue'

/** What computing something consumed: the electricity, the CO2 it made and the water it cost, each with what that is like. */
const props = defineProps<{ consumption: Consumption; heading: string; compact?: boolean }>()

// Each one in things that fill, which can be counted: bulbs lit, balloons of gas, bottles of water.
const items = computed(() => [
  { key: 'energy' as const, label: 'Électricité', value: formatEnergy(props.consumption.energyWh), units: unitsOf('energy', props.consumption.energyWh), like: '' },
  { key: 'co2' as const, label: 'CO₂', value: formatCo2(props.consumption.co2G), units: unitsOf('co2', props.consumption.co2G), like: co2Equivalent(props.consumption.co2G) },
  { key: 'water' as const, label: 'Eau', value: formatWater(props.consumption.waterMl), units: unitsOf('water', props.consumption.waterMl), like: '' },
])
</script>

<template>
  <section class="consumption" :class="{ 'consumption--compact': compact }" :aria-label="heading" data-testid="consumption">
    <p class="consumption__heading fr-text--sm fr-mb-0">
      {{ heading }}<span v-if="consumption.durationS > 0" class="consumption__time"> · calcul de {{ formatDuration(consumption.durationS) }}</span>
    </p>
    <ul class="consumption__items">
      <li v-for="item in items" :key="item.key" class="consumption__item" :data-testid="`consumption-${item.key}`">
        <span class="consumption__label">{{ item.label }}</span>
        <strong class="consumption__value" data-testid="consumption-value">{{ item.value }}</strong>
        <template v-if="item.units">
          <span class="consumption__things" aria-hidden="true" data-testid="consumption-things">
            <ConsumptionGauge v-for="(level, i) in item.units.levels" :key="i" :shape="item.units.shape" :level="level" :index="i" :width="compact ? 14 : 18" />
            <span v-if="item.units.count >= MAX_SHOWN" class="consumption__more">+</span>
          </span>
          <span class="consumption__like" data-testid="consumption-units">≈ {{ item.units.text }}</span>
        </template>
        <span v-if="item.like" class="consumption__like" data-testid="consumption-like">≈ {{ item.like }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.consumption {
  display: grid;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-left: 4px solid var(--border-plain-success);
  background: var(--background-default-grey);
}

.consumption__heading {
  color: var(--text-mention-grey);
}

.consumption__items {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.5rem 1rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.consumption__item {
  display: grid;
  align-content: start;
  gap: 0.125rem;
  min-width: 0;
}

/* What it is in things that fill: they wrap when there are many. */
.consumption__things {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.25rem;
  padding: 0.125rem 0;
}

.consumption__more {
  color: var(--text-mention-grey);
  line-height: 1;
}

.consumption__label {
  color: var(--text-mention-grey);
  font-size: 0.8125rem;
  line-height: 1.25rem;
}

.consumption__value {
  font-size: 1.25rem;
  line-height: 1.5rem;
  font-variant-numeric: tabular-nums;
}

.consumption__like {
  font-size: 0.8125rem;
}

.consumption--compact .consumption__value {
  font-size: 1rem;
}
</style>
