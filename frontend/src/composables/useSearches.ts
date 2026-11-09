import { ref } from 'vue'
import * as api from '../data/api'
import type { Search, SearchSummary } from '../data/search'

/**
 * The searches for similar documents: the ones the person has made (kept, to be opened again) and the one that is open. A
 * search is computed by a worker, so it is first running; it is followed until it is over, as the uses of an analysis are.
 */
const searches = ref<SearchSummary[]>([])
const opened = ref<Search | null>(null)
const loaded = ref(false)
const failed = ref(false)

// How often a running search is asked for, and for how long: a worker that has not answered by then is the backend's to
// end as failed, the page only stops asking.
const POLL_MS = 2000
const POLL_LIMIT = 450
const following = new Set<string>()

const summaryOf = ({ neighbours, links: _links, ...summary }: Search): SearchSummary => ({ ...summary, neighbourCount: neighbours.length })

function keep(search: Search | SearchSummary) {
  const summary = 'neighbours' in search ? summaryOf(search) : search
  const known = searches.value.some((s) => s.id === summary.id)
  searches.value = known ? searches.value.map((s) => (s.id === summary.id ? summary : s)) : [summary, ...searches.value]
  if ('neighbours' in search && opened.value?.id === search.id) opened.value = search
}

function follow(id: string) {
  if (following.has(id)) return
  following.add(id)
  let asked = 0
  const tick = async () => {
    let over = ++asked > POLL_LIMIT
    try {
      const search = await api.fetchSearch(id)
      keep(search)
      if (search.status !== 'running') over = true
    } catch (error) {
      // The search is gone (deleted from another window): nothing to follow. Anything else is tried again.
      over ||= error instanceof api.ApiError && error.status === 404
    }
    if (over) following.delete(id)
    else setTimeout(tick, POLL_MS)
  }
  setTimeout(tick, POLL_MS)
}

const reason = (error: unknown) => (error instanceof api.ApiError ? error.message : 'Le serveur est injoignable.')

export function resetSearches() {
  searches.value = []
  opened.value = null
  loaded.value = false
  failed.value = false
  following.clear()
}

export function useSearches() {
  /** The searches of the person, the newest first. */
  async function load() {
    try {
      searches.value = await api.fetchSearches()
      failed.value = false
    } catch {
      failed.value = true
    }
    loaded.value = true
  }

  /** Sends a file to be looked for among `templateIds` (null: every model the person can see). Throws an `ApiError`. */
  async function start(file: File, k: number, templateIds: string[] | null): Promise<Search> {
    const search = await api.postSearch(file, k, templateIds)
    opened.value = search
    keep(search)
    if (search.status === 'running') follow(search.id)
    return search
  }

  /** Opens a search that was made: what it found, and what it consumed. Throws an `ApiError` (404: it is not there). */
  async function open(id: string): Promise<Search> {
    if (opened.value?.id !== id) opened.value = null
    const search = await api.fetchSearch(id)
    opened.value = search
    keep(search)
    if (search.status === 'running') follow(search.id)
    return search
  }

  /** Deletes a search. Returns the reason when it was refused. */
  async function remove(id: string): Promise<string> {
    try {
      await api.deleteSearch(id)
    } catch (error) {
      if (!(error instanceof api.ApiError && error.status === 404)) return reason(error)
    }
    searches.value = searches.value.filter((s) => s.id !== id)
    if (opened.value?.id === id) opened.value = null
    return ''
  }

  return { searches, opened, loaded, failed, load, start, open, remove, reason }
}
