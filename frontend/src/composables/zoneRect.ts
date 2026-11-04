import type { Point } from '../data/mock'

/** A rectangle in fractions (0 to 1) of the page. */
export interface Rect {
  x0: number
  y0: number
  x1: number
  y1: number
}

/** The sides a handle moves: « n », « se », ... ; « move » moves the whole rectangle. */
export type Handle = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw' | 'move'

/** The smallest a side can get (a fraction of the page): a rectangle is never squeezed to nothing. */
export const MIN_SIDE = 0.01

const clamp = (n: number, low: number, high: number) => Math.min(Math.max(n, low), high)

/** The rectangle a zone is, or null when it is anything else (a polygon). A rectangle has its four points at the
 *  corners of its bounds, in any order. */
export function rectOf(points: Point[]): Rect | null {
  if (points.length !== 4) return null
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const rect = { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }
  const corners = new Set(points.map((p) => `${p.x === rect.x0 ? 0 : p.x === rect.x1 ? 1 : 'x'}${p.y === rect.y0 ? 0 : p.y === rect.y1 ? 1 : 'x'}`))
  return corners.size === 4 && ![...corners].some((c) => c.includes('x')) ? rect : null
}

/** The four points of a rectangle, clockwise from the top left. */
export const pointsOf = (r: Rect): Point[] => [
  { x: r.x0, y: r.y0 },
  { x: r.x1, y: r.y0 },
  { x: r.x1, y: r.y1 },
  { x: r.x0, y: r.y1 },
]

/** The rectangle once a handle was dragged by (dx, dy), in fractions of the page. It stays on the page and keeps at
 *  least MIN_SIDE on each side. */
export function resizeRect(start: Rect, handle: Handle, dx: number, dy: number): Rect {
  if (handle === 'move') {
    const mx = clamp(dx, -start.x0, 1 - start.x1)
    const my = clamp(dy, -start.y0, 1 - start.y1)
    return { x0: start.x0 + mx, y0: start.y0 + my, x1: start.x1 + mx, y1: start.y1 + my }
  }
  const next = { ...start }
  if (handle.includes('w')) next.x0 = clamp(start.x0 + dx, 0, start.x1 - MIN_SIDE)
  if (handle.includes('e')) next.x1 = clamp(start.x1 + dx, start.x0 + MIN_SIDE, 1)
  if (handle.includes('n')) next.y0 = clamp(start.y0 + dy, 0, start.y1 - MIN_SIDE)
  if (handle.includes('s')) next.y1 = clamp(start.y1 + dy, start.y0 + MIN_SIDE, 1)
  return next
}
