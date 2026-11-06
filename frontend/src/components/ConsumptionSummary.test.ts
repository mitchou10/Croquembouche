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
