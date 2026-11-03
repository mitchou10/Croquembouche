import { computed, ref } from 'vue'

// The session lives on the backend (a cookie the page cannot read): the page only asks who is signed in.
interface Me {
  user_id: string
  email: string
  first_name: string
  last_name: string
  is_admin: boolean
}

// The identifier of the account (what the backend knows them by), and the name to show for it.
const userId = ref<string | null>(null)
const displayName = ref<string | null>(null)
const isAdmin = ref(false)
const email = ref<string | null>(null)

let loading: Promise<void> | null = null

/** Records who is signed in; `load` does it from the backend, tests do it by hand. */
function setUser(id: string | null, details: { isAdmin?: boolean; email?: string; name?: string } = {}) {
  userId.value = id
  displayName.value = id === null ? null : (details.name ?? id)
  isAdmin.value = id !== null && (details.isAdmin ?? false)
  email.value = id === null ? null : (details.email ?? `${id.toLowerCase()}@example.org`)
  // Whoever sets it, the session is known: the backend need not be asked.
  loading = Promise.resolve()
}

async function fetchMe() {
  try {
    const response = await fetch('/api/auth/me', { credentials: 'same-origin' })
    if (!response.ok) return setUser(null)
    const me = (await response.json()) as Me
    const name = [me.first_name, me.last_name].filter(Boolean).join(' ')
    setUser(me.user_id, { isAdmin: me.is_admin, email: me.email, name: name || me.email || me.user_id })
  } catch {
    // The backend cannot be reached: nobody is signed in as far as the page can tell.
    setUser(null)
  }
}

export function useSession() {
  const isAuthenticated = computed(() => userId.value !== null)

  /** Asks the backend who is signed in, once: the router waits for it before deciding where a visitor may go. */
  function load(): Promise<void> {
    loading ??= fetchMe()
    return loading
  }

  /** Sends the browser to Keycloak; it comes back to `redirect` (an in-app path) once signed in. */
  function login(redirect = '/catalogue') {
    const path = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/catalogue'
    window.location.assign(`/api/auth/login?redirect=${encodeURIComponent(path)}`)
  }

  /** Ends the session on the backend, then goes through Keycloak's own sign-out, which returns to the landing page. */
  async function logout() {
    let destination = '/'
    try {
      const response = await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
      if (response.ok) destination = ((await response.json()) as { redirectUrl: string }).redirectUrl
    } catch {
      // Signed out here all the same.
    }
    setUser(null)
    window.location.assign(destination)
  }

  return { userId, displayName, isAuthenticated, isAdmin, email, setUser, load, login, logout }
}
