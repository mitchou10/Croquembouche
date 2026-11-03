import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { groupSeed, type Share } from '../data/mock'
import ShareInput from './ShareInput.vue'

function mountInput(initial: Share[] = [], props: Record<string, unknown> = {}) {
  const wrapper = mount(ShareInput, {
    props: {
      groups: groupSeed,
      modelValue: initial,
      'onUpdate:modelValue': (value: Share[]) => wrapper.setProps({ modelValue: value }),
      ...props,
    },
  })
  return wrapper
}

const tags = (w: ReturnType<typeof mount>) => w.findAll('.share__tags button').map((b) => b.text())
const type = async (w: ReturnType<typeof mount>, text: string) => {
  await w.get('input').setValue(text)
  await w.get('input').trigger('keydown.enter')
}

describe('ShareInput', () => {
  it('takes an e-mail address with Enter, and a group by its name', async () => {
    const wrapper = mountInput()
    await type(wrapper, 'Marie.Dupont@example.org')
    await type(wrapper, 'équipe courriers')
    expect(tags(wrapper)).toEqual(['marie.dupont@example.org', 'Équipe courriers'])
    expect(wrapper.emitted('update:modelValue')!.at(-1)![0]).toEqual([
      { kind: 'email', value: 'marie.dupont@example.org' },
      { kind: 'group', value: 'Équipe courriers' },
    ])
    expect(wrapper.get('input').element.value).toBe('') // ready for the next one
  })

  it('says why when it is neither, and keeps what was typed to correct it', async () => {
    const wrapper = mountInput()
    await type(wrapper, 'marie')
    expect(tags(wrapper)).toEqual([])
    expect(wrapper.get('[role="alert"]').text()).toBe('« marie » n’est ni une adresse e-mail ni un groupe connu.')
    expect(wrapper.get('input').element.value).toBe('marie')
    expect(wrapper.get('input').attributes('aria-invalid')).toBe('true')
    await wrapper.get('input').setValue('marie@example.org') // typing again clears the message
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('takes nobody twice, a group or an address, whatever the case', async () => {
    const wrapper = mountInput()
    await type(wrapper, 'a@b.fr')
    await type(wrapper, 'A@B.FR')
    await type(wrapper, 'Direction')
    await type(wrapper, 'direction')
    expect(tags(wrapper)).toEqual(['a@b.fr', 'Direction'])
    expect(wrapper.find('[role="alert"]').exists()).toBe(false) // not a mistake: already there
  })

  it('takes a blank for nothing, without complaining', async () => {
    const wrapper = mountInput()
    await type(wrapper, '   ')
    expect(tags(wrapper)).toEqual([])
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('takes what was typed when leaving the field, and complains if it is not a recipient', async () => {
    const wrapper = mountInput()
    await wrapper.get('input').setValue('a@b.fr')
    await wrapper.get('input').trigger('blur')
    expect(tags(wrapper)).toEqual(['a@b.fr'])
    await wrapper.get('input').setValue('nope')
    await wrapper.get('input').trigger('blur')
    expect(wrapper.get('[role="alert"]').exists()).toBe(true)
  })

  it('adds a group picked in the browser\'s list at once, but waits for Enter on an address', async () => {
    const wrapper = mountInput()
    await wrapper.get('input').setValue('Direction') // exactly a group, no typing: a pick
    expect(tags(wrapper)).toEqual(['Direction'])
    await wrapper.get('input').setValue('a@b.fr')
    expect(tags(wrapper)).toEqual(['Direction'])
  })

  it('offers the groups that are not chosen yet, with their name', async () => {
    const wrapper = mountInput([{ kind: 'group', value: 'Direction' }])
    const options = wrapper.findAll('datalist option')
    expect(options.map((o) => o.attributes('value'))).toEqual(['Équipe courriers', 'Préfecture de Paris', 'Service contentieux'])
    expect(options[0].attributes('label')).toBe('Groupe · Équipe courriers')
  })

  it('has no list when there is no group', () => {
    const wrapper = mountInput([], { groups: [] })
    expect(wrapper.find('datalist').exists()).toBe(false)
    expect(wrapper.get('input').attributes('list')).toBeUndefined()
  })

  it('takes a recipient away from its tag, or the last one with Backspace in an empty field', async () => {
    const wrapper = mountInput([
      { kind: 'email', value: 'a@b.fr' },
      { kind: 'group', value: 'Direction' },
      { kind: 'email', value: 'c@d.fr' },
    ])
    await wrapper.findAll('.share__tags button')[1].trigger('click')
    expect(tags(wrapper)).toEqual(['a@b.fr', 'c@d.fr'])
    await wrapper.get('input').setValue('xx')
    await wrapper.get('input').trigger('keydown.backspace')
    expect(tags(wrapper)).toEqual(['a@b.fr', 'c@d.fr']) // there is text: Backspace erases the text, not a recipient
    await wrapper.get('input').setValue('')
    await wrapper.get('input').trigger('keydown.backspace')
    expect(tags(wrapper)).toEqual(['a@b.fr'])
  })

  it('tells a screen reader which are groups and which are addresses', () => {
    const wrapper = mountInput([
      { kind: 'email', value: 'a@b.fr' },
      { kind: 'group', value: 'Direction' },
    ])
    const labels = wrapper.findAll('.share__tags button').map((b) => b.attributes('aria-label'))
    expect(labels).toEqual(['Retirer l’adresse a@b.fr', 'Retirer le groupe Direction'])
    expect(wrapper.findAll('.share__tags button')[1].classes()).toContain('share__tag--group')
    expect(wrapper.findAll('.share__tags button')[0].classes()).not.toContain('share__tag--group')
  })

  it('stops at twenty recipients', async () => {
    const full = Array.from({ length: 20 }, (_, i) => ({ kind: 'email' as const, value: `p${i}@b.fr` }))
    const wrapper = mountInput(full)
    await type(wrapper, 'one-more@b.fr')
    expect(tags(wrapper)).toHaveLength(20)
    expect(wrapper.get('[role="alert"]').text()).toBe('20 destinataires au plus.')
  })

  it('keeps what was chosen, but takes nothing more or away, when it is off the table', async () => {
    const wrapper = mountInput([{ kind: 'email', value: 'a@b.fr' }], { disabled: true })
    expect(tags(wrapper)).toEqual(['a@b.fr'])
    expect(wrapper.get('input').attributes('disabled')).toBeDefined()
    expect(wrapper.get('input').attributes('placeholder')).toBe('Visible par tous') // says why, even with recipients kept
    expect(wrapper.get('.share__tags button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.share__box').classes()).toContain('share__box--disabled')
    const empty = mountInput([], { disabled: true })
    expect(empty.get('input').attributes('placeholder')).toBe('Visible par tous')
  })

  it('lets its form ask whether what was typed has been taken', async () => {
    const wrapper = mountInput()
    const exposed = wrapper.vm as unknown as { commit: () => boolean }
    await wrapper.get('input').setValue('a@b.fr')
    expect(exposed.commit()).toBe(true)
    await wrapper.get('input').setValue('nope')
    expect(exposed.commit()).toBe(false)
    await wrapper.get('input').setValue('')
    expect(exposed.commit()).toBe(true)
  })
})
