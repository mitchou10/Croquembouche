import { DOMWrapper, flushPromises, VueWrapper } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'
import { fakeFetch, resetBackend } from './fakeBackend'

// The pages talk to the backend with `fetch`: in the tests it is the fake one, from the demo data again each time.
beforeEach(() => {
  resetBackend()
  vi.stubGlobal('fetch', fakeFetch)
})

// What an action does reaches the page after the backend has answered: a click is not over until it has.
for (const wrapper of [DOMWrapper, VueWrapper]) {
  const trigger = wrapper.prototype.trigger
  wrapper.prototype.trigger = async function (this: unknown, ...args: Parameters<typeof trigger>) {
    await trigger.apply(this as never, args)
    await flushPromises()
  } as typeof trigger
}
