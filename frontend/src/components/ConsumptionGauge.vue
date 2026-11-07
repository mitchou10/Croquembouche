<script setup lang="ts">
import { computed, useId } from 'vue'
import type { GaugeKind } from '../composables/consumption'

/**
 * A thing that fills as much as what was consumed: a light bulb for the electricity, a balloon of gas for the CO2, a
 * bottle for the water. It fills when it appears, and moves a little after (a wave, bubbles, a glow) unless the person
 * asked for less motion.
 */
const props = defineProps<{ kind: GaugeKind; level: number; size?: number }>()

const id = useId()
const HEIGHT = 64
const level = computed(() => Math.min(1, Math.max(0, props.level)))
// What can be filled in each drawing, as the heights of its inside: full is its top, empty its bottom (the base of a
// bulb is not filled, nor the air above a balloon).
const inside = { water: [5, 63], energy: [5, 40], co2: [5, 41] } as const
const style = computed(() => ({
  '--level': String(level.value),
  '--top': String(inside[props.kind][0]),
  '--bottom': String(inside[props.kind][1]),
}))

const outlines: Record<GaugeKind, string> = {
  water: 'M14 3h12v8c0 4 8 6 8 14v34a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4V25c0-8 8-10 8-14z',
  energy: 'M20 3a16 16 0 0 0-9 29c2 2 3 4 3 7v3h12v-3c0-3 1-5 3-7A16 16 0 0 0 20 3z',
  co2: 'M20 4c11 0 17 8 17 18 0 11-8 20-17 20S3 33 3 22C3 12 9 4 20 4z',
}
</script>

<template>
  <span class="gauge" :class="`gauge--${kind}`" :style="style" :data-level="level" data-testid="gauge" aria-hidden="true">
    <svg :width="size ?? 40" :height="((size ?? 40) * HEIGHT) / 40" viewBox="0 0 40 64" focusable="false">
      <defs>
        <clipPath :id="`${id}-clip`"><path :d="outlines[kind]" /></clipPath>
      </defs>
      <g :clip-path="`url(#${id}-clip)`">
        <rect class="gauge__empty" x="0" y="0" width="40" height="64" />
        <g class="gauge__fill" data-testid="gauge-fill">
          <rect class="gauge__liquid" x="-10" y="0" width="60" height="70" />
          <path v-if="kind === 'water'" class="gauge__wave" d="M-20 0q5-3 10 0t10 0 10 0 10 0 10 0 10 0 10 0 10 0v6h-80z" />
          <template v-if="kind === 'co2'">
            <circle class="gauge__bubble gauge__bubble--1" cx="12" cy="40" r="2" />
            <circle class="gauge__bubble gauge__bubble--2" cx="22" cy="44" r="1.5" />
            <circle class="gauge__bubble gauge__bubble--3" cx="29" cy="38" r="2.5" />
          </template>
        </g>
      </g>
      <path class="gauge__outline" :d="outlines[kind]" />
      <template v-if="kind === 'energy'">
        <path class="gauge__outline" d="M14 46h12M15 50h10M17 54h6" />
      </template>
      <template v-if="kind === 'co2'">
        <path class="gauge__outline" d="M17 42l3 4 3-4z" />
        <text class="gauge__text" x="20" y="27" text-anchor="middle">CO₂</text>
      </template>
    </svg>
  </span>
</template>

<style scoped>
.gauge {
  --water: #417dc4;
  --light: #f5c518;
  --gas: #7c8594;
  display: inline-block;
  flex-shrink: 0;
  line-height: 0;
}

.gauge__empty {
  fill: var(--background-alt-grey, #f6f6f6);
}

.gauge__outline {
  fill: none;
  stroke: var(--text-mention-grey, #666);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.gauge__text {
  fill: var(--text-default-grey, #161616);
  font: 700 9px sans-serif;
}

.gauge__liquid,
.gauge__wave {
  fill: var(--water);
}

.gauge--energy .gauge__liquid {
  fill: var(--light);
}

.gauge--co2 .gauge__liquid {
  fill: var(--gas);
}

.gauge__bubble {
  fill: #fff;
  opacity: 0.7;
}

/* Where the fill rests: its top at the level of the gauge. It starts empty (at the bottom of the inside) and rises. */
.gauge__fill {
  transform: translateY(calc((var(--bottom) - var(--level) * (var(--bottom) - var(--top))) * 1px));
  animation: gauge-rise 1.8s cubic-bezier(0.4, 0, 0.2, 1) both;
}

@keyframes gauge-rise {
  from {
    transform: translateY(calc(var(--bottom) * 1px));
  }
}

.gauge__wave {
  animation: gauge-wave 2.4s linear infinite;
}

@keyframes gauge-wave {
  to {
    transform: translateX(20px);
  }
}

.gauge__bubble {
  animation: gauge-bubble 3s ease-in infinite;
}

.gauge__bubble--2 {
  animation-delay: 1s;
}

.gauge__bubble--3 {
  animation-delay: 2s;
}

@keyframes gauge-bubble {
  from {
    transform: translateY(0);
    opacity: 0.7;
  }
  to {
    transform: translateY(-26px);
    opacity: 0;
  }
}

.gauge--energy {
  filter: drop-shadow(0 0 calc(var(--level) * 5px) var(--light));
  animation: gauge-glow 2.4s ease-in-out infinite alternate;
}

@keyframes gauge-glow {
  from {
    filter: drop-shadow(0 0 calc(var(--level) * 2px) var(--light));
  }
  to {
    filter: drop-shadow(0 0 calc(var(--level) * 6px) var(--light));
  }
}

@media (prefers-reduced-motion: reduce) {
  .gauge__fill,
  .gauge__wave,
  .gauge__bubble,
  .gauge--energy {
    animation: none;
  }
}
</style>
