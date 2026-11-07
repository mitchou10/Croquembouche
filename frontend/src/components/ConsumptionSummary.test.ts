import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConsumptionSummary from './ConsumptionSummary.vue'

const consumption = { durationS: 3.2, energyWh: 2.4, co2G: 0.12, waterMl: 600 }

describe('ConsumptionSummary', () => {
  it('says the electricity, the CO2 and the water, each with what it is like, and how long it took', () => {
    const wrapper = mount(ConsumptionSummary, { props: { consumption, heading: 'Cette analyse a consommé' } })
    const text = (key: string) => wrapper.get(`[data-testid="consumption-${key}"]`).text().replace(/[  ]/g, ' ')
    expect(wrapper.text()).toContain('Cette analyse a consommé')
    expect(wrapper.text()).toContain('calcul de 3,2 s')
    expect(text('energy')).toContain('2,4 Wh')
    expect(text('energy')).toContain('ampoule LED')
    expect(text('co2')).toContain('0,12 g')
    expect(text('co2')).toContain('en voiture')
    expect(text('water')).toContain('600 mL')
    expect(text('water')).toContain('1,2 bouteille')
  })

  it('does not say a time it does not know', () => {
    const wrapper = mount(ConsumptionSummary, { props: { consumption: { ...consumption, durationS: 0 }, heading: 'Total' } })
    expect(wrapper.text()).not.toContain('calcul de')
  })
})

describe('ConsumptionSummary gauges', () => {
  const levels = (props: { energyWh: number; co2G: number; waterMl: number }) =>
    mount(ConsumptionSummary, { props: { consumption: { durationS: 1, ...props }, heading: 'Total' } })
      .findAll('[data-testid="gauge"]')
      .map((g) => Number(g.attributes('data-level')))

  it('has a gauge for the electricity, the CO2 and the water, filled as much as each was consumed', () => {
    const [energy, co2, water] = levels({ energyWh: 2.4, co2G: 0.12, waterMl: 250 })
    expect(energy).toBeGreaterThan(0)
    expect(energy).toBeLessThan(1)
    expect(co2).toBeGreaterThan(0)
    expect(water).toBeGreaterThan(0.5) // half a bottle: past the middle on a logarithmic scale
  })

  it('fills more for more, up to full, whatever the quantity', () => {
    const little = levels({ energyWh: 0.1, co2G: 0.1, waterMl: 1 })
    const much = levels({ energyWh: 5000, co2G: 5000, waterMl: 5000 })
    little.forEach((level, i) => expect(level).toBeLessThan(much[i]))
    expect(much).toEqual([1, 1, 1])
  })

  it('is told to be indicative, and hidden from assistive technologies (the figures say it)', () => {
    const wrapper = mount(ConsumptionSummary, { props: { consumption, heading: 'Total' } })
    const gauge = wrapper.get('[data-testid="gauge"]')
    expect(gauge.attributes('aria-hidden')).toBe('true')
    expect(gauge.attributes('title')).toContain('échelle logarithmique')
  })
})
