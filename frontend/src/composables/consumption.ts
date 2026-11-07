import type { Analysis, Consumption } from '../data/mock'

/**
 * What a use consumed, told in things people have an idea of. Everything that is a guess is here, to be corrected in one
 * place: the equivalents are orders of magnitude, not measures (the electricity and the CO2 are measured by the worker,
 * the water is estimated by the backend from the electricity).
 */
const EQUIVALENTS = {
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

/** What a quantity is counted in, so that it can be seen: the units of each ladder are what a person has an idea of, each
 * one drawn as a thing that fills (see `ConsumptionGauge`). The unit is the smallest one of which there are fewer than
 * ten (never a hundred bottles: a bucket, a bath); past the largest one it says « plus de 10 » and shows ten full. Below
 * the smallest one there is only a part of it. Everything that is a guess is here, to be corrected in one place. */
export type GaugeKind = 'energy' | 'co2' | 'water'
export type GaugeShape = 'bulb' | 'balloon' | 'spoon' | 'glass' | 'bottle' | 'bucket' | 'bath'

interface Unit {
  /** How much of the quantity (Wh, g, mL) one of them is. */
  amount: number
  one: string
  many: string
  shape: GaugeShape
}

const LADDERS: Record<GaugeKind, Unit[]> = {
  // A LED bulb of 10 W, lit for a minute, an hour, a day, a month, a year.
  energy: [
    { amount: 10 / 60, one: 'ampoule LED allumée 1 minute', many: 'ampoules LED allumées 1 minute', shape: 'bulb' },
    { amount: 10, one: 'ampoule LED allumée 1 heure', many: 'ampoules LED allumées 1 heure', shape: 'bulb' },
    { amount: 240, one: 'ampoule LED allumée 1 jour', many: 'ampoules LED allumées 1 jour', shape: 'bulb' },
    { amount: 7_200, one: 'ampoule LED allumée 1 mois', many: 'ampoules LED allumées 1 mois', shape: 'bulb' },
    { amount: 87_600, one: 'ampoule LED allumée 1 an', many: 'ampoules LED allumées 1 an', shape: 'bulb' },
  ],
  // The gas of a balloon: a litre of CO2 weighs about 1,84 g (at 20 °C); and ten times that, a hundred, a thousand.
  co2: [
    { amount: 1.84, one: 'ballon de 1 L de CO₂', many: 'ballons de 1 L de CO₂', shape: 'balloon' },
    { amount: 18.4, one: 'ballon de 10 L de CO₂', many: 'ballons de 10 L de CO₂', shape: 'balloon' },
    { amount: 184, one: 'ballon de 100 L de CO₂', many: 'ballons de 100 L de CO₂', shape: 'balloon' },
    { amount: 1_840, one: 'ballon de 1 000 L de CO₂', many: 'ballons de 1 000 L de CO₂', shape: 'balloon' },
  ],
  // A teaspoon, a glass, a bottle of a litre, a bucket, a bath.
  water: [
    { amount: 5, one: 'cuillère à café', many: 'cuillères à café', shape: 'spoon' },
    { amount: 200, one: 'verre d’eau', many: 'verres d’eau', shape: 'glass' },
    { amount: 1_000, one: 'bouteille d’1 L', many: 'bouteilles d’1 L', shape: 'bottle' },
    { amount: 10_000, one: 'seau de 10 L', many: 'seaux de 10 L', shape: 'bucket' },
    { amount: 150_000, one: 'baignoire', many: 'baignoires', shape: 'bath' },
  ],
}

/** The most things drawn, and counted: past that they are all full and it says « plus de 10 ». */
export const MAX_SHOWN = 10
/** What is seen of a part that is there: a little something, however small. */
const MIN_SEEN = 0.06

export interface Units {
  shape: GaugeShape
  /** How many of the unit there are, with the figures that matter. */
  count: number
  /** « 3,4 bouteilles d’1 L ». */
  text: string
  /** How full each thing drawn is, from 0 to 1: the whole ones, then the part. */
  levels: number[]
}

/** What a quantity is, in things that fill: « 3,4 bouteilles d’1 L » is three full bottles and one filled at 40 %. Nothing
 * for nothing. */
export function unitsOf(kind: GaugeKind, value: number): Units | null {
  if (!(value > 0)) return null
  const ladder = LADDERS[kind]
  const unit = ladder.find((u) => value / u.amount < MAX_SHOWN) ?? ladder[ladder.length - 1]
  const count = value / unit.amount
  const over = count >= MAX_SHOWN
  const levels = Array.from({ length: over ? MAX_SHOWN : Math.ceil(count) }, (_, i) =>
    Math.round(Math.min(1, Math.max(MIN_SEEN, count - i)) * 100) / 100,
  )
  const text = over ? `plus de ${MAX_SHOWN} ${unit.many}` : `${figure(count)} ${plural(count, unit.one, unit.many)}`
  return { shape: unit.shape, count, text, levels }
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

/** The CO2 as the distance a car would drive to emit it. */
export function co2Equivalent(g: number): string {
  if (g <= 0) return ''
  const meters = (g / EQUIVALENTS.carGramsPerKm) * 1000
  return meters >= 1000 ? `${figure(meters / 1000)} km en voiture` : `${figure(meters)} m en voiture`
}
