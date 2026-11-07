<script setup lang="ts">
import { computed } from 'vue'
import {
  co2Equivalent,
  electricityEquivalent,
  formatCo2,
  formatDuration,
  formatEnergy,
  formatWater,
  gaugeLevel,
  waterEquivalent,
} from '../composables/consumption'
import type { Consumption } from '../data/mock'
import ConsumptionGauge from './ConsumptionGauge.vue'

/** What computing something consumed: the electricity, the CO2 it made and the water it cost, each with what that is like. */
const props = defineProps<{ consumption: Consumption; heading: string; compact?: boolean }>()

const items = computed(() => [
  { key: 'energy' as const, label: 'Électricité', value: formatEnergy(props.consumption.energyWh), like: electricityEquivalent(props.consumption.energyWh), level: gaugeLevel('energy', props.consumption.energyWh) },
  { key: 'co2' as const, label: 'CO₂', value: formatCo2(props.consumption.co2G), like: co2Equivalent(props.consumption.co2G), level: gaugeLevel('co2', props.consumption.co2G) },
  { key: 'water' as const, label: 'Eau', value: formatWater(props.consumption.waterMl), like: waterEquivalent(props.consumption.waterMl), level: gaugeLevel('water', props.consumption.waterMl) },
])
</script>

<template>
  <section class="consumption" :class="{ 'consumption--compact': compact }" :aria-label="heading" data-testid="consumption">
    <p class="consumption__heading fr-text--sm fr-mb-0">
      {{ heading }}<span v-if="consumption.durationS > 0" class="consumption__time"> · calcul de {{ formatDuration(consumption.durationS) }}</span>
    </p>
    <ul class="consumption__items">
      <li v-for="item in items" :key="item.key" class="consumption__item" :data-testid="`consumption-${item.key}`">
        <ConsumptionGauge
          :kind="item.key"
          :level="item.level"
          :size="compact ? 24 : 34"
          class="consumption__gauge"
          title="Remplissage indicatif, sur une échelle logarithmique : plein, c’est un muffin cuit, un kilomètre en voiture ou une bouteille d’eau."
        />
        <span class="consumption__label">{{ item.label }}</span>
        <strong class="consumption__value" data-testid="consumption-value">{{ item.value }}</strong>
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
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: 0.625rem;
  row-gap: 0.125rem;
  align-items: start;
  min-width: 0;
}

.consumption__gauge {
  grid-row: 1 / span 3;
  align-self: center;
}

.consumption__item > :not(.consumption__gauge) {
  grid-column: 2;
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
