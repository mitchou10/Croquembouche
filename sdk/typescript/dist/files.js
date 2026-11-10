// Documents to send: what they can be given as, and the form the API takes them in.
const TYPES = {
    pdf: 'application/pdf',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp',
    gif: 'image/gif',
};
const mimeOf = (name) => TYPES[name.split('.').pop()?.toLowerCase() ?? ''] ?? 'application/octet-stream';
/** The `multipart/form-data` of a request: the document under `file`, and the other fields as text. */
export async function formWith(document, filename, fields = {}) {
    let name = filename;
    let blob;
    if (typeof document === 'string') {
        const { readFile } = await import('node:fs/promises');
        const { basename } = await import('node:path');
        name ??= basename(document);
        blob = new Blob([new Uint8Array(await readFile(document))]);
    }
    else if (document instanceof Blob) {
        name ??= document.name || undefined;
        blob = document;
    }
    else {
        blob = new Blob([document instanceof ArrayBuffer ? document : document.slice().buffer]);
    }
    name ??= 'document';
    const form = new FormData();
    form.append('file', blob.type ? blob : new Blob([blob], { type: mimeOf(name) }), name);
    for (const [key, value] of Object.entries(fields))
        if (value !== undefined)
            form.append(key, String(value));
    return form;
}
/** For `openapi-fetch`: the body is the form that was made, whatever the typed body says. */
export const asForm = (form) => ({ body: {}, bodySerializer: () => form });
