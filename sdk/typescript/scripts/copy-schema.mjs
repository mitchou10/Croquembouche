// `tsc` does not carry a `.d.ts` that it only reads into its output, and the types of the package point to this one.
import { cpSync, mkdirSync } from 'node:fs'

mkdirSync('dist/generated', { recursive: true })
cpSync('src/generated/schema.d.ts', 'dist/generated/schema.d.ts')
