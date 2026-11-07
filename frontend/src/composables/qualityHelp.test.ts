import { describe, expect, it } from 'vitest'
import { EXAMPLE, exampleFigures, METRICS, ORDER } from './qualityHelp'

describe('the explanations of the quality', () => {
  it('explain every figure, each in a question and a few words, and none twice', () => {
    expect(new Set(ORDER).size).toBe(ORDER.length)
    expect(ORDER.sort()).toEqual(Object.keys(METRICS).sort())
    for (const key of ORDER) {
      const { term, question, text } = METRICS[key]
      expect(term.length).toBeGreaterThan(0)
      expect(question.endsWith('?')).toBe(true)
      expect(text.length).toBeGreaterThan(40)
      expect(text.length).toBeLessThan(420) // a few words, not a lesson
    }
  })

  it('make the example with the formulas of the figures: precision, recall and F1', () => {
    expect(EXAMPLE).toEqual({ proposed: 10, validated: 8, invalidated: 2, added: 4 })
    // 8 right of 10 judged, 8 found of the 12 there were; F1 is their harmonic mean.
    expect(exampleFigures()).toEqual({ precision: '80 %', recall: '67 %', f1: '73 %' })
  })
})
