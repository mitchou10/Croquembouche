import type { Point } from '../data/mock'

/** Straightening the zone of an element found on a document that lies turned or at an angle: its four corners, which the
 *  worker carries over in the order the model has them (top left, top right, bottom right, bottom left), are brought back
 *  to an upright rectangle with a perspective transformation, a CSS `matrix3d`. */

/** How far from upright a rectangle may be (a fraction of the page) and still be cut out as it is. */
const UPRIGHT = 0.004

/** Solves the linear system `a · x = b` (Gaussian elimination, partial pivoting); null when it has no single solution. */
function solve(a: number[][], b: number[]): number[] | null {
  const n = b.length
  const m = a.map((row, i) => [...row, b[i]])
  for (let col = 0; col < n; col++) {
    let pivot = col
    for (let row = col + 1; row < n; row++) if (Math.abs(m[row][col]) > Math.abs(m[pivot][col])) pivot = row
    if (Math.abs(m[pivot][col]) < 1e-12) return null
    ;[m[col], m[pivot]] = [m[pivot], m[col]]
    for (let row = col + 1; row < n; row++) {
      const factor = m[row][col] / m[col][col]
      for (let k = col; k <= n; k++) m[row][k] -= factor * m[col][k]
    }
  }
  const x = new Array<number>(n).fill(0)
  for (let row = n - 1; row >= 0; row--) {
    let sum = m[row][n]
    for (let k = row + 1; k < n; k++) sum -= m[row][k] * x[k]
    x[row] = sum / m[row][row]
  }
  return x
}

/** The homography taking each point of `from` to the one of `to` (four of each): nine numbers, by rows, the last one 1. */
export function homography(from: Point[], to: Point[]): number[] | null {
  const a: number[][] = []
  const b: number[] = []
  from.forEach((p, i) => {
    const { x: u, y: v } = to[i]
    a.push([p.x, p.y, 1, 0, 0, 0, -u * p.x, -u * p.y])
    b.push(u)
    a.push([0, 0, 0, p.x, p.y, 1, -v * p.x, -v * p.y])
    b.push(v)
  })
  const h = solve(a, b)
  return h && h.every(Number.isFinite) ? [...h, 1] : null
}

/** A homography as the CSS says it (columns first), for an element whose `transform-origin` is its top left corner. */
export const toMatrix3d = (h: number[]) =>
  `matrix3d(${[h[0], h[3], 0, h[6], h[1], h[4], 0, h[7], 0, 0, 1, 0, h[2], h[5], 0, 1].join(',')})`

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y)

const isConvex = (quad: Point[]) => {
  const signs = new Set<boolean>()
  for (let i = 0; i < 4; i++) {
    const [a, b, c] = [quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]]
    const cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)
    if (Math.abs(cross) < 1e-12) return false
    signs.add(cross > 0)
  }
  return signs.size === 1
}

/** A zone of four corners that sits straight on the page, as a rectangle drawn on a model does. */
export const isUpright = (quad: Point[]) =>
  quad.length === 4 &&
  Math.abs(quad[0].y - quad[1].y) < UPRIGHT &&
  Math.abs(quad[2].y - quad[3].y) < UPRIGHT &&
  Math.abs(quad[0].x - quad[3].x) < UPRIGHT &&
  Math.abs(quad[1].x - quad[2].x) < UPRIGHT &&
  quad[1].x > quad[0].x &&
  quad[3].y > quad[0].y

/**
 * How to bring a zone of four corners (fractions of a page of `width` by `height` pixels) back to a rectangle that is as
 * wide as the zone is (its top and bottom sides averaged) and as tall (its left and right ones), drawn `canvas` pixels
 * wide: its shape (width over height) and the `matrix3d` to put on the page image, laid out at its own pixel size.
 * Null when the zone is not four corners, is not convex, or is straight already: it is then cut out as it is.
 */
export function straighten(points: Point[], width: number, height: number, canvas: number) {
  if (points.length !== 4 || isUpright(points) || !isConvex(points)) return null
  const quad = points.map((p) => ({ x: p.x * width, y: p.y * height }))
  const w = (distance(quad[0], quad[1]) + distance(quad[3], quad[2])) / 2
  const h = (distance(quad[0], quad[3]) + distance(quad[1], quad[2])) / 2
  if (w < 1 || h < 1) return null
  const aspect = w / h
  const target = [
    { x: 0, y: 0 },
    { x: canvas, y: 0 },
    { x: canvas, y: canvas / aspect },
    { x: 0, y: canvas / aspect },
  ]
  const found = homography(quad, target)
  return found && { aspect, matrix: toMatrix3d(found) }
}
