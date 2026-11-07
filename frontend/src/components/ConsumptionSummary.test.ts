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
    expect(text('energy')).toMatch(/ampoules? LED/)
    expect(text('co2')).toContain('0,12 g')
    expect(text('co2')).toContain('en voiture')
    expect(text('water')).toContain('600 mL')
    expect(text('water')).toContain('3 verres d’eau')
  })

  it('does not say a time it does not know', () => {
    const wrapper = mount(ConsumptionSummary, { props: { consumption: { ...consumption, durationS: 0 }, heading: 'Total' } })
    expect(wrapper.text()).not.toContain('calcul de')
  })
})

describe('ConsumptionSummary things that fill', () => {
  const mounted = (props: { energyWh: number; co2G: number; waterMl: number }) =>
    mount(ConsumptionSummary, { props: { consumption: { durationS: 1, ...props }, heading: 'Total' } })
  const things = (wrapper: ReturnType<typeof mounted>, key: string) =>
    wrapper.get(`[data-testid="consumption-${key}"]`).findAll('[data-testid="gauge"]').map((g) => Number(g.attributes('data-level')))
  const said = (wrapper: ReturnType<typeof mounted>, key: string) =>
    wrapper.get(`[data-testid="consumption-${key}"] [data-testid="consumption-units"]`).text().replace(/[  ]/g, ' ')

  it('counts the water in bottles of a litre, the whole ones full and the last one as full as what is left', () => {
    const wrapper = mounted({ energyWh: 1, co2G: 1, waterMl: 3400 })
    expect(things(wrapper, 'water')).toEqual([1, 1, 1, 0.4])
    expect(said(wrapper, 'water')).toBe('≈ 3,4 bouteilles d’1 L')
  })

  it('counts a small quantity in a smaller thing: spoons, then glasses, then bottles', () => {
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 9 }), 'water')).toBe('≈ 1,8 cuillère à café')
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 600 }), 'water')).toBe('≈ 3 verres d’eau')
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 1500 }), 'water')).toBe('≈ 7,5 verres d’eau')
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 2300 }), 'water')).toBe('≈ 2,3 bouteilles d’1 L')
  })

  it('counts the electricity in LED bulbs lit for a minute, an hour, a day', () => {
    expect(said(mounted({ energyWh: 0.4, co2G: 1, waterMl: 1 }), 'energy')).toContain('ampoules LED allumées 1 minute')
    expect(said(mounted({ energyWh: 5, co2G: 1, waterMl: 1 }), 'energy')).toBe('≈ 0,5 ampoule LED allumée 1 heure')
    expect(said(mounted({ energyWh: 480, co2G: 1, waterMl: 1 }), 'energy')).toBe('≈ 2 ampoules LED allumées 1 jour')
  })

  it('counts the CO2 in balloons of gas, and still says what it is in a car', () => {
    const wrapper = mounted({ energyWh: 1, co2G: 5.52, waterMl: 1 })
    expect(things(wrapper, 'co2')).toEqual([1, 1, 1])
    expect(said(wrapper, 'co2')).toBe('≈ 3 ballons de 1 L de CO₂')
    expect(wrapper.get('[data-testid="consumption-co2"]').text()).toContain('en voiture')
  })

  it('never shows a hundred bottles: a bucket, a bath, and past that « plus de 10 »', () => {
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 70_000 }), 'water')).toBe('≈ 7 seaux de 10 L')
    expect(said(mounted({ energyWh: 1, co2G: 1, waterMl: 300_000 }), 'water')).toBe('≈ 2 baignoires')
    const wrapper = mounted({ energyWh: 1, co2G: 1, waterMl: 5_000_000 })
    expect(things(wrapper, 'water')).toEqual(Array(10).fill(1))
    expect(said(wrapper, 'water')).toBe('≈ plus de 10 baignoires')
  })

  it('is hidden from assistive technologies, the figures say the same', () => {
    const wrapper = mounted({ energyWh: 1, co2G: 1, waterMl: 1 })
    expect(wrapper.get('[data-testid="consumption-things"]').attributes('aria-hidden')).toBe('true')
  })
})
