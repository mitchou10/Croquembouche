import { computed, ref } from 'vue'
import { fetchVersion } from '../data/api'

// The version of the application, as the frontend and the backend each say it: the frontend knows its own (it is built
// with it), the backend is asked once. They are the same one when a release is deployed whole, and a difference says
// that one of the two is not up to date.
export const frontendVersion: string = __APP_VERSION__

const backend = ref<string | null>(null)
const failed = ref(false)
let loading: Promise<void> | null = null

export function loadBackendVersion(): Promise<void> {
  loading ??= fetchVersion()
    .then(({ version }) => {
      backend.value = version
      failed.value = false
    })
    .catch(() => {
      // The page still works: the version is just not told, and the next time tries again.
      failed.value = true
      loading = null
    })
  return loading
}

/** For the tests: forget what was loaded. */
export function resetVersions() {
  backend.value = null
  failed.value = false
  loading = null
}

export function useVersions() {
  void loadBackendVersion()
  return {
    frontend: frontendVersion,
    /** What the backend says, « … » while it has not answered, « indisponible » when it cannot. */
    backend: computed(() => backend.value ?? (failed.value ? 'indisponible' : '…')),
    /** Both are known and they are not the same. */
    differ: computed(() => backend.value !== null && backend.value !== frontendVersion),
  }
}
