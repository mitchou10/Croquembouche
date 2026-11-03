import { describe, expect, it } from 'vitest'
import { groupSeed } from '../data/mock'
import { describeShares, parseShare, sameShare } from './shares'

describe('parseShare', () => {
  it('takes an e-mail address, trimmed and in lower case', () => {
    expect(parseShare('  Marie.Dupont@Example.ORG ', groupSeed)).toEqual({ kind: 'email', value: 'marie.dupont@example.org' })
  })

  it('takes the name of a group in the spelling of the backend, whatever the case typed', () => {
    expect(parseShare('équipe COURRIERS', groupSeed)).toEqual({ kind: 'group', value: 'Équipe courriers' })
    expect(parseShare('Direction', groupSeed)).toEqual({ kind: 'group', value: 'Direction' })
  })

  it.each(['', '   ', 'marie', 'marie@', '@example.org', 'marie@example', 'marie dupont@example.org', 'Un groupe inconnu'])(
    'is neither an address nor a group: %j',
    (text) => {
      expect(parseShare(text, groupSeed)).toBeNull()
    },
  )

  it('has no group to name when there are none', () => {
    expect(parseShare('Direction', [])).toBeNull()
  })
})

describe('sameShare', () => {
  it('is the same kind and the same value, case aside', () => {
    expect(sameShare({ kind: 'email', value: 'a@b.fr' }, { kind: 'email', value: 'A@B.fr' })).toBe(true)
    expect(sameShare({ kind: 'email', value: 'a@b.fr' }, { kind: 'group', value: 'a@b.fr' })).toBe(false)
    expect(sameShare({ kind: 'group', value: 'Direction' }, { kind: 'group', value: 'Direction' })).toBe(true)
  })
})

describe('describeShares', () => {
  it('counts the people and the groups, in the singular and in the plural', () => {
    const email = (v: string) => ({ kind: 'email' as const, value: v })
    const group = (v: string) => ({ kind: 'group' as const, value: v })
    expect(describeShares([])).toBe('')
    expect(describeShares([email('a@b.fr')])).toBe('1 personne')
    expect(describeShares([email('a@b.fr'), email('c@d.fr')])).toBe('2 personnes')
    expect(describeShares([group('Direction')])).toBe('1 groupe')
    expect(describeShares([email('a@b.fr'), group('x'), group('y')])).toBe('1 personne et 2 groupes')
  })
})
