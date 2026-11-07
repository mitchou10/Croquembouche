import type { Analysis, Consumption } from '../data/mock'

/**
 * What a use consumed, told in things people have an idea of. Everything that is a guess is here, to be corrected in one
 * place: the equivalents are orders of magnitude, not measures (the electricity and the CO2 are measured by the worker,
 * the water is estimated by the backend from the electricity).
 */
const EQUIVALENTS = {
  /** An electric oven (2 kW) baking a batch of 12 muffins for 25 minutes. */
  muffinWh: 70,
  /** A LED bulb. */
  ledWatts: 10,
  /** A bottle of water, and a teaspoon. */
  bottleMl: 500,
  teaspoonMl: 5,
  /** What an average car emits a kilometre (ADEME, about). */
  carGramsPerKm: 200,
} as const

const FR = (digits: number) => new Intl.NumberFormat('fr-FR', { maximumFractionDigits: digits })

/** A number with the digits that matter: two significant ones below 10, none past the unit above 100. */
export function figure(value: number): string {
  if (value === 0) return '0'
  if (value >= 100) return FR(0).format(Math.round(value))
  if (value >= 10) return FR(0).format(value)
  if (value >= 1) return FR(1).format(value)
  return FR(value >= 0.1 ? 2 : 3).format(value)
}

const plural = (n: number, one: string, many: string) => (n < 2 ? one : many)

export const emptyConsumption = (): Consumption => ({ durationS: 0, energyWh: 0, co2G: 0, waterMl: 0 })

/** What several analyses consumed, together. */
export const totalConsumption = (analyses: Analysis[]): Consumption =>
  analyses.reduce((sum, a) => {
    const c = a.consumption ?? emptyConsumption()
    return {
      durationS: sum.durationS + c.durationS,
      energyWh: sum.energyWh + c.energyWh,
      co2G: sum.co2G + c.co2G,
      waterMl: sum.waterMl + c.waterMl,
    }
  }, emptyConsumption())

/** What fills a gauge: the quantity at which it is empty and at which it is full, on a logarithmic scale (the quantities
 * are far too apart for a linear one: a use is a few hundredths of a bottle, a month of them is one). Full is what the
 * equivalent is about: a muffin baked, a kilometre by car, a bottle of water. */
const GAUGE = {
  energy: { empty: 0.01, full: 70 },
  co2: { empty: 0.01, full: 200 },
  water: { empty: 0.1, full: 500 },
} as const

export type GaugeKind = keyof typeof GAUGE

/** How full a gauge is, from 0 (nothing was consumed) to 1; a little something is always seen when there is something. */
export function gaugeLevel(kind: GaugeKind, value: number): number {
  if (!(value > 0)) return 0
  const { empty, full } = GAUGE[kind]
  const level = Math.log(value / empty) / Math.log(full / empty)
  return Math.round(Math.min(1, Math.max(0.06, level)) * 100) / 100
}

export const hasConsumption = (c: Consumption | null | undefined): c is Consumption => !!c && c.energyWh > 0

export function formatEnergy(wh: number): string {
  return wh >= 1000 ? `${figure(wh / 1000)} kWh` : `${figure(wh)} Wh`
}

export function formatCo2(g: number): string {
  return g >= 1000 ? `${figure(g / 1000)} kg` : `${figure(g)} g`
}

export function formatWater(ml: number): string {
  return ml >= 1000 ? `${figure(ml / 1000)} L` : `${figure(ml)} mL`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${figure(seconds)} s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes} min ${Math.round(seconds - minutes * 60)} s`
}

/** The electricity as muffins baked when it is that much, else as the time a LED bulb would stay lit. */
export function electricityEquivalent(wh: number): string {
  if (wh <= 0) return ''
  if (wh >= EQUIVALENTS.muffinWh / 2) {
    const muffins = wh / EQUIVALENTS.muffinWh
    return `${figure(muffins)} ${plural(muffins, 'muffin cuit', 'muffins cuits')} au four`
  }
  const seconds = (wh / EQUIVALENTS.ledWatts) * 3600
  return seconds >= 120 ? `une ampoule LED allumée ${figure(seconds / 60)} min` : `une ampoule LED allumée ${figure(seconds)} s`
}

/** The water as bottles of water when it is half of one or more, else as teaspoons. */
export function waterEquivalent(ml: number): string {
  if (ml <= 0) return ''
  if (ml >= EQUIVALENTS.bottleMl / 2) {
    const bottles = ml / EQUIVALENTS.bottleMl
    return `${figure(bottles)} ${plural(bottles, 'bouteille', 'bouteilles')} d’eau`
  }
  const spoons = ml / EQUIVALENTS.teaspoonMl
  return `${figure(spoons)} ${plural(spoons, 'cuillère à café', 'cuillères à café')}`
}

/** The CO2 as the distance a car would drive to emit it. */
export function co2Equivalent(g: number): string {
  if (g <= 0) return ''
  const meters = (g / EQUIVALENTS.carGramsPerKm) * 1000
  return meters >= 1000 ? `${figure(meters / 1000)} km en voiture` : `${figure(meters)} m en voiture`
}
