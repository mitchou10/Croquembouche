import { type Document } from './files.js';
import { type Http } from './http.js';
import type { DocumentOut, EntityTypeOut, Share, TemplateCreate, TemplateMetrics, TemplateOut, TemplateUpdate, TemplateVersionDetail, TemplateVersionOut, Visibility } from './types.js';
/** The catalogue: the models, their entities (with their zones), their versions and the image of their pages. What a
 *  token may see is what it gets: a model it cannot use is not in the list, and is not found. */
export declare class Templates {
    private readonly http;
    constructor(http: Http);
    /** The models, searched by name, description or category (`q`), and only the token's own with `mine`. */
    list(q?: string, { mine }?: {
        mine?: boolean;
    }): Promise<TemplateOut[]>;
    get(templateId: string): Promise<TemplateOut>;
    /** Its versions (X.Y.Z), the newest first. */
    versions(templateId: string): Promise<TemplateVersionOut[]>;
    /** A version as it was: all its fields, entities and zones included. */
    version(templateId: string, version: string): Promise<TemplateVersionDetail>;
    /** The image of a page (from 1) of the example document. `documentId`: the one of an older version. */
    page(templateId: string, number: number, { documentId }?: {
        documentId?: string;
    }): Promise<Uint8Array>;
    /** How right the analysis has been on the model, from what people decided of its results. */
    metrics(templateId: string): Promise<TemplateMetrics>;
    entityTypes(): Promise<EntityTypeOut[]>;
    categories(): Promise<string[]>;
    /** Sends the example document of a model (an image or a PDF): its `id` goes in `documentId`. */
    uploadDocument(document: Document, { filename }?: {
        filename?: string;
    }): Promise<DocumentOut>;
    /** The image of a page (from 1) of a document that was sent. */
    documentPage(documentId: string, number: number): Promise<Uint8Array>;
    create(body: TemplateCreate): Promise<TemplateOut>;
    /** Its owner only. The fields as they are to become: what is left out is taken away. */
    update(templateId: string, body: TemplateUpdate): Promise<TemplateOut>;
    /** Says who can use the model: `private`, `shared` (with the people and groups in `shares`) or `public`. */
    share(templateId: string, visibility: Visibility, shares?: Share[]): Promise<TemplateOut>;
    /** Goes back to a version, which makes a new one. */
    restore(templateId: string, version: string): Promise<TemplateOut>;
    /** Makes a sub-model a model of its own. */
    promote(templateId: string): Promise<TemplateOut>;
    /** Deletes a model that no analysis uses. A model with sub-models says which one takes its place. */
    delete(templateId: string, { promoteChild }?: {
        promoteChild?: string;
    }): Promise<void>;
}
