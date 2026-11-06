import { describe, expect, it } from 'vitest'
import { homography, isUpright, straighten, toMatrix3d } from './perspective'

const apply = (h: number[], x: number, y: number) => {
  const w = h[6] * x + h[7] * y + h[8]
  return { x: (h[0] * x + h[1] * y + h[2]) / w, y: (h[3] * x + h[4] * y + h[5]) / w }
}

const rectangle = [
  { x: 0.1, y: 0.2 },
  { x: 0.5, y: 0.2 },
  { x: 0.5, y: 0.4 },
  { x: 0.1, y: 0.4 },
]
// The same rectangle turned a quarter turn: what a document scanned on its side gives.
const turned = [
  { x: 0.6, y: 0.1 },
  { x: 0.6, y: 0.5 },
  { x: 0.4, y: 0.5 },
  { x: 0.4, y: 0.1 },
]

describe('homography', () => {
  it('takes each corner to its target, and what is between them with it', () => {
    const to = [
      { x: 0, y: 0 },
      { x: 400, y: 0 },
      { x: 400, y: 200 },
      { x: 0, y: 200 },
    ]
    const h = homography(turned.map((p) => ({ x: p.x * 100, y: p.y * 100 })), to)!
    turned.forEach((p, i) => {
      const got = apply(h, p.x * 100, p.y * 100)
      expect(got.x).toBeCloseTo(to[i].x, 6)
      expect(got.y).toBeCloseTo(to[i].y, 6)
    })
    const middle = apply(h, 50, 30) // the centre of the turned rectangle
    expect(middle.x).toBeCloseTo(200, 6)
    expect(middle.y).toBeCloseTo(100, 6)
  })

  it('has none for corners that are on one line', () => {
    const line = [0, 1, 2, 3].map((x) => ({ x, y: x }))
    expect(homography(line, rectangle)).toBeNull()
  })
})

describe('toMatrix3d', () => {
  it('writes the columns first, as the CSS reads them', () => {
    expect(toMatrix3d([1, 2, 3, 4, 5, 6, 7, 8, 1])).toBe('matrix3d(1,4,0,7,2,5,0,8,0,0,1,0,3,6,0,1)')
  })
})

describe('isUpright', () => {
  it('is a rectangle that sits straight on the page', () => {
    expect(isUpright(rectangle)).toBe(true)
    expect(isUpright(turned)).toBe(false)
    expect(isUpright(rectangle.slice(0, 3))).toBe(false)
  })
})

describe('straighten', () => {
  it('leaves a zone that is straight to be cut out as it is', () => {
    expect(straighten(rectangle, 1000, 1000, 400)).toBeNull()
  })

  it('does not take a zone that is not four corners, or not convex', () => {
    expect(straighten([...rectangle, { x: 0.3, y: 0.5 }], 1000, 1000, 400)).toBeNull()
    const bowtie = [rectangle[0], rectangle[2], rectangle[1], rectangle[3]]
    expect(straighten(bowtie, 1000, 1000, 400)).toBeNull()
  })

  it('gives the shape the zone has once straight: a quarter turn swaps its sides', () => {
    // 0.2 wide by 0.4 tall on a page of 1000 by 500 pixels: 100 by 200 pixels, the top side being the long one turned.
    const result = straighten(turned, 1000, 500, 400)!
    expect(result.aspect).toBeCloseTo((0.4 * 500) / (0.2 * 1000), 6) // 200 / 200
    expect(result.matrix).toMatch(/^matrix3d\((-?[\d.e-]+,){15}-?[\d.e-]+\)$/)
  })
})
