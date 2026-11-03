import { beforeEach, vi } from 'vitest'
import { fakeFetch, resetBackend } from './fakeBackend'

// The pages talk to the backend with `fetch`: in the tests it is the fake one, from the demo data again each time.
beforeEach(() => {
  resetBackend()
  vi.stubGlobal('fetch', fakeFetch)
})
