import { ref } from 'vue'
import { fetchGroups } from '../data/api'
import type { Group } from '../data/mock'

// The groups an analysis can be shared with, as the backend gives them: loaded once, then shared.
const groups = ref<Group[]>([])
let loading: Promise<void> | null = null

export function loadGroups(): Promise<void> {
  loading ??= fetchGroups()
    .then((list) => {
      groups.value = list
    })
    .catch(() => {
      // Sharing with a person still works; the next use tries again.
      loading = null
    })
  return loading
}

/** For the tests: forget what was loaded. */
export function resetGroups() {
  groups.value = []
  loading = null
}

export function useGroups() {
  void loadGroups()
  return { groups }
}
