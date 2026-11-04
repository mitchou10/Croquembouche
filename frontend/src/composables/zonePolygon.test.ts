import { describe, expect, it } from 'vitest'
import { insertVertex, midpoints, moveVertex, movePolygon, removeVertex } from './zonePolygon'

const triangle = [
  { x: 0.2, y: 0.2 },
  { x: 0.6, y: 0.2 },
  { x: 0.4, y: 0.6 },
]

describe('movePolygon', () => {
  it('moves every point by the same amount', () => {
    expect(movePolygon(triangle, 0.1, 0.1).map((p) => p.x)).toEqual([0.30000000000000004, 0.7, 0.5])
  })

  it('keeps its shape and stops at the edge of the page', () => {
    const moved = movePolygon(triangle, 5, -5)
    expect(Math.max(...moved.map((p) => p.x))).toBe(1)
    expect(Math.min(...moved.map((p) => p.y))).toBe(0)
    expect(moved[1].x - moved[0].x).toBeCloseTo(0.4)
  })
})

describe('vertices', () => {
  it('moves one point and keeps it on the page', () => {
    expect(moveVertex(triangle, 1, { x: 2, y: -1 })).toEqual([triangle[0], { x: 1, y: 0 }, triangle[2]])
  })

  it('inserts a point in the middle of an edge, the last edge included', () => {
    expect(insertVertex(triangle, 0)[1]).toEqual({ x: 0.4, y: 0.2 })
    const last = insertVertex(triangle, 2)
    expect(last).toHaveLength(4)
    expect(last[3].x).toBeCloseTo(0.3)
  })

  it('removes a point, but never below three', () => {
    const square = [...triangle, { x: 0.1, y: 0.5 }]
    expect(removeVertex(square, 3)).toEqual(triangle)
    expect(removeVertex(triangle, 0)).toBe(triangle)
  })

  it('finds the middle of each edge', () => {
    expect(midpoints(triangle)).toHaveLength(3)
    expect(midpoints(triangle)[0]).toEqual({ x: 0.4, y: 0.2 })
  })
})
