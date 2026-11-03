import { computed, ref } from 'vue'

// Mocked session: no backend yet, the identifier typed on the login page is the whole identity.
const STORAGE_KEY = 'croquembouche.userId'

function readStoredUserId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function storeUserId(value: string | null) {
  try {
    if (value === null) localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // Storage can be blocked (private window): the session then only lasts until the page is reloaded.
  }
}

const userId = ref<string | null>(readStoredUserId())

// Mocked like the rest of the session: the identifiers that have the administrator's rights. The backend will say.
const ADMINISTRATORS = ['admin']

export function useSession() {
  const isAuthenticated = computed(() => userId.value !== null)
  const isAdmin = computed(() => userId.value !== null && ADMINISTRATORS.includes(userId.value.toLowerCase()))

  /** Returns false (and logs nobody in) when the identifier is blank. */
  function login(identifier: string): boolean {
    const trimmed = identifier.trim()
    if (!trimmed) return false
    userId.value = trimmed
    storeUserId(trimmed)
    return true
  }

  function logout() {
    userId.value = null
    storeUserId(null)
  }

  /** The address an analysis shared « with a person » reaches this user at: mocked, as the rest of the session. */
  const email = computed(() => (userId.value === null ? null : `${userId.value.toLowerCase()}@example.org`))

  return { userId, isAuthenticated, isAdmin, email, login, logout }
}
