import { describe, expect, it } from 'vitest'
import { curlExamples } from './curlExample'

const options = { origin: 'https://croquembouche.example.org', analysisId: 'a1b2', keepScreenshot: false }

describe('curlExamples', () => {
  it('sends the document to the analysis, with the token of the person, and keeps the id of the use', () => {
    const [send] = curlExamples(options)

    expect(send.title).toBe('1. Envoyer le document')
    expect(send.command).toBe(
      [
        'RUN_ID=$(curl -s -X POST "https://croquembouche.example.org/api/analyses/a1b2/runs" \\',
        '  -H "Authorization: Bearer $TOKEN" \\',
        '  -F "file=@mon-document.pdf" \\',
        '  -F "keepScreenshot=false" | jq -r .id)',
      ].join('\n'),
    )
  })

  it('then reads the result of that use', () => {
    const [, read] = curlExamples(options)

    expect(read.title).toBe('2. Lire le résultat')
    expect(read.command).toBe(
      ['curl -s "https://croquembouche.example.org/api/analyses/a1b2/runs/$RUN_ID" \\', '  -H "Authorization: Bearer $TOKEN" | jq'].join('\n'),
    )
  })

  it('keeps a capture of the document when asked to', () => {
    expect(curlExamples({ ...options, keepScreenshot: true })[0].command).toContain('-F "keepScreenshot=true"')
  })

  it('does not double the slash when the address ends with one', () => {
    expect(curlExamples({ ...options, origin: 'http://localhost:5173/' })[1].command).toContain('"http://localhost:5173/api/analyses/a1b2/runs/$RUN_ID"')
  })
})
