/** A document: its bytes (`Blob`, a `File`, `Uint8Array`, `ArrayBuffer`) or, in Node, the path of a file. */
export type Document = Blob | Uint8Array | ArrayBuffer | string;
/** The `multipart/form-data` of a request: the document under `file`, and the other fields as text. */
export declare function formWith(document: Document, filename: string | undefined, fields?: Record<string, string | number | boolean | undefined>): Promise<FormData>;
/** For `openapi-fetch`: the body is the form that was made, whatever the typed body says. */
export declare const asForm: (form: FormData) => {
    body: never;
    bodySerializer: () => FormData;
};
