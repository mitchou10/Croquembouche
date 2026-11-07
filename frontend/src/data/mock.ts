// Placeholder data until the backend exists.

export interface Point {
  /** Fractions (0 to 1) of the image's width and height, so a zone does not depend on the display size. */
  x: number
  y: number
}

/** An area drawn on the model's document: a polygon, which a rectangle is a special case of. */
export interface Zone {
  /** 1-based; always 1 for an image. */
  page: number
  points: Point[]
}

/** A kind of value an entity can be. The list comes from the backend, each with its definition (see data/api.ts). */
export interface EntityTypeInfo {
  /** The code stored on an entity. */
  value: string
  label: string
  definition: string
}

// What the backend would answer for the list of types: stands in for it until there is one.
export const entityTypeSeed: EntityTypeInfo[] = [
  { value: 'text', label: 'Texte', definition: 'Une suite de caractères libre : un nom, une adresse, une référence… La valeur est gardée telle qu’elle est écrite.' },
  { value: 'date', label: 'Date', definition: 'Une date, quelle que soit la façon dont elle est écrite (12/03/2026, 12 mars 2026). Elle est lue et rendue au format AAAA-MM-JJ.' },
  { value: 'integer', label: 'Entier', definition: 'Un nombre sans partie décimale : une quantité, un numéro. Les séparateurs de milliers (espaces, points) sont ignorés.' },
  { value: 'decimal', label: 'Nombre décimal', definition: 'Un nombre avec une partie décimale. La virgule et le point sont acceptés comme séparateur.' },
  { value: 'amount', label: 'Montant', definition: 'Une somme d’argent, avec ou sans devise (1 250,00 €). Le montant et la devise sont extraits séparément.' },
  { value: 'percentage', label: 'Pourcentage', definition: 'Un taux exprimé en pourcentage (20 %). La valeur est rendue sous forme de nombre, 20 pour 20 %.' },
  { value: 'yes_no', label: 'Oui / non', definition: 'Une réponse à deux issues : une case cochée ou non, « oui » ou « non ». Rendue sous forme de booléen.' },
  { value: 'image', label: 'Image', definition: 'Une image sans texte à lire : une signature, un tampon, un logo, une photo. La zone en est recadrée et gardée telle quelle.' },
  { value: 'table', label: 'Tableau', definition: 'Des lignes et des colonnes de valeurs (lignes d’une facture, d’une commande…). La zone entoure tout le tableau.' },
]

/**
 * Something to look for in documents: described by a name and a definition, and optionally pinned to a zone
 * drawn on the model's document (which then serves as an example of where and how it appears).
 */
export interface TemplateEntity {
  id: string
  name: string
  definition: string
  /** The `value` of one of the backend's types. */
  type: string
  /** Samples of what it looks like in a document: « 12/03/2026 », « 1 250,00 € »... a few are enough to show the form. */
  examples: string[]
  /** Optional words that say more of what it is (« verso », « à la main »...). */
  tags: string[]
  zone?: Zone
  /** Identifiers of the users who starred it: an entity can be worth keeping even when the model is not. */
  stars: string[]
}

/**
 * An image or a PDF. Once uploaded it has an `id` and the backend serves an image of each of its `pages` (a PDF's
 * pages are screenshots); `url` is then the first one. Without an `id` it is a single image at `url`.
 */
export interface TemplateDocument {
  id?: string
  name: string
  type: string
  url: string
  /** 1 for an image. */
  pages?: number
}

/** What is said of a page of a model's document: a name and a description, both optional. */
export interface PageFields {
  /** From 1. */
  page: number
  name: string
  description: string
}

/** A page of a model, as the backend gives it: with how it is called (its name, else the model's name and its number). */
export interface TemplatePage extends PageFields {
  label: string
}

export interface TemplateFields {
  name: string
  description: string
  /** Tags: some from the usual list, others made up by whoever filled the form. */
  categories: string[]
  entities: TemplateEntity[]
  /** The pages that were given a name or a description: the others are « name · page N ». */
  pages: PageFields[]
}

export type SuggestionStatus = 'pending' | 'accepted' | 'rejected'

/** A remark on a suggestion, from anyone signed in: the owner, its author, or someone else with a view on it. */
export interface Comment {
  id: string
  authorId: string
  /** What to show of the author: their name. */
  authorName: string
  text: string
  date: string
}

