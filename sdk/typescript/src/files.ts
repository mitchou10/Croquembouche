// Documents to send: what they can be given as, and the form the API takes them in.

/** A document: its bytes (`Blob`, a `File`, `Uint8Array`, `ArrayBuffer`) or, in Node, the path of a file. */
export type Document = Blob | Uint8Array | ArrayBuffer | string

const TYPES: Record<string, string> = {
  pdf: 'application/pdf',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
}

const mimeOf = (name: string) => TYPES[name.split('.').pop()?.toLowerCase() ?? ''] ?? 'application/octet-stream'

/** The `multipart/form-data` of a request: the document under `file`, and the other fields as text. */
export async function formWith(
  document: Document,
  filename: string | undefined,
  fields: Record<string, string | number | boolean | undefined> = {},
): Promise<FormData> {
  let name = filename
  let blob: Blob
  if (typeof document === 'string') {
    const { readFile } = await import('node:fs/promises')
    const { basename } = await import('node:path')
    name ??= basename(document)
    blob = new Blob([new Uint8Array(await readFile(document))])
  } else if (document instanceof Blob) {
    name ??= (document as File).name || undefined
    blob = document
  } else {
    blob = new Blob([document instanceof ArrayBuffer ? document : (document.slice().buffer as ArrayBuffer)])
  }
  name ??= 'document'
  const form = new FormData()
  form.append('file', blob.type ? blob : new Blob([blob], { type: mimeOf(name) }), name)
  for (const [key, value] of Object.entries(fields)) if (value !== undefined) form.append(key, String(value))
  return form
}

/** For `openapi-fetch`: the body is the form that was made, whatever the typed body says. */
export const asForm = (form: FormData) => ({ body: {} as never, bodySerializer: () => form })
