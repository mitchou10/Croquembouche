/**
 * The calls to try an analysis from a terminal, as `curl` commands: sending a document, then reading what was found. The
 * API takes the Keycloak access token of the person (`Authorization: Bearer`), and answers at once with the use, which
 * goes on running: its result is asked for with its `id`. What a use found is its person's alone, so the token is theirs.
 */
export interface CurlOptions {
  /** Where the API is: the address of the page, which forwards `/api` to the backend. */
  origin: string
  analysisId: string
  /** Whether a capture of the document is kept (the checkbox of the page). */
  keepScreenshot: boolean
}

export interface CurlExample {
  /** What it is for. */
  title: string
  command: string
}

export function curlExamples({ origin, analysisId, keepScreenshot }: CurlOptions): CurlExample[] {
  const url = `${origin.replace(/\/$/, '')}/api/analyses/${analysisId}/runs`
  return [
    {
      title: '1. Envoyer le document',
      command: [
        `RUN_ID=$(curl -s -X POST "${url}" \\`,
        '  -H "Authorization: Bearer $TOKEN" \\',
        '  -F "file=@mon-document.pdf" \\',
        `  -F "keepScreenshot=${keepScreenshot}" | jq -r .id)`,
      ].join('\n'),
    },
    {
      title: '2. Lire le résultat',
      command: [`curl -s "${url}/$RUN_ID" \\`, '  -H "Authorization: Bearer $TOKEN" | jq'].join('\n'),
    },
  ]
}
