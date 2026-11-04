import { describe, expect, it } from 'vitest'
import { resizeRect, MIN_SIDE, pointsOf, rectOf } from './zoneRect'

const rect = { x0: 0.2, y0: 0.2, x1: 0.6, y1: 0.5 }

describe('rectOf', () => {
  it('finds the rectangle of its four points, whatever their order', () => {
    expect(rectOf(pointsOf(rect))).toEqual(rect)
    expect(rectOf([...pointsOf(rect)].reverse())).toEqual(rect)
  })

  it('is null for a polygon', () => {
    expect(rectOf([{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }])).toBeNull()
    expect(rectOf([{ x: 0, y: 0 }, { x: 1, y: 0.1 }, { x: 1, y: 1 }, { x: 0, y: 1 }])).toBeNull()
  })
})

describe('resizeRect', () => {
  it('moves the sides of the handle only', () => {
    expect(resizeRect(rect, 'e', 0.1, 0.3)).toEqual({ ...rect, x1: 0.7 })
    expect(resizeRect(rect, 'nw', -0.1, -0.1)).toEqual({ ...rect, x0: 0.1, y0: 0.1 })
  })

  it('stays on the page', () => {
    expect(resizeRect(rect, 'se', 5, 5)).toEqual({ ...rect, x1: 1, y1: 1 })
    expect(resizeRect(rect, 'nw', -5, -5)).toEqual({ ...rect, x0: 0, y0: 0 })
  })

  it('keeps a minimum size instead of flipping', () => {
    const next = resizeRect(rect, 'e', -5, 0)
    expect(next.x1 - next.x0).toBeCloseTo(MIN_SIDE)
  })

  it('moves the whole rectangle, keeping its size, and stops at the edge', () => {
    expect(resizeRect(rect, 'move', 0.1, 0.1)).toEqual({ x0: 0.30000000000000004, y0: 0.30000000000000004, x1: 0.7, y1: 0.6 })
    const edge = resizeRect(rect, 'move', 5, -5)
    expect(edge.x1).toBe(1)
    expect(edge.y0).toBe(0)
    expect(edge.x1 - edge.x0).toBeCloseTo(0.4)
  })
})
