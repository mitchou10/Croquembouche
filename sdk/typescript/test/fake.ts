// A fake API: the answers a backend would give, kept as plain JSON, and what was asked of it.
import { Croquembouche, type CroquembouchOptions } from '../src/index.js'

export const URL = 'http://api.test'
export const SQUARE = { page: 1, points: [{ x: 0.1, y: 0.1 }, { x: 0.4, y: 0.1 }, { x: 0.4, y: 0.3 }] }

export function entity(id = 'e1', name = 'Numéro', zones: unknown[] = [SQUARE]) {
  return { id, name, type: 'text', definition: 'Le numéro', examples: [], tags: [], stars: [], zones, zone: zones[0] ?? null }
}

export function template(id = 't1', name = 'Formulaire', changes: Record<string, unknown> = {}) {
  return {
    id,
    version: '1.0.0',
    ownerId: 'alice',
    ownerName: 'Alice',
    name,
    description: 'Un formulaire',
    categories: [],
    entities: [entity()],
    pages: [],
    stars: [],
    suggestions: [],
    children: [],
    visibility: 'public',
    shares: [],
    ...changes,
  }
}

export function detection(changes: Record<string, unknown> = {}) {
  return {
    id: 'd1',
    zone: SQUARE,
    classifications: [
      { templateId: 't1', confidence: 0.9 },
      { templateId: null, confidence: 0.1 },
    ],
    review: { status: 'pending' },
    source: 'analysis',
    entityId: 'e1',
    foundInText: false,
    text: '42',
    zoneIndex: null,
    ...changes,
  }
}

export function run(status = 'running', changes: Record<string, unknown> = {}) {
  return {
    id: 'r1',
    userId: 'alice',
    userName: 'Alice',
    date: '2026-11-10',
    status,
    matches: 0,
    hasResult: true,
    ocrStatus: 'none',
    findStatus: 'none',
    detections: null,
    pages:
      status === 'done'
        ? [{ page: 1, classifications: [{ templateId: 't1', confidence: 0.9 }], review: { status: 'pending' } }]
        : null,
    templateVersions: { t1: '1.0.0' },
    ...changes,
  }
}

export function analysis(changes: Record<string, unknown> = {}) {
  return {
    id: 'a1',
    canOpen: true,
    name: 'Courriers',
    description: '',
    ownerId: 'alice',
    ownerName: 'Alice',
    views: 0,
    runs: [],
    templateIds: ['t1'],
    templateVersions: {},
    isPublic: false,
    shares: [],
    date: '2026-11-10',
    status: 'done',
    matches: 0,
    ...changes,
  }
}

/** The answers of a route, one after the other, the last for ever. */
export class Seq {
  constructor(readonly answers: unknown[]) {}
  next(): unknown {
    return this.answers.length > 1 ? this.answers.shift() : this.answers[0]
  }
}

type Answer = unknown | Seq | ((request: Request) => Response)

export class FakeAPI {
  routes = new Map<string, { status: number; answer: Answer }>()
  seen: Request[] = []

  on(route: string, answer: Answer, status = 200): void {
    this.routes.set(route, { status, answer })
  }

  /** The `fetch` of the SDK. */
  fetch = async (input: Request | string | URL, init?: RequestInit): Promise<Response> => {
    const request = new Request(input, init)
    this.seen.push(request.clone())
    const route = `${request.method} ${new globalThis.URL(request.url).pathname}`
    const found = this.routes.get(route)
    if (!found) return Response.json({ detail: `no route ${route}` }, { status: 404 })
    let { answer } = found
    if (typeof answer === 'function') return (answer as (r: Request) => Response)(request)
    if (answer instanceof Seq) answer = answer.next()
    if (answer instanceof Uint8Array) return new Response(answer as BodyInit, { status: found.status })
    if (typeof answer === 'string') return new Response(answer, { status: found.status })
    return found.status === 204 ? new Response(null, { status: 204 }) : Response.json(answer, { status: found.status })
  }

  requests(route: string): Request[] {
    return this.seen.filter((r) => `${r.method} ${new globalThis.URL(r.url).pathname}` === route)
  }

  static async body(request: Request): Promise<any> {
    return JSON.parse(await request.text())
  }

  client(options: CroquembouchOptions = {}): Croquembouche {
    return new Croquembouche(URL, { fetch: this.fetch as typeof fetch, ...options })
  }
}
