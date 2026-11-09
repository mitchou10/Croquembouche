/**
 * The place of the nodes of a graph, found the way a force graph does: the nodes push each other away, the links pull
 * the nodes they join to the distance they ask for, and everything is drawn a little to the middle so that nothing
 * leaves. Nothing but numbers: the page decides what to do with them (draw them, drag them), and a test can settle a
 * layout without a screen.
 */

export interface LayoutNode {
  id: string
  /** Half of the node's biggest side: what must not be covered by another node. */
  radius: number
  x: number
  y: number
  vx: number
  vy: number
  /** A node that is held (the one being dragged, or the one the graph is about) does not move by itself. */
  fixed: boolean
}

export interface LayoutLink {
  source: string
  target: string
  /** How far apart the two nodes want to be, centre to centre. */
  distance: number
  /** 0 to 1: how hard the link pulls. */
  strength: number
}

export interface Layout {
  nodes: LayoutNode[]
  /** One step; gives the energy that is left (the nodes' speeds, added), which is near 0 once the graph has settled. */
  tick(): number
  /** Steps until nothing moves any more, or `max` of them. */
  settle(max?: number): void
  /** Wakes a settled graph up (after a node was moved by hand). */
  reheat(): void
  /** Sets the size of the area the nodes are kept in. */
  resize(width: number, height: number): void
}

const REPULSION = 2600
const GRAVITY = 0.012
const DAMPING = 0.82
const MAX_SPEED = 30
const MIN_ENERGY = 0.02

/** A number in [0, 1) that is the same for the same seed: the first positions must not change from one visit to the next. */
function seeded(seed: number): () => number {
  let state = seed >>> 0 || 1
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0
    return state / 4294967296
  }
}

export function createLayout(
  input: { id: string; radius: number; fixed?: boolean; x?: number; y?: number }[],
  links: LayoutLink[],
  width: number,
  height: number,
): Layout {
  const random = seeded(input.length * 7919 + 17)
  let w = width
  let h = height
  // Around the middle, not on top of each other (which would make no direction to push away to).
  const nodes: LayoutNode[] = input.map((node, i) => {
    const angle = (i / Math.max(input.length, 1)) * Math.PI * 2 + random() * 0.4
    const spread = node.fixed ? 0 : Math.min(w, h) * (0.2 + random() * 0.15)
    return {
      id: node.id,
      radius: node.radius,
      // A node that is held can be put where it must be (the pages of a document, in a row).
      x: node.x ?? w / 2 + Math.cos(angle) * spread,
      y: node.y ?? h / 2 + Math.sin(angle) * spread,
      vx: 0,
      vy: 0,
      fixed: node.fixed ?? false,
    }
  })
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const edges = links.flatMap((l) => {
    const source = byId.get(l.source)
    const target = byId.get(l.target)
    return source && target && source !== target ? [{ source, target, link: l }] : []
  })
  let alpha = 1

  function tick(): number {
    // Every pair pushes the other away, the more the closer they are, and never lets them overlap.
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i]
        const b = nodes[j]
        let dx = b.x - a.x
        let dy = b.y - a.y
        let d2 = dx * dx + dy * dy
        if (d2 < 1) {
          // Exactly on each other: any direction will do, but it must be the same every time.
          dx = (i % 2 ? 1 : -1) * 0.5
          dy = (j % 2 ? 1 : -1) * 0.5
          d2 = dx * dx + dy * dy
        }
        const d = Math.sqrt(d2)
        const overlap = Math.max(0, a.radius + b.radius + 8 - d)
        const push = (REPULSION / d2 + overlap * 0.5) * alpha
        const fx = (dx / d) * push
        const fy = (dy / d) * push
        a.vx -= fx
        a.vy -= fy
        b.vx += fx
        b.vy += fy
      }
    }
    // Every link pulls, or pushes, its two nodes towards the distance it asks for.
    for (const { source, target, link } of edges) {
      const dx = target.x - source.x
      const dy = target.y - source.y
      const d = Math.sqrt(dx * dx + dy * dy) || 1
      const pull = ((d - link.distance) / d) * link.strength * 0.5 * alpha
      source.vx += dx * pull
      source.vy += dy * pull
      target.vx -= dx * pull
      target.vy -= dy * pull
    }
    let energy = 0
    for (const n of nodes) {
      if (n.fixed) {
        n.vx = 0
        n.vy = 0
        continue
      }
      n.vx += (w / 2 - n.x) * GRAVITY * alpha
      n.vy += (h / 2 - n.y) * GRAVITY * alpha
      n.vx = Math.max(-MAX_SPEED, Math.min(MAX_SPEED, n.vx * DAMPING))
      n.vy = Math.max(-MAX_SPEED, Math.min(MAX_SPEED, n.vy * DAMPING))
      n.x += n.vx
      n.y += n.vy
      // Kept in the area, with the node's own size to spare.
      n.x = Math.max(n.radius, Math.min(w - n.radius, n.x))
      n.y = Math.max(n.radius, Math.min(h - n.radius, n.y))
      energy += Math.abs(n.vx) + Math.abs(n.vy)
    }
    alpha = Math.max(alpha * 0.985, 0.05)
    return energy
  }

  return {
    nodes,
    tick,
    settle(max = 400) {
      for (let i = 0; i < max; i++) if (tick() < MIN_ENERGY && i > 20) break
    },
    reheat() {
      alpha = Math.max(alpha, 0.5)
    },
    resize(width, height) {
      w = width
      h = height
    },
  }
}
