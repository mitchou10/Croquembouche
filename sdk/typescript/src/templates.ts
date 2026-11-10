import { type Document, asForm, formWith } from './files.js'
import { type Http, ok } from './http.js'
import type {
  DocumentOut,
  EntityTypeOut,
  Share,
  TemplateCreate,
  TemplateMetrics,
  TemplateOut,
  TemplateUpdate,
  TemplateVersionDetail,
  TemplateVersionOut,
  Visibility,
} from './types.js'

/** The catalogue: the models, their entities (with their zones), their versions and the image of their pages. What a
 *  token may see is what it gets: a model it cannot use is not in the list, and is not found. */
export class Templates {
  constructor(private readonly http: Http) {}

  /** The models, searched by name, description or category (`q`), and only the token's own with `mine`. */
  list(q = '', { mine = false }: { mine?: boolean } = {}): Promise<TemplateOut[]> {
    return ok(this.http.GET('/api/templates', { params: { query: { q, mine } } }))
  }

  get(templateId: string): Promise<TemplateOut> {
    return ok(this.http.GET('/api/templates/{template_id}', { params: { path: { template_id: templateId } } }))
  }

  /** Its versions (X.Y.Z), the newest first. */
  versions(templateId: string): Promise<TemplateVersionOut[]> {
    return ok(
      this.http.GET('/api/templates/{template_id}/versions', { params: { path: { template_id: templateId } } }),
    )
  }

  /** A version as it was: all its fields, entities and zones included. */
  version(templateId: string, version: string): Promise<TemplateVersionDetail> {
    return ok(
      this.http.GET('/api/templates/{template_id}/versions/{version}', {
        params: { path: { template_id: templateId, version } },
      }),
    )
  }

  /** The image of a page (from 1) of the example document. `documentId`: the one of an older version. */
  async page(templateId: string, number: number, { documentId }: { documentId?: string } = {}): Promise<Uint8Array> {
    const data = await ok(
      this.http.GET('/api/templates/{template_id}/pages/{number}', {
        params: { path: { template_id: templateId, number }, query: { documentId } },
        parseAs: 'arrayBuffer',
      }),
    )
    return new Uint8Array(data as ArrayBuffer)
  }

  /** How right the analysis has been on the model, from what people decided of its results. */
  metrics(templateId: string): Promise<TemplateMetrics> {
    return ok(
      this.http.GET('/api/templates/{template_id}/metrics', { params: { path: { template_id: templateId } } }),
    )
  }

  entityTypes(): Promise<EntityTypeOut[]> {
    return ok(this.http.GET('/api/entity-types'))
  }

  categories(): Promise<string[]> {
    return ok(this.http.GET('/api/categories'))
  }

  // --- writing: a token of a person, which makes them the owner (a service account that reads changes nothing)

  /** Sends the example document of a model (an image or a PDF): its `id` goes in `documentId`. */
  async uploadDocument(document: Document, { filename }: { filename?: string } = {}): Promise<DocumentOut> {
    return ok(this.http.POST('/api/documents', { ...asForm(await formWith(document, filename)) }))
  }

  /** The image of a page (from 1) of a document that was sent. */
  async documentPage(documentId: string, number: number): Promise<Uint8Array> {
    const data = await ok(
      this.http.GET('/api/documents/{document_id}/pages/{number}', {
        params: { path: { document_id: documentId, number } },
        parseAs: 'arrayBuffer',
      }),
    )
    return new Uint8Array(data as ArrayBuffer)
  }

  create(body: TemplateCreate): Promise<TemplateOut> {
    return ok(this.http.POST('/api/templates', { body }))
  }

  /** Its owner only. The fields as they are to become: what is left out is taken away. */
  update(templateId: string, body: TemplateUpdate): Promise<TemplateOut> {
    return ok(this.http.PUT('/api/templates/{template_id}', { params: { path: { template_id: templateId } }, body }))
  }

  /** Says who can use the model: `private`, `shared` (with the people and groups in `shares`) or `public`. */
  share(templateId: string, visibility: Visibility, shares: Share[] = []): Promise<TemplateOut> {
    return ok(
      this.http.PUT('/api/templates/{template_id}/shares', {
        params: { path: { template_id: templateId } },
        body: { visibility, shares },
      }),
    )
  }

  /** Goes back to a version, which makes a new one. */
  restore(templateId: string, version: string): Promise<TemplateOut> {
    return ok(
      this.http.POST('/api/templates/{template_id}/versions/{version}/restore', {
        params: { path: { template_id: templateId, version } },
      }),
    )
  }

  /** Makes a sub-model a model of its own. */
  promote(templateId: string): Promise<TemplateOut> {
    return ok(this.http.POST('/api/templates/{template_id}/promote', { params: { path: { template_id: templateId } } }))
  }

  /** Deletes a model that no analysis uses. A model with sub-models says which one takes its place. */
  async delete(templateId: string, { promoteChild }: { promoteChild?: string } = {}): Promise<void> {
    await ok(
      this.http.DELETE('/api/templates/{template_id}', {
        params: { path: { template_id: templateId }, query: { promote: promoteChild } },
      }),
    )
  }
}
