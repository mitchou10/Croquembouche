/** A JSON Schema, as a task declares it. */
export type JsonSchema = Record<string, unknown>

/** An instance of a worker that has a task. */
export interface TaskInstance {
  instanceId: string
  /** Which worker it is an instance of (`template_matching`, `ocr`, `gliner`). */
  service: string
  hostname: string | null
  startedAt: string
  lastSeenAt: string
  /** Whether it said it was alive recently enough. */
  online: boolean
}

/** A task a worker declares, in one version, with the instances that have it. */
export interface Task {
  name: string
  version: string
  description: string
  author: string
  /** What it takes, what can be set, and what it gives. */
  inputSchema: JsonSchema
  parameters: JsonSchema
  outputSchema: JsonSchema
  createdAt: string
  instances: TaskInstance[]
  /** How many of its instances are online. */
  online: number
}
