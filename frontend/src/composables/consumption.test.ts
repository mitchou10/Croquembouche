import { describe, expect, it } from 'vitest'
import {
  co2Equivalent,
  electricityEquivalent,
  figure,
  formatCo2,
  formatDuration,
  formatEnergy,
  formatWater,
  hasConsumption,
  totalConsumption,
  waterEquivalent,
} from './consumption'

const nbsp = (text: string) => text.replace(/[  ]/g, ' ')

describe('figure', () => {
  it('keeps the digits that matter', () => {
    expect([0, 0.0123, 0.45, 2.34, 23.4, 1234.6].map((n) => nbsp(figure(n)))).toEqual(['0', '0,012', '0,45', '2,3', '23', '1 235'])
  })
})

describe('units', () => {
  it('goes up a unit when it is a thousand of the one below', () => {
    expect(nbsp(formatEnergy(2.4))).toBe('2,4 Wh')
    expect(nbsp(formatEnergy(1500))).toBe('1,5 kWh')
    expect(nbsp(formatCo2(0.12))).toBe('0,12 g')
    expect(nbsp(formatCo2(2500))).toBe('2,5 kg')
    expect(nbsp(formatWater(4.3))).toBe('4,3 mL')
    expect(nbsp(formatWater(1800))).toBe('1,8 L')
    expect(formatDuration(3.2)).toBe('3,2 s')
    expect(formatDuration(65)).toBe('1 min 5 s')
  })
})

describe('equivalents', () => {
  it('says a small electricity as the time a LED bulb stays lit, a big one as muffins baked', () => {
    expect(electricityEquivalent(2)).toBe('une ampoule LED allumée 12 min')
    expect(electricityEquivalent(0.05)).toBe('une ampoule LED allumée 18 s')
    expect(electricityEquivalent(140)).toBe('2 muffins cuits au four')
    expect(electricityEquivalent(70)).toBe('1 muffin cuit au four')
    expect(electricityEquivalent(0)).toBe('')
  })

  it('says a little water as teaspoons, half a bottle or more as bottles', () => {
    expect(waterEquivalent(3.6)).toBe('0,72 cuillère à café')
    expect(waterEquivalent(50)).toBe('10 cuillères à café')
    expect(waterEquivalent(250)).toBe('0,5 bouteille d’eau')
    expect(waterEquivalent(1500)).toBe('3 bouteilles d’eau')
  })

  it('says the CO2 as the distance a car drives to make it', () => {
    expect(co2Equivalent(0.1)).toBe('0,5 m en voiture')
    expect(nbsp(co2Equivalent(400))).toBe('2 km en voiture')
    expect(co2Equivalent(0)).toBe('')
  })
})

describe('totalConsumption', () => {
  const analysis = (consumption?: { durationS: number; energyWh: number; co2G: number; waterMl: number }) => ({ consumption }) as never

  it('adds up what the analyses consumed, the ones not measured counting for nothing', () => {
    const total = totalConsumption([
      analysis({ durationS: 1, energyWh: 2, co2G: 3, waterMl: 4 }),
      analysis(),
      analysis({ durationS: 10, energyWh: 20, co2G: 30, waterMl: 40 }),
    ])
    expect(total).toEqual({ durationS: 11, energyWh: 22, co2G: 33, waterMl: 44 })
    expect(hasConsumption(total)).toBe(true)
    expect(hasConsumption(totalConsumption([]))).toBe(false)
    expect(hasConsumption(null)).toBe(false)
  })
})
