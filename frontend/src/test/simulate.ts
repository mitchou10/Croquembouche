/** What testing an analysis on a document would say, made up: the fake backend's answer, and what the tests expect of it. */
import type { Analysis, Classification, Detection } from '../data/mock'

// A small hash of the name of the file: the same file always gives the same answer, which is what a demo needs.
function hash(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
  return h >>> 0
}

/** A seeded source of numbers between 0 and 1 (mulberry32): the same seed, the same sequence. */
function random(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// A class something can be: a model and, for the page of a document, the page of the model (null for a model with no document).
interface Key {
  templateId: string
  templatePage?: number | null
}

const same = (a: Key, b: Key) => a.templateId === b.templateId && a.templatePage === b.templatePage

/**
 * Every class something could be, the likeliest first, adding up to 100 %: the analysis is 62 to 98 % sure of the best answer,
 * and the rest is shared among the other classes and « other ».
 */
function classesFor(best: Key | null, keys: Key[], next: () => number): Classification[] {
  const others: (Key | null)[] = [...keys.filter((k) => !best || !same(k, best)), ...(best === null ? [] : [null])]
  // With no other class to share the rest with, the only one is certain.
  const top = others.length ? 62 + Math.floor(next() * 37) : 100
  const weights = others.map(() => next() + 0.05)
  const total = weights.reduce((sum, w) => sum + w, 0)
  const shares = weights.map((w) => Math.floor(((100 - top) * w) / total))
  if (shares.length) shares[0] += 100 - top - shares.reduce((sum, n) => sum + n, 0) // what rounding left goes to the first
  const make = (key: Key | null, confidence: number): Classification => ({
    templateId: key?.templateId ?? null,
    ...(key && key.templatePage !== undefined && { templatePage: key.templatePage }),
    confidence,
  })
  return [make(best, top / 100), ...others.map((k, i) => make(k, shares[i] / 100))].sort((a, b) => b.confidence - a.confidence)
}

/**
 * What a page of a document corresponds to, made up: a page of one of the models of the analysis, with every class it could
 * be (`pagesOf` says how many pages a model has, 0 for one with no document). Answers the same for the same file and page,
 * and differently from what is found in the page.
 */
export function simulatePage(
  analysis: Pick<Analysis, 'templateIds'>,
  file: { name: string; size: number },
  page = 1,
  pagesOf: (templateId: string) => number = () => 0,
): Classification[] {
  const next = random(hash(`page|${file.name}|${file.size}|${page}`))
  const keys: Key[] = analysis.templateIds.flatMap((templateId): Key[] => {
    const count = pagesOf(templateId)
    return count ? Array.from({ length: count }, (_, i) => ({ templateId, templatePage: i + 1 })) : [{ templateId, templatePage: null }]
  })
  const best = keys.length ? keys[Math.floor(next() * keys.length)] : null
  return classesFor(best, keys, next)
}

/**
 * What testing an analysis on a document says, made up: elements found at places of the page, each with what it could be
 * and how sure the analysis is of each. Stands in for the backend, and answers the same for the same file.
 */
export function simulateTest(analysis: Pick<Analysis, 'templateIds'>, file: { name: string; size: number }): Detection[] {
  const next = random(hash(`${file.name}|${file.size}`))
  const found: Omit<Detection, 'id'>[] = []

  for (const templateId of analysis.templateIds) {
    const count = Math.floor(next() * 4) // 0 to 3: a model is missing from a document one time in four
    for (let i = 0; i < count; i++) {
      // A zone: mostly a rectangle, sometimes a polygon with a corner cut, as drawn on a model.
      const w = 0.12 + next() * 0.23
      const h = 0.06 + next() * 0.16
      const x = 0.03 + next() * (0.94 - w)
      const y = 0.03 + next() * (0.94 - h)
      const round = (n: number) => Math.round(n * 1000) / 1000
      const corner = next() < 0.35
      const points = corner
        ? [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h * 0.6 }, { x: x + w * 0.8, y: y + h }, { x, y: y + h }]
        : [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }]

      const classifications = classesFor({ templateId }, analysis.templateIds.map((id) => ({ templateId: id })), next)
      found.push({ zone: { page: 1, points: points.map((p) => ({ x: round(p.x), y: round(p.y) })) }, classifications })
    }
  }

  // In reading order, top to bottom and left to right.
  const top = (d: Omit<Detection, 'id'>) => Math.min(...d.zone.points.map((p) => p.y))
  const left = (d: Omit<Detection, 'id'>) => Math.min(...d.zone.points.map((p) => p.x))
  return found.sort((a, b) => top(a) - top(b) || left(a) - left(b)).map((d, i) => ({ ...d, id: `d${i + 1}` }))
}

