import { entityTypeSeed, groupSeed, type EntityTypeInfo, type Group } from './mock'

// The calls the backend will answer. Until it exists they return the demo data, after the delay of a network.

/** GET /api/entity-types */
export async function fetchEntityTypes(): Promise<EntityTypeInfo[]> {
  await Promise.resolve()
  return structuredClone(entityTypeSeed)
}

/** GET /api/groups: the groups an analysis can be shared with. */
export async function fetchGroups(): Promise<Group[]> {
  await Promise.resolve()
  return structuredClone(groupSeed)
}
