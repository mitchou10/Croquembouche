import { describe, expect, it } from 'vitest'
import { createLayout } from './forceLayout'

const gap = (a: { x: number; y: number }, b: { x: number; y: number }) => Math.hypot(a.x - b.x, a.y - b.y)

describe('the force layout', () => {
  const nodes = [
    { id: 'q', radius: 40, fixed: true },
    { id: 'near', radius: 30 },
    { id: 'far', radius: 30 },
  ]
  const links = [
    { source: 'q', target: 'near', distance: 150, strength: 0.8 },
    { source: 'q', target: 'far', distance: 330, strength: 0.8 },
  ]

  it('keeps the node it is about where it is', () => {
    const layout = createLayout(nodes, links, 800, 540)
    layout.settle()
    expect(layout.nodes[0]).toMatchObject({ x: 400, y: 270 })
  })

  it('puts a node at about the distance its link asks for, so the closer a document looks, the closer it sits', () => {
    const layout = createLayout(nodes, links, 800, 540)
    layout.settle()
    const [q, near, far] = layout.nodes
    expect(gap(q, near)).toBeLessThan(gap(q, far))
    expect(gap(q, near)).toBeGreaterThan(100)
    expect(gap(q, far)).toBeGreaterThan(220)
  })

  it('does not let nodes cover each other', () => {
    const many = [{ id: 'q', radius: 50, fixed: true }, ...Array.from({ length: 10 }, (_, i) => ({ id: `n${i}`, radius: 35 }))]
    const layout = createLayout(many, many.slice(1).map((n) => ({ source: 'q', target: n.id, distance: 160, strength: 0.8 })), 800, 540)
    layout.settle()
    for (let i = 0; i < layout.nodes.length; i++)
      for (let j = i + 1; j < layout.nodes.length; j++)
        expect(gap(layout.nodes[i], layout.nodes[j])).toBeGreaterThan((layout.nodes[i].radius + layout.nodes[j].radius) * 0.9)
  })

  it('keeps every node in the area', () => {
    const layout = createLayout(nodes, links, 800, 540)
    layout.settle()
    for (const n of layout.nodes) {
      expect(n.x).toBeGreaterThanOrEqual(n.radius)
      expect(n.x).toBeLessThanOrEqual(800 - n.radius)
      expect(n.y).toBeGreaterThanOrEqual(n.radius)
      expect(n.y).toBeLessThanOrEqual(540 - n.radius)
    }
  })

  it('gives the same layout every time', () => {
    const run = () => {
      const layout = createLayout(nodes, links, 800, 540)
      layout.settle()
      return layout.nodes.map((n) => [n.x, n.y])
    }
    expect(run()).toEqual(run())
  })

  it('calms down, and moves again when a node is moved by hand', () => {
    const layout = createLayout(nodes, links, 800, 540)
    layout.settle()
    expect(layout.tick()).toBeLessThan(1)
    layout.nodes[1].x = layout.nodes[0].x + 5
    layout.nodes[1].y = layout.nodes[0].y
    layout.reheat()
    expect(layout.tick()).toBeGreaterThan(1)
  })

  it('ignores a link to a node that is not there', () => {
    const layout = createLayout(nodes, [{ source: 'q', target: 'ghost', distance: 100, strength: 1 }], 800, 540)
    expect(() => layout.settle()).not.toThrow()
  })
})