/** A change proposed by someone other than the owner: the owner decides whether it is applied. */
export interface Suggestion {
  id: string
  authorId: string
  authorName: string
  fields: TemplateFields
  message: string
  date: string
  status: SuggestionStatus
  comments: Comment[]
  /** Identifiers of the users who starred it: a way to say « yes, this one » without writing a comment. */
  stars: string[]
}

export interface Template extends TemplateFields {
  id: string
  /** X.Y.Z, kept by the backend: X when the example document changes, Y when what describes the model does, Z when its
   *  entities do. */
  version: string
  /** The model it is a sub-model of (a sub-model has no sub-model), and its name; null for a root. */
  parentId: string | null
  parentName: string | null
  /** The sub-models of a root, by name. */
  children: { id: string; name: string; version: string }[]
  document?: TemplateDocument
  /** Who made it, as the backend knows them (the identifier of their account), and their name to show. */
  ownerId: string
  ownerName: string
  /** One per page of its document, with the default name filled in. */
  pages: TemplatePage[]
  /** Identifiers of the users who starred it. */
  stars: string[]
  suggestions: Suggestion[]
}

/** A version of a model, as it was saved: the list of them is its history. */
export interface TemplateVersion {
  version: string
  date: string
  authorId: string
  authorName: string
  /** The example document it had (versions with the same X have the same one). */
  document?: TemplateDocument
}

export type AnalysisStatus = 'done' | 'running' | 'failed'
/** A use can also have been stopped by its person, which an analysis as a whole is never. */
export type RunStatus = AnalysisStatus | 'cancelled'

/** A group of people an analysis can be shared with: the signed-in user's own (see data/api.ts). */
export interface Group {
  id: string
  name: string
}

/** The demo's groups, with who is in them: what the tests' fake backend answers from. */
export interface GroupSeed extends Group {
  members: number
  memberIds: string[]
}

export const groupSeed: GroupSeed[] = [
  { id: 'g1', name: 'Équipe courriers', members: 12, memberIds: ['alice.martin', 'bob.durand'] },
  { id: 'g2', name: 'Préfecture de Paris', members: 34, memberIds: ['bob.durand', 'dana'] },
  { id: 'g3', name: 'Service contentieux', members: 8, memberIds: ['chloe.petit'] },
  { id: 'g4', name: 'Direction', members: 5, memberIds: ['alice.martin'] },
]

/** Who an analysis is shared with: a person, by e-mail address, or a whole group, by name. */
export interface Share {
  kind: 'email' | 'group'
  value: string
}

/** What an element could be, and how sure the analysis is of it: a model of the analysis, or « other » (no model). */
export interface Classification {
  templateId: string | null
  /** For the classification of a page of a document: the page of the model it looks like (« form X, page 3 »). */
  templatePage?: number | null
  /** And the version (X.Y.Z) of the model it is a page of: a model is looked for in every X it has had. */
  templateVersion?: string | null
  /** 0 to 1. */
  confidence: number
}

/** Something the analysis found in a document: where, and what it could be, the most likely first. */
export interface Detection {
  id: string
  zone: Zone
  classifications: Classification[]
  /** Which entity of the model it is, when known: what the quality of each entity is measured on. */
  entityId?: string | null
  /** Found in the text by the definition of its entity (it has no zone on its model), not by carrying a zone over. */
  foundInText?: boolean
  /** The text read in the zone, once the analysis reads them (OCR): absent until then. */
  text?: string | null
}

/** What the person who ran the analysis decided of a prediction: still to look at, right, wrong, or corrected by hand. */
export type ReviewStatus = 'pending' | 'validated' | 'invalidated' | 'annotated'

export interface Review {
  status: ReviewStatus
  /** For an annotation: the model it is, one of the models of the analysis. */
  templateId?: string
  /** For the annotation of a page: the page of that model, when it has several. */
  templatePage?: number
}

export interface ReviewedDetection extends Detection {
  review: Review
  /** Found by the analysis, or drawn by hand by the person (then it is an annotation from the start). */
  source?: 'analysis' | 'manual'
}

/** What the analysis makes of one page of the document: which page of which model it corresponds to, the likeliest first. */
export interface RunPage {
  /** The page of the document tried, from 1. */
  page: number
  classifications: Classification[]
  review: Review
}

