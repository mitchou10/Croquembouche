<script setup lang="ts">
import { computed, useId } from 'vue'
import type { GaugeShape } from '../composables/consumption'

/**
 * One thing that fills as much as what it stands for: a light bulb, a balloon of gas, a teaspoon, a glass, a bottle, a bucket
 * or a bath. It
 * fills when it appears (each one a little after the one before), and moves a little after (a wave, bubbles, a glow)
 * unless the person asked for less motion.
 */
const props = defineProps<{ shape: GaugeShape; level: number; width?: number; index?: number }>()

const id = useId()
const level = computed(() => Math.min(1, Math.max(0, props.level)))

// The outline of each drawing, on a 40 x 64 board, and what can be filled in it: from its top (full) to its bottom (empty).
const outlines: Record<GaugeShape, string> = {
  bottle: 'M14 3h12v8c0 4 8 6 8 14v34a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4V25c0-8 8-10 8-14z',
  glass: 'M7 8h26l-3 51a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4z',
  spoon: 'M20 4c-8 0-12 7-12 14s5 11 12 11 12-4 12-11S28 4 20 4z',
  bulb: 'M20 3a16 16 0 0 0-9 29c2 2 3 4 3 7v3h12v-3c0-3 1-5 3-7A16 16 0 0 0 20 3z',
  balloon: 'M20 4c11 0 17 8 17 18 0 11-8 20-17 20S3 33 3 22C3 12 9 4 20 4z',
  bucket: 'M7 22h26l-3 36a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4z',
  bath: 'M3 30h34v8a14 14 0 0 1-14 14H17A14 14 0 0 1 3 38z',
}
const inside: Record<GaugeShape, [number, number]> = {
  bottle: [5, 63],
  glass: [9, 62],
  spoon: [5, 29],
  bulb: [5, 40],
  balloon: [5, 41],
  bucket: [23, 61],
  bath: [32, 51],
}
const style = computed(() => ({
  '--level': String(level.value),
  '--top': String(inside[props.shape][0]),
  '--bottom': String(inside[props.shape][1]),
  '--delay': `${(props.index ?? 0) * 0.14}s`,
}))
const waves = computed(() => ['bottle', 'glass', 'bucket', 'bath'].includes(props.shape))
const size = computed(() => props.width ?? 22)
</script>

<template>
  <span class="gauge" :class="`gauge--${shape}`" :style="style" :data-level="level" data-testid="gauge" aria-hidden="true">
    <svg :width="size" :height="(size * 64) / 40" viewBox="0 0 40 64" focusable="false">
      <defs>
        <clipPath :id="`${id}-clip`"><path :d="outlines[shape]" /></clipPath>
      </defs>
      <g :clip-path="`url(#${id}-clip)`">
        <rect class="gauge__empty" x="0" y="0" width="40" height="64" />
        <g class="gauge__fill" data-testid="gauge-fill">
          <rect class="gauge__liquid" x="-10" y="0" width="60" height="70" />
          <path v-if="waves" class="gauge__wave" d="M-20 0q5-3 10 0t10 0 10 0 10 0 10 0 10 0 10 0 10 0v6h-80z" />
          <template v-if="shape === 'balloon'">
            <circle class="gauge__bubble gauge__bubble--1" cx="12" cy="40" r="2" />
            <circle class="gauge__bubble gauge__bubble--2" cx="22" cy="44" r="1.5" />
            <circle class="gauge__bubble gauge__bubble--3" cx="29" cy="38" r="2.5" />
          </template>
        </g>
      </g>
      <path class="gauge__outline" :d="outlines[shape]" />
      <path v-if="shape === 'spoon'" class="gauge__outline gauge__handle" d="M18.5 29h3l-.8 33h-1.4z" />
      <path v-if="shape === 'bulb'" class="gauge__outline" d="M14 46h12M15 50h10M17 54h6" />
      <path v-if="shape === 'balloon'" class="gauge__outline" d="M17 42l3 5 3-5z" />
      <path v-if="shape === 'bucket'" class="gauge__outline" d="M10 22c0-12 20-12 20 0" />
      <path v-if="shape === 'bath'" class="gauge__outline" d="M8 52l-2 6M32 52l2 6M30 30V16c0-4-6-4-6 0" />
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
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.gauge__handle {
  fill: var(--text-mention-grey, #666);
}

.gauge__liquid,
.gauge__wave {
  fill: var(--water);
}

.gauge--bulb .gauge__liquid {
  fill: var(--light);
}

.gauge--balloon .gauge__liquid {
  fill: var(--gas);
}

.gauge__bubble {
  fill: #fff;
  opacity: 0.7;
}

/* Where the fill rests: its top at the level of the thing. It starts empty (at the bottom of the inside) and rises. */
.gauge__fill {
  transform: translateY(calc((var(--bottom) - var(--level) * (var(--bottom) - var(--top))) * 1px));
  animation: gauge-rise 1.6s cubic-bezier(0.4, 0, 0.2, 1) var(--delay) both;
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

.gauge--bulb {
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
  .gauge--bulb {
    animation: none;
  }
}
</style>
