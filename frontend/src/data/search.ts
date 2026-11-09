import type { Consumption } from './mock'

/**
 * A search for the documents that look like one that was sent: the pages of the document (a PDF has several) and, for
 * each, the pages of models of the catalogue that look the most like it. It is computed by a worker, so it is first
 * `running`; it is kept, with what it consumed, to be opened again.
 */
export type SearchStatus = 'running' | 'done' | 'failed'

export const MIN_NEIGHBOURS = 1
export const MAX_NEIGHBOURS = 12
export const DEFAULT_NEIGHBOURS = 6

/** A page of a model of the catalogue that looks like a page of the document. */
export interface SearchNeighbour {
  /** `<model>:<page>`: the same page of a model is one node, whatever the pages of the document it looks like. */
  id: string
  templateId: string
  templatePage: number
  /** 0 to 1: how much it looks like the page of the document it looks the most like. */
  similarity: number
}

/**
 * A link between two nodes. The pages of the document are `page-1`, `page-2`...; a link from one to a neighbour says it
 * is one of the neighbours of that page. A link between two neighbours says they look like each other too.
 */
export interface SearchLink {
  source: string
  target: string
  similarity: number
}

export interface SearchSummary {
  id: string
  fileName: string
  status: SearchStatus
  /** How many neighbours were asked for, for each page. */
  k: number
  /** The models looked in, or null for every model the person can see. */
  templateIds: string[] | null
  /** ISO date and time. */
  createdAt: string
  /** How many pages the document has. */
  pages: number
  neighbourCount: number
  /** What it consumed, once it is over and measured. */
  consumption: Consumption | null
}

export interface Search extends SearchSummary {
  neighbours: SearchNeighbour[]
  links: SearchLink[]
}

export const pageNodeId = (page: number) => `page-${page}`
