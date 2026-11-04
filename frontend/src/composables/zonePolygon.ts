import type { Point } from '../data/mock'

/** A polygon keeps at least this many points. */
export const MIN_POINTS = 3

const clamp = (n: number, low: number, high: number) => Math.min(Math.max(n, low), high)

/** The points once the whole polygon was moved by (dx, dy), fractions of the page: it keeps its shape and stops at
 *  the edge of the page. */
export function movePolygon(points: Point[], dx: number, dy: number): Point[] {
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const mx = clamp(dx, -Math.min(...xs), 1 - Math.max(...xs))
  const my = clamp(dy, -Math.min(...ys), 1 - Math.max(...ys))
  return points.map((p) => ({ x: p.x + mx, y: p.y + my }))
}

/** The points with the one at `index` put at `to`, kept on the page. */
export function moveVertex(points: Point[], index: number, to: Point): Point[] {
  return points.map((p, i) => (i === index ? { x: clamp(to.x, 0, 1), y: clamp(to.y, 0, 1) } : p))
}

/** The points with a new one in the middle of the edge that starts at `index` (the last point joins the first). */
export function insertVertex(points: Point[], index: number): Point[] {
  const a = points[index]
  const b = points[(index + 1) % points.length]
  const middle = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
  return [...points.slice(0, index + 1), middle, ...points.slice(index + 1)]
}

/** The points without the one at `index`; unchanged when that would leave less than MIN_POINTS. */
export function removeVertex(points: Point[], index: number): Point[] {
  return points.length <= MIN_POINTS ? points : points.filter((_, i) => i !== index)
}

/** The middle of each edge, where a new point can be pulled out: edge i joins point i to the next one. */
export const midpoints = (points: Point[]): Point[] =>
  points.map((a, i) => {
    const b = points[(i + 1) % points.length]
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
  })
