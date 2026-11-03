import type { Group, Share } from '../data/mock'

export const MAX_SHARES = 20

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * What was typed, as a recipient: an e-mail address (kept in lower case), or the name of a group (in the spelling the
 * backend gives it, whatever the case typed). Null when it is neither.
 */
export function parseShare(text: string, groups: Group[]): Share | null {
  const trimmed = text.trim()
  if (EMAIL.test(trimmed)) return { kind: 'email', value: trimmed.toLowerCase() }
  const group = groups.find((g) => g.name.toLowerCase() === trimmed.toLowerCase())
  return group ? { kind: 'group', value: group.name } : null
}

export const sameShare = (a: Share, b: Share) => a.kind === b.kind && a.value.toLowerCase() === b.value.toLowerCase()

/** « 2 personnes et 1 groupe », for a short summary. */
export function describeShares(shares: Share[]): string {
  const people = shares.filter((s) => s.kind === 'email').length
  const groups = shares.length - people
  const part = (n: number, one: string, many: string) => (n ? [`${n} ${n > 1 ? many : one}`] : [])
  return [...part(people, 'personne', 'personnes'), ...part(groups, 'groupe', 'groupes')].join(' et ')
}