/** One use of an analysis: who ran it, when, how it went, and (for a document tried) what was found in it. */
/** What computing something consumed: electricity (Wh), CO2 (g), water (mL, estimated from the electricity), time (s). */
export interface Consumption {
  durationS: number
  energyWh: number
  co2G: number
  waterMl: number
}

export interface AnalysisRun {
  id: string
  userId: string
  /** What to show of who ran it: their name. */
  userName: string
  /** Whether it was tried on a document, so has a result (which is for whoever ran it to see). */
  hasResult: boolean
  /** The text of the document is read beside the analysis, which does not wait for it: absent for a use from before. */
  ocrStatus?: 'none' | 'running' | 'done' | 'failed'
  /** The entities with no zone are found in that text once it is read: waiting for it, being found, found, or not. */
  findStatus?: 'none' | 'waiting' | 'running' | 'done' | 'failed'
  /** What it consumed, once it has ended: absent when it was not measured. */
  consumption?: Consumption | null
  date: string
  status: RunStatus
  matches: number
  /** The document the analysis was tried on. */
  fileName?: string
  /** What was found in it. Only the person who ran it can see this, an administrator included. */
  detections?: ReviewedDetection[]
  /** Which page of which model each page of the document corresponds to. */
  pages?: RunPage[]
  /** A capture of the document, when the person chose to keep one: null once deleted. */
  screenshot?: TemplateDocument | null
  /** What was decided of that capture once the predictions were looked at: kept, or deleted. */
  fileDecision?: 'kept' | 'deleted'
}

export interface Analysis {
  id: string
  /** False for an analysis one is only told of (named, with its date and status): the rest of it is empty. */
  canOpen: boolean
  name: string
  description: string
  /** Who made it: they, and whoever it is public or shared to, and an administrator, can open it. */
  ownerId: string
  ownerName: string
  /** How many times its page was opened. */
  views: number
  /** Each time it was used, newest first. */
  runs: AnalysisRun[]
  templateIds: string[]
  /** Open to every user: then it has no recipients to name. */
  isPublic: boolean
  shares: Share[]
  date: string
  status: AnalysisStatus
  matches: number
  /** What all its measured uses consumed. */
  consumption?: Consumption
}

