import { computed, ref } from 'vue'
import { fetchEntityTypes } from '../data/api'
import type { EntityTypeInfo } from '../data/mock'

// The types an entity can have, as the backend gives them: loaded once, then shared.
const types = ref<EntityTypeInfo[]>([])
const failed = ref(false)
let loading: Promise<void> | null = null

export function loadEntityTypes(): Promise<void> {
  loading ??= fetchEntityTypes()
    .then((list) => {
      types.value = list
      failed.value = false
    })
    .catch(() => {
      // The page still works, showing the codes: and the next use tries again.
      failed.value = true
      loading = null
    })
  return loading
}

/** For the tests: forget what was loaded. */
export function resetEntityTypes() {
  types.value = []
  failed.value = false
  loading = null
}

const find = (value: string) => types.value.find((t) => t.value === value)

/** What to show for a type: its label, or its code when the backend does not (or not yet) know it. */
export const entityTypeLabel = (value: string) => find(value)?.label ?? value
export const entityTypeDefinition = (value: string) => find(value)?.definition ?? ''

export function useEntityTypes() {
  void loadEntityTypes()

  /** The options of a select: the types, and the one an entity already has if the backend no longer lists it. */
  const optionsFor = (current: string) => [
    ...types.value.map((t) => ({ value: t.value, text: t.label })),
    ...(current && !find(current) ? [{ value: current, text: `${current} (inconnu)` }] : []),
  ]

  return { types, failed, loaded: computed(() => types.value.length > 0), optionsFor }
}
