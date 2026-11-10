// Gives every operation of the OpenAPI document an identifier of its own: `catalogue_create`, `analyses_create`.
// The shared document names an operation after the function of its route, which is unique within a tag (what the Python
// modules are), not within the document; the types of an operation are looked up by this name, so two of one name would
// be one type.
import { readFileSync, writeFileSync } from 'node:fs'

const [from, to] = process.argv.slice(2)
const spec = JSON.parse(readFileSync(from, 'utf8'))
const seen = new Set()
for (const operations of Object.values(spec.paths)) {
  for (const operation of Object.values(operations)) {
    const tag = (operation.tags?.[0] ?? 'default').toLowerCase()
    operation.operationId = `${tag}_${operation.operationId}`
    if (seen.has(operation.operationId)) throw new Error(`Two operations are called ${operation.operationId}`)
    seen.add(operation.operationId)
  }
}
writeFileSync(to, JSON.stringify(spec))