// A made-up letter, drawn as an SVG so the demo model has an example document without shipping a file.
export const sampleLetter = `data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
    <rect width="600" height="800" fill="#fff"/>
    <rect x="36" y="48" width="180" height="128" fill="#e1e1fd"/>
    <text x="48" y="96" font-family="sans-serif" font-size="18" font-weight="700" fill="#000091">RÉPUBLIQUE</text>
    <text x="48" y="120" font-family="sans-serif" font-size="18" font-weight="700" fill="#000091">FRANÇAISE</text>
    <text x="48" y="160" font-family="serif" font-size="12" font-style="italic" fill="#161616">Liberté Égalité Fraternité</text>
    <g fill="#ddd"><rect x="48" y="260" width="500" height="10"/><rect x="48" y="290" width="460" height="10"/>
    <rect x="48" y="320" width="500" height="10"/><rect x="48" y="350" width="400" height="10"/>
    <rect x="48" y="410" width="500" height="10"/><rect x="48" y="440" width="480" height="10"/></g>
  </svg>`,
)}`

export const defaultCategories = ['Identité', 'Tampon', 'Signature', 'Code', 'Formulaire', 'Autre']

const letterEntities = (): TemplateEntity[] => [
  { id: 'e1', stars: ['bob.durand', 'chloe.petit'], type: 'text', examples: ['RÉPUBLIQUE FRANÇAISE'], tags: [], name: 'Emblème', definition: 'Le drapeau tricolore et la mention « République française ».', zone: { page: 1, points: [{ x: 0.06, y: 0.06 }, { x: 0.36, y: 0.06 }, { x: 0.36, y: 0.22 }, { x: 0.06, y: 0.22 }] } },
  { id: 'e2', stars: [], type: 'text', examples: ['Liberté Égalité Fraternité'], tags: [], name: 'Devise', definition: 'La devise « Liberté, Égalité, Fraternité » sous le bloc-marque.' },
]

type RawComment = Omit<Comment, 'authorName'>
type RawFields = Omit<TemplateFields, 'pages'>
type RawSuggestion = Omit<Suggestion, 'authorName' | 'comments' | 'fields'> & { comments: RawComment[]; fields: RawFields }
type RawTemplate = Omit<Template, 'ownerName' | 'suggestions' | 'pages' | 'version' | 'parentId' | 'parentName' | 'children'> & { suggestions: RawSuggestion[] }

const rawTemplates: RawTemplate[] = [
  {
    id: 't1',
    name: 'Logo Marianne',
    description: 'Bloc-marque de la République française.',
    categories: ['Identité', 'Officiel'],
    ownerId: 'alice.martin',
    stars: ['bob.durand', 'chloe.petit'],
    entities: letterEntities(),
    document: { name: 'courrier-exemple.svg', type: 'image/svg+xml', url: sampleLetter },
    suggestions: [
      {
        id: 's1',
        authorId: 'bob.durand',
        fields: {
          name: 'Logo Marianne',
          description: 'Bloc-marque de la République française, version couleur.',
          categories: ['Identité', 'Officiel'],
          entities: letterEntities(),
        },
        message: 'Précise qu’il s’agit de la version couleur.',
        date: '2026-11-01',
        status: 'pending',
        stars: ['chloe.petit'],
        comments: [
          { id: 'c1', authorId: 'alice.martin', text: 'Bonne idée, mais la version couleur existe-t-elle en noir et blanc ?', date: '2026-11-02' },
        ],
      },
    ],
  },
  {
    id: 't2',
    name: 'Tampon « Reçu »',
    description: 'Tampon rond apposé sur les accusés de réception.',
    categories: ['Tampon'],
    ownerId: 'bob.durand',
    stars: ['alice.martin'],
    entities: [{ id: 'e3', stars: ['alice.martin'], type: 'date', examples: ['12/03/2026', '1 novembre 2026'], tags: [], name: 'Date de réception', definition: 'La date inscrite au centre du tampon, au format JJ/MM/AAAA.' }],
    suggestions: [],
  },
  {
    id: 't3',
    name: 'Signature type',
    description: 'Signature manuscrite de référence.',
    categories: ['Signature'],
    ownerId: 'alice.martin',
    stars: [],
    entities: [],
    suggestions: [],
  },
  {
    id: 't4',
    name: 'Code QR de suivi',
    description: 'Code QR imprimé en pied de courrier.',
    categories: ['Code'],
    ownerId: 'chloe.petit',
    stars: ['alice.martin', 'bob.durand', 'chloe.petit'],
    entities: [{ id: 'e4', stars: [], type: 'integer', examples: ['20260142', '20259871'], tags: [], name: 'Numéro de dossier', definition: 'Le numéro encodé dans le code QR de suivi.' }],
    suggestions: [],
  },
  {
    id: 't5',
    name: 'Case à cocher',
    description: 'Case cochée dans les formulaires scannés.',
    categories: ['Formulaire'],
    ownerId: 'bob.durand',
    stars: [],
    entities: [],
    suggestions: [],
  },
  {
    id: 't6',
    name: 'Filigrane « Copie »',
    description: 'Filigrane diagonal des copies certifiées.',
    categories: ['Tampon'],
    ownerId: 'chloe.petit',
    stars: ['alice.martin'],
    entities: [],
    suggestions: [],
  },
  {
    id: 't7',
    name: 'Cachet de la poste',
    description: 'Cachet rond oblitérant le timbre, avec la date et le bureau d’émission.',
    categories: ['Tampon'],
    ownerId: 'alice.martin',
    stars: ['bob.durand'],
    suggestions: [],
    entities: [],
  },
  {
    id: 't8',
    name: 'Numéro de dossier imprimé',
    description: 'Numéro à huit chiffres imprimé en haut à droite des courriers de la préfecture.',
    categories: ['Code', 'Officiel'],
    ownerId: 'bob.durand',
    stars: [],
    suggestions: [],
    entities: [],
  },
  {
    id: 't9',
    name: 'Paraphe',
    description: 'Initiales manuscrites apposées en bas de chaque page d’un contrat.',
    categories: ['Signature'],
    ownerId: 'chloe.petit',
    stars: ['alice.martin', 'bob.durand'],
    suggestions: [],
    entities: [],
  },
  {
    id: 't10',
    name: 'Logo CAF',
    description: 'Logotype de la Caisse d’allocations familiales sur les attestations.',
    categories: ['Identité'],
    ownerId: 'alice.martin',
    stars: [],
    suggestions: [],
    entities: [],
  },
  {
    id: 't11',
    name: 'Case « Refusé »',
    description: 'Case cochée indiquant un refus dans les formulaires de demande.',
    categories: ['Formulaire'],
    ownerId: 'chloe.petit',
    stars: [],
    suggestions: [],
    entities: [],
  },
]

// In the demo the name of everyone is their identifier.
export const templates: Template[] = rawTemplates.map((t) => ({
  ...t,
  version: '1.0.0',
  parentId: null,
  parentName: null,
  children: [],
  ownerName: t.ownerId,
  // A demo model's document is one image: one page, which is the model itself.
  pages: t.document ? [{ page: 1, name: '', description: '', label: t.name }] : [],
  suggestions: t.suggestions.map((s) => ({
    ...s,
    authorName: s.authorId,
    fields: { ...s.fields, pages: [] },
    comments: s.comments.map((c) => ({ ...c, authorName: c.authorId })),
  })),
}))

type RawRun = Omit<AnalysisRun, 'userName' | 'hasResult'>
type RawAnalysis = Omit<Analysis, 'canOpen' | 'ownerName' | 'runs'> & { runs: RawRun[] }

const rawAnalyses: RawAnalysis[] = [
  {
    id: 'a1', name: 'Courriers octobre', description: '', ownerId: 'alice.martin', views: 42, isPublic: false, shares: [],
    templateIds: ['t1', 't6'], date: '2026-10-30', status: 'done', matches: 128,
    runs: [
      { id: 'r1', userId: 'alice.martin', date: '2026-10-30', status: 'done', matches: 128, fileName: 'courrier-octobre-1.svg' },
      { id: 'r2', userId: 'alice.martin', date: '2026-10-22', status: 'done', matches: 97, fileName: 'courrier-octobre-2.png' },
      { id: 'r3', userId: 'alice.martin', date: '2026-10-15', status: 'failed', matches: 0 },
      { id: 'r4', userId: 'alice.martin', date: '2026-10-08', status: 'done', matches: 110 },
    ],
  },
  {
    id: 'a2', name: 'Accusés de réception T3', description: 'Tampons des accusés du troisième trimestre, à recouper avec le registre.', ownerId: 'bob.durand', views: 17, isPublic: false,
    shares: [{ kind: 'group', value: 'Équipe courriers' }],
    templateIds: ['t2'], date: '2026-11-02', status: 'running', matches: 41,
    runs: [
      { id: 'r5', userId: 'bob.durand', date: '2026-11-02', status: 'running', matches: 41 },
      { id: 'r6', userId: 'alice.martin', date: '2026-10-28', status: 'done', matches: 52 },
    ],
  },
  {
    id: 'a3', name: 'Formulaires CERFA', description: 'Cases cochées et codes QR des formulaires scannés en octobre.', ownerId: 'chloe.petit', views: 9, isPublic: false, shares: [],
    templateIds: ['t5', 't4'], date: '2026-11-03', status: 'failed', matches: 0,
    runs: [
      { id: 'r7', userId: 'chloe.petit', date: '2026-11-03', status: 'failed', matches: 0 },
      { id: 'r8', userId: 'chloe.petit', date: '2026-11-01', status: 'failed', matches: 0 },
    ],
  },
  {
    id: 'a4', name: 'Contrats signés', description: 'Vérification des signatures sur les contrats de l’année.', ownerId: 'alice.martin', views: 31, isPublic: false,
    shares: [{ kind: 'email', value: 'marie.dupont@example.org' }, { kind: 'group', value: 'Service contentieux' }],
    templateIds: ['t3'], date: '2026-10-21', status: 'done', matches: 87,
    runs: [
      { id: 'r9', userId: 'alice.martin', date: '2026-10-21', status: 'done', matches: 87 },
      { id: 'r10', userId: 'chloe.petit', date: '2026-10-19', status: 'done', matches: 84 },
      { id: 'r11', userId: 'alice.martin', date: '2026-10-02', status: 'done', matches: 80 },
    ],
  },
  {
    id: 'a5', name: 'Attestations CAF', description: '', ownerId: 'alice.martin', views: 120, isPublic: true, shares: [],
    templateIds: ['t10'], date: '2026-10-12', status: 'done', matches: 214,
    runs: [
      { id: 'r12', userId: 'alice.martin', date: '2026-10-12', status: 'done', matches: 214, fileName: 'attestation-caf.png' },
      { id: 'r13', userId: 'dana', date: '2026-10-11', status: 'done', matches: 201, fileName: 'attestation-dana.png' },
      { id: 'r14', userId: 'bob.durand', date: '2026-10-09', status: 'done', matches: 190 },
      { id: 'r15', userId: 'chloe.petit', date: '2026-10-07', status: 'running', matches: 33 },
      { id: 'r16', userId: 'dana', date: '2026-10-03', status: 'failed', matches: 0 },
    ],
  },
  {
    id: 'a6', name: 'Courriers de la poste', description: 'Cachets et numéros de dossier des courriers reçus.', ownerId: 'bob.durand', views: 24, isPublic: false,
    shares: [{ kind: 'email', value: 'paul.martin@example.org' }, { kind: 'group', value: 'Préfecture de Paris' }],
    templateIds: ['t7', 't8'], date: '2026-10-05', status: 'done', matches: 63,
    runs: [
      { id: 'r17', userId: 'bob.durand', date: '2026-10-05', status: 'done', matches: 63 },
      { id: 'r18', userId: 'dana', date: '2026-10-04', status: 'done', matches: 60 },
    ],
  },
  {
    id: 'a7', name: 'Contrats paraphés', description: '', ownerId: 'chloe.petit', views: 5, isPublic: false, shares: [{ kind: 'email', value: 'dana@example.org' }],
    templateIds: ['t9', 't3'], date: '2026-11-03', status: 'running', matches: 12,
    runs: [{ id: 'r19', userId: 'chloe.petit', date: '2026-11-03', status: 'running', matches: 12 }],
  },
  {
    id: 'a8', name: 'Demandes refusées', description: '', ownerId: 'chloe.petit', views: 3, isPublic: false, shares: [],
    templateIds: ['t11'], date: '2026-09-28', status: 'failed', matches: 0,
    runs: [{ id: 'r20', userId: 'chloe.petit', date: '2026-09-28', status: 'failed', matches: 0 }],
  },
]

// In the demo the name of everyone is their identifier, and what is told of an analysis to whoever opens it is all of it.
export const analyses: Analysis[] = rawAnalyses.map((a) => ({
  ...a,
  canOpen: true,
  ownerName: a.ownerId,
  runs: a.runs.map((r) => ({ ...r, userName: r.userId, hasResult: !!r.fileName })),
}))

export const statusLabels: Record<RunStatus, { label: string; type: 'success' | 'info' | 'error' | 'warning' }> = {
  done: { label: 'Terminée', type: 'success' },
  running: { label: 'En cours', type: 'info' },
  failed: { label: 'En échec', type: 'error' },
  cancelled: { label: 'Annulée', type: 'warning' },
}

/**
 * How right the analysis has been on a model, as far as people have said so (validated, invalidated, annotated): there is
 * no set of documents to measure against, the figures grow with every decision.
 */
export interface Quality {
  /** Predictions someone decided on, those nobody looked at yet, and the decisions split into right and wrong. */
  reviewed: number
  pending: number
  correct: number
  wrong: number
  /** What people found that the analysis did not: added by hand, or annotated as this model on another's prediction. */
  missed: number
  /** Null while there is nothing to divide. */
  precision: number | null
  recall: number | null
  f1: number | null
  /** How sure the analysis was, on average, of what turned out right and of what turned out wrong. */
  meanConfidenceCorrect: number | null
  meanConfidenceWrong: number | null
}

export interface TemplateQuality {
  /** The classification of the pages; `exact`: of those rightly taken for a page of the model, the share whose page of it was right too. */
  pages: Quality & { exact: number | null }
  elements: Quality
  entities: (Quality & { id: string; name: string })[]
}

/** The quality on one model among the decisions of one person, or of everyone. */
export interface ModelQuality {
  id: string
  name: string
  pages: Quality & { exact: number | null }
  elements: Quality
}

/** The quality over every model together and model by model, the models with the most decisions first. */
export interface QualityOverview {
  pages: Quality & { exact: number | null }
  elements: Quality
  models: ModelQuality[]
  /** How many people decided something: only for everyone's decisions. */
  reviewers?: number | null
}
