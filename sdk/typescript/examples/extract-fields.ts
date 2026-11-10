// Lit les champs d'un document avec une analyse déjà créée : `node extract-fields.ts scan.pdf <id de l'analyse>`.
// L'application s'authentifie avec son propre compte de service (voir docs/sdk.md).
import { Croquembouche, keycloakTokenUrl } from 'croquembouche-sdk'

const [document, analysisId] = process.argv.slice(2)
if (!document || !analysisId) throw new Error('Usage: extract-fields.ts <document> <analysis id>')

const client = new Croquembouche(process.env.CROQUEMBOUCHE_URL!, {
  tokenUrl: keycloakTokenUrl(process.env.KEYCLOAK_URL!, process.env.KEYCLOAK_REALM ?? 'croquembouche'),
  clientId: process.env.CLIENT_ID!,
  clientSecret: process.env.CLIENT_SECRET!,
})

const run = await client.analyses.run(analysisId, document)
const result = await run.wait({ timeoutMs: 120_000 })
for (const element of result.elements) {
  const name = element.entity?.name ?? '(entité inconnue)'
  console.log(`${name}: ${JSON.stringify(element.text)} (${Math.round(element.confidence * 100)} %, page ${element.zone.page})`)
}
