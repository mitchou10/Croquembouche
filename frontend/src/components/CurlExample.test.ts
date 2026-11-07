import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CurlExample from './CurlExample.vue'

const mounted = (keepScreenshot = false) => mount(CurlExample, { props: { analysisId: 'a1', keepScreenshot } })
const open = async (wrapper: ReturnType<typeof mounted>) => {
  await wrapper.get('[data-testid="curl-button"]').trigger('click')
  return wrapper
}

describe('CurlExample', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('is a button, and the commands are not shown until it is clicked', async () => {
    const wrapper = mounted()
    const button = wrapper.get('[data-testid="curl-button"]')
    expect(button.text()).toBe('Tester avec curl')
    expect(button.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('[data-testid="curl-panel"]').exists()).toBe(false)

    await button.trigger('click')
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('[data-testid="curl-panel"]').exists()).toBe(true)
    await button.trigger('click') // it closes too
    expect(wrapper.find('[data-testid="curl-panel"]').exists()).toBe(false)
  })

  it('shows the command to send a document to this analysis and the one to read its result', async () => {
    const wrapper = await open(mounted())

    const commands = wrapper.findAll('[data-testid="curl-command"]').map((c) => c.text())
    expect(commands).toHaveLength(2)
    expect(commands[0]).toContain(`${window.location.origin}/api/analyses/a1/runs`)
    expect(commands[0]).toContain('-F "file=@mon-document.pdf"')
    expect(commands[0]).toContain('Authorization: Bearer $TOKEN')
    expect(commands[1]).toContain('/api/analyses/a1/runs/$RUN_ID')
  })

  it('follows the capture the page is set to keep, or not', async () => {
    const wrapper = await open(mounted(false))
    expect(wrapper.get('[data-testid="curl-command"]').text()).toContain('keepScreenshot=false')

    await wrapper.setProps({ keepScreenshot: true })
    expect(wrapper.get('[data-testid="curl-command"]').text()).toContain('keepScreenshot=true')
  })

  it('explains the token, the file, and that the result is private to the person', async () => {
    const text = (await open(mounted())).get('[data-testid="curl-panel"]').text()

    expect(text).toContain('jeton d’accès Keycloak')
    expect(text).toContain('20 Mo au plus')
    expect(text).toContain('n’est visible que par la personne qui l’a lancée')
  })

  it('copies a command, and says so for a moment', async () => {
    vi.useFakeTimers()
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = await open(mounted())

    await wrapper.findAll('[data-testid="curl-copy"]')[1].trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('/api/analyses/a1/runs/$RUN_ID'))
    expect(wrapper.findAll('[data-testid="curl-copied"]').map((s) => s.text())).toEqual(['', 'Copié'])
    await vi.advanceTimersByTimeAsync(2100)
    expect(wrapper.findAll('[data-testid="curl-copied"]').map((s) => s.text())).toEqual(['', ''])
    vi.useRealTimers()
  })

  it('says when it could not copy', async () => {
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    const wrapper = await open(mounted())

    await wrapper.get('[data-testid="curl-copy"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="curl-copied"]').text()).toBe('Copie impossible')
  })
})
