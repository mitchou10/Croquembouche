import { describe, expect, it } from 'vitest'
import {
  co2Equivalent,
  figure,
  formatCo2,
  formatDuration,
  formatEnergy,
  formatWater,
  hasConsumption,
  MAX_SHOWN,
  totalConsumption,
  unitsOf,
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

describe('the equivalent in a car', () => {
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

describe('unitsOf', () => {
  it('has nothing for nothing', () => {
    expect(unitsOf('water', 0)).toBeNull()
    expect(unitsOf('energy', Number.NaN)).toBeNull()
  })

  it('takes the smallest unit of which there are fewer than ten', () => {
    expect(unitsOf('water', 4)?.shape).toBe('spoon')
    expect(unitsOf('water', 100)?.shape).toBe('glass')
    expect(unitsOf('water', 3400)?.shape).toBe('bottle')
    expect(unitsOf('water', 30_000)?.shape).toBe('bucket')
    expect(unitsOf('water', 400_000)?.shape).toBe('bath')
    expect(unitsOf('water', 0.01)?.shape).toBe('spoon') // only a part of the smallest
    expect(unitsOf('energy', 0.4)?.text).toContain('minute')
    expect(unitsOf('energy', 5)?.text).toContain('1 heure')
    expect(unitsOf('energy', 500)?.text).toContain('1 jour')
    expect(unitsOf('co2', 0.01)?.text).toContain('1 L de CO₂')
  })

  it('never counts ten or more: the next unit, and past the largest « plus de 10 »', () => {
    for (const kind of ['energy', 'co2', 'water'] as const) {
      for (const value of [0.001, 0.1, 3, 90, 4_000, 60_000, 900_000, 1e8, 1e11]) {
        const units = unitsOf(kind, value)!
        expect(units.levels.length).toBeLessThanOrEqual(MAX_SHOWN)
        // No « 100 bouteilles », no « 35 ampoules »: fewer than ten, or « plus de 10 ».
        if (!units.text.startsWith('plus de')) expect(units.count).toBeLessThan(MAX_SHOWN)
      }
    }
    expect(unitsOf('water', 1e9)?.text).toBe('plus de 10 baignoires')
    expect(unitsOf('energy', 1e9)?.text).toBe('plus de 10 ampoules LED allumées 1 an')
    expect(unitsOf('co2', 1e9)?.text).toBe('plus de 10 ballons de 1 000 L de CO₂')
  })

  it('draws the whole ones full then the part, always seeing a little of a part that is there', () => {
    expect(unitsOf('water', 2500)?.levels).toEqual([1, 1, 0.5])
    expect(unitsOf('water', 1000)?.levels).toEqual([1, 1, 1, 1, 1]) // five glasses
    expect(unitsOf('water', 0.001)?.levels).toEqual([0.06])
  })

  it('draws ten at most', () => {
    expect(unitsOf('water', 1e9)?.levels).toEqual(Array(MAX_SHOWN).fill(1))
    expect(unitsOf('water', 9_500)?.levels).toHaveLength(10)
    expect(unitsOf('water', 8_200)?.levels).toHaveLength(9)
  })
})
