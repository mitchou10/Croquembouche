// Placeholder data until the backend can say which documents look like another: there is no endpoint for it yet. The
// page only depends on the shapes below, so the real answer (the nearest pages of the catalogue's index) replaces
// `findNeighbours` without anything else changing.

export interface Neighbour {
  id: string
  name: string
  /** 0 to 1: how much the document looks like the one that was sent. */
  similarity: number
  /** A picture of the document (the first page of it). */
  imageUrl: string
}

/** A link between two neighbours, when they look like each other too: it makes groups appear in the graph. */
export interface NeighbourLink {
  source: string
  target: string
  similarity: number
}

export interface Neighbourhood {
  neighbours: Neighbour[]
  links: NeighbourLink[]
}

export const MIN_NEIGHBOURS = 1
export const MAX_NEIGHBOURS = 12
export const DEFAULT_NEIGHBOURS = 6

const KINDS = [
  'Facture',
  'Bulletin de salaire',
  'Avis d’imposition',
  'Attestation',
  'Contrat de travail',
  'Relevé bancaire',
  'Devis',
  'Bon de commande',
  'Justificatif de domicile',
  'Quittance de loyer',
  'Carte d’identité',
  'Feuille de soins',
]

function hash(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
  return h >>> 0
}

function seeded(seed: number): () => number {
  let state = seed || 1
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0
    return state / 4294967296
  }
}

/** A sheet of paper as a picture: a coloured title, lines of text, a block. Each hue makes a document look its own. */
export function sheetImage(hue: number, seed: number): string {
  const random = seeded(seed)
  const lines = Array.from({ length: 9 }, (_, i) => {
    const width = 50 + Math.round(random() * 70)
    return `<rect x="14" y="${58 + i * 12}" width="${width}" height="4" rx="2" fill="#c9ced6"/>`
  }).join('')
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 190">` +
    `<rect width="140" height="190" fill="#fff"/>` +
    `<rect x="14" y="14" width="${50 + Math.round(random() * 50)}" height="12" rx="2" fill="hsl(${hue} 55% 45%)"/>` +
    `<rect x="14" y="32" width="${30 + Math.round(random() * 40)}" height="5" rx="2" fill="#9aa1ad"/>` +
    `<rect x="84" y="40" width="42" height="26" rx="2" fill="hsl(${hue} 45% 88%)"/>${lines}</svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

/**
 * The `k` documents that look the most like the one sent, the likeliest first. The same file always gives the same
 * answer. Pretends to take a moment, as the real one will.
 */
export async function findNeighbours(file: File, k: number): Promise<Neighbourhood> {
  const count = Math.max(MIN_NEIGHBOURS, Math.min(MAX_NEIGHBOURS, Math.round(k)))
  const seed = hash(`${file.name}|${file.size}`)
  const random = seeded(seed)
  const start = seed % KINDS.length
  const neighbours: Neighbour[] = Array.from({ length: count }, (_, i) => {
    const kind = KINDS[(start + i * 5) % KINDS.length]
    const similarity = Math.max(0.3, 0.97 - i * (0.5 / Math.max(count, 1)) - random() * 0.04)
    return {
      id: `n${i + 1}`,
      name: `${kind} ${String(1 + Math.floor(random() * 90)).padStart(2, '0')}`,
      similarity: Math.round(similarity * 100) / 100,
      imageUrl: sheetImage(Math.round(((start + i * 5) % KINDS.length) * 30) % 360, hash(`${seed}-${i}`)),
    }
  })
  // The ones that look the most like the file also look like each other.
  const links: NeighbourLink[] = []
  for (let i = 0; i < count; i++) {
    for (let j = i + 1; j < count; j++) {
      const shared = Math.min(neighbours[i].similarity, neighbours[j].similarity) - 0.12 - random() * 0.2
      if (shared > 0.45) links.push({ source: neighbours[i].id, target: neighbours[j].id, similarity: Math.round(shared * 100) / 100 })
    }
  }
  return { neighbours, links }
}
