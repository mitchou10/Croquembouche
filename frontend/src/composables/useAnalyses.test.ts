import { beforeEach, describe, expect, it, vi } from 'vitest'
import { backendAnalysis, fakeFetch } from '../test/fakeBackend'
import { loadAnalyses, resetAnalyses, statsOf, useAnalyses } from './useAnalyses'
import { loadCatalogue, resetCatalogue } from './useCatalogue'
import { useSession } from './useSession'

// Who asks decides what the backend answers: each describe starts again from the demo analyses as someone sees them.
const asUser = async (user: string | null = 'alice.martin', details: { isAdmin?: boolean } = {}) => {
  resetAnalyses()
  resetCatalogue()
  useSession().setUser(user, details)
  await loadAnalyses()
}

const png = (name = 'scan.png') => new File(['x'], name, { type: 'image/png' })
const pdf = (name = 'scan.pdf') => new File(['x'], name, { type: 'application/pdf' })
const input = {
  name: '  Contrats  ',
  description: '  Les contrats de l’année.  ',
  templateIds: ['t1', 't3'],
  isPublic: false,
  shares: [
    { kind: 'email' as const, value: 'marie@example.org' },
    { kind: 'group' as const, value: 'Direction' },
  ],
}

describe('the analyses, as the backend gives them', () => {
  beforeEach(() => asUser())

  it('are loaded once, every one of them', async () => {
    const { analyses, total } = useAnalyses()
    expect(total.value).toBe(analyses.value.length)
    expect(analyses.value.length).toBeGreaterThan(5)
    const calls = vi.fn(fakeFetch)
    vi.stubGlobal('fetch', calls)
    await loadAnalyses()
    expect(calls).not.toHaveBeenCalled()
  })

  it('start empty, and are asked for again later, when the backend cannot be reached', async () => {
    resetAnalyses()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const { analyses, failed } = useAnalyses()
    await loadAnalyses()
    expect(analyses.value).toEqual([])
    expect(failed.value).toBe(true)
    vi.stubGlobal('fetch', fakeFetch)
    await loadAnalyses()
    expect(failed.value).toBe(false)
    expect(analyses.value.length).toBeGreaterThan(5)
  })

  it('give the names of the models of an analysis, or say one is unknown', async () => {
    await loadCatalogue()
    const { find, modelNames } = useAnalyses()
    expect(modelNames(find('a1')!)).toEqual(['Logo Marianne', 'Filigrane « Copie »'])
    expect(modelNames({ templateIds: ['nope'] })).toEqual(['Modèle inconnu'])
  })
})

describe('creating an analysis', () => {
  beforeEach(() => asUser('chloe.petit'))

  it('makes one that is running, with its first use, first in the list', async () => {
    const { analyses, createAnalysis } = useAnalyses()
    const before = analyses.value.length
    const created = await createAnalysis({ ...input, shares: [{ kind: 'email', value: 'marie@example.org' }, { kind: 'group', value: 'Service contentieux' }] })
    expect(created).toMatchObject({ name: 'Contrats', description: 'Les contrats de l’année.', ownerId: 'chloe.petit', views: 0, status: 'running', matches: 0, canOpen: true })
    expect(created.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(created.runs).toHaveLength(1)
    expect(created.runs[0]).toMatchObject({ userId: 'chloe.petit', status: 'running', matches: 0 })
    expect(statsOf([created])).toEqual({ views: 0, uses: 1, done: 0, running: 1, failed: 0 })
    expect(analyses.value).toHaveLength(before + 1)
    expect(analyses.value[0].id).toBe(created.id)
    expect(created.shares).toHaveLength(2)
  })

  it('keeps no recipient for an analysis that is public: it is for everyone', async () => {
    const created = await useAnalyses().createAnalysis({ ...input, isPublic: true })
    expect(created).toMatchObject({ isPublic: true, shares: [] })
  })

  it('may have no description and no recipient', async () => {
    expect(await useAnalyses().createAnalysis({ ...input, description: '', shares: [] })).toMatchObject({ description: '', shares: [], isPublic: false })
  })

  it('says why the backend refuses it', async () => {
    await expect(useAnalyses().createAnalysis({ ...input, name: '  ' })).rejects.toThrow('Donnez un nom')
  })
})

describe('who can open an analysis', () => {
  const openedBy = async (who: string | null, details: { isAdmin?: boolean } = {}) => {
    await asUser(who, details)
    return useAnalyses().accessible.value.map((a) => a.id)
  }

  it('is its owner, whatever it is, and anyone when it is public', async () => {
    // alice.martin made a1, a4 and a5; a5 is public.
    expect(await openedBy('alice.martin')).toEqual(expect.arrayContaining(['a1', 'a4', 'a5']))
    expect(await openedBy('chloe.petit')).toEqual(expect.arrayContaining(['a3', 'a7', 'a8', 'a5']))
    expect(await openedBy('someone.new')).toEqual(['a5']) // only the public one
  })

  it('is the people it is shared with, by e-mail address', async () => {
    expect(await openedBy('dana')).toContain('a7') // shared with dana@example.org
    expect(await openedBy('bob.durand')).not.toContain('a7')
  })

  it('is the members of the groups it is shared with', async () => {
    expect(await openedBy('alice.martin')).toContain('a2') // « Équipe courriers »
    expect(await openedBy('dana')).toContain('a6') // « Préfecture de Paris »
    expect(await openedBy('chloe.petit')).not.toContain('a2')
  })

  it('is every analysis for an administrator, and none for no one signed in', async () => {
    expect(await openedBy('admin', { isAdmin: true })).toHaveLength(useAnalyses().total.value)
    expect(await openedBy(null)).toEqual([])
  })

  it('names the others and says so, without what is in them', async () => {
    await asUser('dana')
    const closed = useAnalyses().find('a3')!
    expect(closed).toMatchObject({ canOpen: false, name: 'Formulaires CERFA', description: '', runs: [], templateIds: [], views: 0 })
    expect(useAnalyses().canAccess(closed)).toBe(false)
  })

  it('shows the recipients to the owner and an administrator only', async () => {
    await asUser('alice.martin')
    expect(useAnalyses().find('a4')!.shares.length).toBeGreaterThan(0)
    await asUser('dana')
    expect(useAnalyses().find('a7')!.shares).toEqual([]) // dana can open a7, not see who else can
    await asUser('admin', { isAdmin: true })
    expect(useAnalyses().find('a4')!.shares.length).toBeGreaterThan(0)
  })
})

describe('the views of an analysis', () => {
  it('counts one more each time someone who can open it looks at it', async () => {
    await asUser('alice.martin')
    const { find, registerView } = useAnalyses()
    expect(find('a1')!.views).toBe(42)
    expect(await registerView('a1')).toBe(true)
    expect(await registerView('a1')).toBe(true)
    expect(find('a1')!.views).toBe(44)
  })

  it('counts nothing for someone who cannot open it, or for an analysis that does not exist', async () => {
    await asUser('dana')
    const { registerView, actionError } = useAnalyses()
    expect(await registerView('a1')).toBe(false)
    expect(actionError.value).toBe('Not found')
    expect(backendAnalysis('a1').views).toBe(42)
    expect(await registerView('nope')).toBe(false)
  })
})

describe('statsOf', () => {
  beforeEach(() => asUser('admin', { isAdmin: true }))

  it('sums the views and the uses, and counts the uses by state', () => {
    const { analyses, find } = useAnalyses()
    expect(statsOf([find('a1')!])).toEqual({ views: 42, uses: 4, done: 3, running: 0, failed: 1 })
    expect(statsOf([find('a5')!])).toEqual({ views: 120, uses: 5, done: 3, running: 1, failed: 1 })
    expect(statsOf(analyses.value)).toEqual({ views: 251, uses: 20, done: 12, running: 3, failed: 5 })
  })

  it('is all zeros for nothing, and its states add up to the uses', () => {
    expect(statsOf([])).toEqual({ views: 0, uses: 0, done: 0, running: 0, failed: 0 })
    const s = statsOf(useAnalyses().analyses.value)
    expect(s.done + s.running + s.failed).toBe(s.uses)
  })
})

describe('trying an analysis on a document', () => {
  beforeEach(() => asUser('alice.martin'))
  const analysisOf = (id: string) => useAnalyses().find(id)!

  it('makes a use of it, one\'s own and done, with what was found still to be looked at', async () => {
    const before = analysisOf('a1').runs.length
    const run = (await useAnalyses().startRun('a1', png(), { saveScreenshot: true }))!
    expect(analysisOf('a1').runs).toHaveLength(before + 1)
    expect(analysisOf('a1').runs[0].id).toBe(run.id)
    expect(run).toMatchObject({ userId: 'alice.martin', status: 'done', fileName: 'scan.png', hasResult: true })
    expect(run.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(run.matches).toBe(run.detections!.length)
    for (const d of run.detections!) expect(d.review).toEqual({ status: 'pending' })
    expect(run.page!.review).toEqual({ status: 'pending' })
    // What the analysis counts of its uses is read again.
    expect(statsOf([analysisOf('a1')])).toMatchObject({ uses: before + 1 })
    expect(analysisOf('a1').matches).toBeGreaterThanOrEqual(128 + run.matches)
  })

  it('keeps the screenshots of the document when asked to, a PDF\'s pages too, and none otherwise', async () => {
    const { startRun } = useAnalyses()
    expect((await startRun('a1', png(), { saveScreenshot: true }))!.screenshot).toMatchObject({ name: 'scan.png', type: 'image/png', pages: 1 })
    expect((await startRun('a1', pdf(), { saveScreenshot: true }))!.screenshot).toMatchObject({ type: 'application/pdf', pages: 3 })
    expect((await startRun('a1', png(), { saveScreenshot: false }))!.screenshot).toBeNull()
  })

  it('is for whoever can open the analysis, and refused to anyone else with the reason', async () => {
    await asUser('dana')
    const { startRun, actionError } = useAnalyses()
    expect(await startRun('a5', png(), { saveScreenshot: false })).not.toBeNull() // public
    expect(await startRun('a6', png(), { saveScreenshot: false })).not.toBeNull() // her group
    expect(await startRun('a3', png(), { saveScreenshot: false })).toBeNull()
    expect(actionError.value).toBe('Not found')
    expect(await startRun('nope', png(), { saveScreenshot: false })).toBeNull()
  })

  it('is refused for a document that is not an image or a PDF', async () => {
    const before = analysisOf('a1').runs.length
    const { startRun, actionError } = useAnalyses()
    expect(await startRun('a1', new File(['x'], 'notes.txt', { type: 'text/plain' }), { saveScreenshot: true })).toBeNull()
    expect(actionError.value).toContain('PDF')
    expect(analysisOf('a1').runs).toHaveLength(before)
  })
})

describe('who sees the result of a use', () => {
  const own = () => useAnalyses().find('a1')!.runs.find((r) => r.id === 'r1')! // alice.martin's, with a result and a capture

  it('is the person who ran it', async () => {
    await asUser('alice.martin')
    const { canSeeResult, ownsRun } = useAnalyses()
    expect(ownsRun(own())).toBe(true)
    expect(canSeeResult(own())).toBe(true)
    expect(own().screenshot).toMatchObject({ name: 'courrier-octobre-1.svg', type: 'image/svg+xml' })
    expect(own().detections![0].review).toEqual({ status: 'validated' }) // the demo's first element
  })

  it('is not someone else, who can open the analysis: the backend does not send it, but says there is one', async () => {
    await asUser('dana')
    const theirs = useAnalyses().find('a5')!.runs.find((r) => r.id === 'r12')! // alice's, on a public analysis
    expect(useAnalyses().canSeeResult(theirs)).toBe(false)
    expect(theirs).toMatchObject({ hasResult: true, userName: 'alice.martin' })
    expect(theirs.detections).toBeUndefined()
    expect(theirs.fileName).toBeUndefined()
  })

  it('is not an administrator either, though they can open the analysis; but is for the uses they ran', async () => {
    await asUser('admin', { isAdmin: true })
    const { canAccess, canSeeResult, ownsRun, startRun, find } = useAnalyses()
    expect(canAccess(find('a1')!)).toBe(true)
    expect(ownsRun(own())).toBe(false)
    expect(canSeeResult(own())).toBe(false)
    expect(canSeeResult((await startRun('a1', png(), { saveScreenshot: false }))!)).toBe(true)
  })

  it('is no one, signed out, and has nothing to see for a use that stored no result', async () => {
    await asUser('alice.martin')
    const without = useAnalyses().find('a1')!.runs.find((r) => r.id === 'r3')!
    expect(useAnalyses().canSeeResult(without)).toBe(false)
    expect(without.hasResult).toBe(false)
    useSession().setUser(null)
    expect(useAnalyses().canSeeResult(own())).toBe(false)
  })
})

describe('looking at the predictions', () => {
  beforeEach(() => asUser('alice.martin'))

  /** A use of the demo analysis a1 in which something was found (a document the made-up analysis finds elements in). */
  const rich = async () => {
    for (let i = 0; i < 300; i++) {
      const run = await useAnalyses().startRun('a1', png(`revue-${i}.png`), { saveScreenshot: true })
      if (run && run.detections!.length >= 2) return run
    }
    throw new Error('no document with two elements')
  }
  const current = (runId: string) => useAnalyses().findRun('a1', runId)!

  it('confirms a prediction, or rejects it, or annotates it with a model of the analysis', async () => {
    const { reviewDetection } = useAnalyses()
    const run = await rich()
    const [first, second] = run.detections!
    expect(await reviewDetection('a1', run.id, first.id, { status: 'validated' })).toBe(true)
    expect(current(run.id).detections![0].review).toEqual({ status: 'validated' })
    await reviewDetection('a1', run.id, second.id, { status: 'invalidated' })
    expect(current(run.id).detections![1].review).toEqual({ status: 'invalidated' })
    await reviewDetection('a1', run.id, first.id, { status: 'annotated', templateId: 't6' })
    expect(current(run.id).detections![0].review).toEqual({ status: 'annotated', templateId: 't6' })
  })

  it('keeps no model with a decision that is not an annotation, and takes a decision back', async () => {
    const { reviewDetection } = useAnalyses()
    const run = await rich()
    const id = run.detections![0].id
    await reviewDetection('a1', run.id, id, { status: 'annotated', templateId: 't1' })
    await reviewDetection('a1', run.id, id, { status: 'validated', templateId: 't1' })
    expect(current(run.id).detections![0].review).toEqual({ status: 'validated' })
    await reviewDetection('a1', run.id, id, { status: 'pending' })
    expect(current(run.id).detections![0].review).toEqual({ status: 'pending' })
  })

  it('is refused an annotation with a model that is not one of the analysis, with the reason', async () => {
    const { reviewDetection, actionError } = useAnalyses()
    const run = await rich()
    const id = run.detections![0].id
    expect(await reviewDetection('a1', run.id, id, { status: 'annotated', templateId: 't3' })).toBe(false) // in the catalogue, not in a1
    expect(actionError.value).toContain('modèles de l’analyse')
    expect(await reviewDetection('a1', run.id, id, { status: 'annotated' })).toBe(false)
    expect(current(run.id).detections![0].review).toEqual({ status: 'pending' })
  })

  it('is for one\'s own results only: not for someone else, an administrator included', async () => {
    const run = await rich()
    const id = run.detections![0].id
    for (const [who, details] of [['admin', { isAdmin: true }], ['dana', {}]] as const) {
      useSession().setUser(who, details)
      expect(await useAnalyses().reviewDetection('a1', run.id, id, { status: 'validated' })).toBe(false)
    }
    expect(useAnalyses().actionError.value).toBe('Not found')
    useSession().setUser('alice.martin')
    expect(current(run.id).detections![0].review).toEqual({ status: 'pending' })
  })

  it('is refused for an element, a use or an analysis that does not exist', async () => {
    const { reviewDetection } = useAnalyses()
    const run = await rich()
    expect(await reviewDetection('a1', run.id, 'nope', { status: 'validated' })).toBe(false)
    expect(await reviewDetection('a1', 'nope', 'd1', { status: 'validated' })).toBe(false)
    expect(await reviewDetection('nope', run.id, 'd1', { status: 'validated' })).toBe(false)
  })

  it('counts how many predictions have been looked at, the page\'s included', async () => {
    const { reviewDetection, reviewPage, reviewProgress } = useAnalyses()
    const run = await rich()
    const total = run.detections!.length + 1 // its elements, and its page
    expect(reviewProgress(run)).toEqual({ total, reviewed: 0 })
    await reviewDetection('a1', run.id, run.detections![0].id, { status: 'validated' })
    await reviewPage('a1', run.id, { status: 'validated' })
    expect(reviewProgress(current(run.id))).toEqual({ total, reviewed: 2 })
    await reviewDetection('a1', run.id, run.detections![0].id, { status: 'pending' })
    expect(reviewProgress(current(run.id)).reviewed).toBe(1)
    expect(reviewProgress(useAnalyses().find('a1')!.runs.find((r) => r.id === 'r3')!)).toEqual({ total: 0, reviewed: 0 })
  })

  it('classifies the page: confirmed, rejected, annotated with a model of the analysis, or taken back', async () => {
    const { reviewPage, actionError } = useAnalyses()
    const run = await rich()
    expect(run.page!.classifications.length).toBeGreaterThan(1)
    expect(await reviewPage('a1', run.id, { status: 'validated' })).toBe(true)
    expect(current(run.id).page!.review).toEqual({ status: 'validated' })
    await reviewPage('a1', run.id, { status: 'annotated', templateId: 't6' })
    expect(current(run.id).page!.review).toEqual({ status: 'annotated', templateId: 't6' })
    expect(await reviewPage('a1', run.id, { status: 'annotated', templateId: 't3' })).toBe(false)
    expect(actionError.value).toContain('modèles de l’analyse')
    await reviewPage('a1', run.id, { status: 'pending' })
    expect(current(run.id).page!.review).toEqual({ status: 'pending' })
    expect(await reviewPage('a1', 'r3', { status: 'validated' })).toBe(false) // a use with no result has no page
  })
})

describe('the elements added by hand', () => {
  const square = { page: 1, points: [{ x: 0.1, y: 0.1 }, { x: 0.4, y: 0.1 }, { x: 0.4, y: 0.4 }, { x: 0.1, y: 0.4 }] }
  beforeEach(() => asUser('alice.martin'))
  const fresh = async () => (await useAnalyses().startRun('a1', png(), { saveScreenshot: true }))!
  const current = (runId: string) => useAnalyses().findRun('a1', runId)!

  it('adds an element annotated with a model of the analysis, after what the analysis found, already looked at', async () => {
    const { addElement } = useAnalyses()
    const run = await fresh()
    const found = run.detections!.length
    expect(await addElement('a1', run.id, { zone: square, templateId: 't6' })).toBe(true)
    expect(await addElement('a1', run.id, { zone: square, templateId: 't1' })).toBe(true)
    const detections = current(run.id).detections!
    expect(detections).toHaveLength(found + 2)
    expect(detections[found]).toMatchObject({ source: 'manual', zone: square, review: { status: 'annotated', templateId: 't6' }, classifications: [{ templateId: 't6', confidence: 1 }] })
    expect(new Set(detections.map((d) => d.id)).size).toBe(found + 2)
  })

  it('is refused a model that is not one of the analysis, or something that is not a zone', async () => {
    const { addElement } = useAnalyses()
    const run = await fresh()
    expect(await addElement('a1', run.id, { zone: square, templateId: 't3' })).toBe(false)
    expect(await addElement('a1', run.id, { zone: { page: 1, points: square.points.slice(0, 2) }, templateId: 't1' })).toBe(false)
    expect(current(run.id).detections!.every((d) => d.source === 'analysis')).toBe(true)
  })

  it('is for the person who ran it only, and for a use that has a result', async () => {
    const run = await fresh()
    useSession().setUser('admin', { isAdmin: true })
    expect(await useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't1' })).toBe(false)
    useSession().setUser('alice.martin')
    expect(await useAnalyses().addElement('a1', 'r3', { zone: square, templateId: 't1' })).toBe(false)
  })

  it('takes away one added by hand, never one the analysis found', async () => {
    const { addElement, removeElement, actionError } = useAnalyses()
    const run = await fresh()
    await addElement('a1', run.id, { zone: square, templateId: 't1' })
    const added = current(run.id).detections!.find((d) => d.source === 'manual')!
    expect(await removeElement('a1', run.id, added.id)).toBe(true)
    expect(current(run.id).detections!.some((d) => d.source === 'manual')).toBe(false)
    const found = current(run.id).detections![0]
    if (found) {
      expect(await removeElement('a1', run.id, found.id)).toBe(false)
      expect(actionError.value).toContain('refusez-le')
    }
    expect(await removeElement('a1', run.id, 'nope')).toBe(false)
  })
})

describe('deleting or keeping the document', () => {
  beforeEach(() => asUser('alice.martin'))
  const withCapture = async () => (await useAnalyses().startRun('a1', png(), { saveScreenshot: true }))!
  const current = (runId: string) => useAnalyses().findRun('a1', runId)!

  it('deletes the screenshots, and keeps what was found and decided', async () => {
    const run = await withCapture()
    await useAnalyses().reviewPage('a1', run.id, { status: 'validated' })
    expect(await useAnalyses().deleteScreenshot('a1', run.id)).toBe(true)
    expect(current(run.id).screenshot).toBeNull()
    expect(current(run.id).fileDecision).toBe('deleted')
    expect(current(run.id).page!.review.status).toBe('validated')
    expect(current(run.id).detections!.length).toBe(run.detections!.length)
  })

  it('says the screenshots are kept, which stops asking', async () => {
    const run = await withCapture()
    expect(await useAnalyses().keepScreenshot('a1', run.id)).toBe(true)
    expect(current(run.id).fileDecision).toBe('kept')
    expect(current(run.id).screenshot).not.toBeNull()
  })

  it('has nothing to delete or keep when none were kept, or once they are deleted', async () => {
    const { startRun, deleteScreenshot, keepScreenshot } = useAnalyses()
    const none = (await startRun('a1', png(), { saveScreenshot: false }))!
    expect(await deleteScreenshot('a1', none.id)).toBe(false)
    expect(await keepScreenshot('a1', none.id)).toBe(false)
    const run = await withCapture()
    await deleteScreenshot('a1', run.id)
    expect(await deleteScreenshot('a1', run.id)).toBe(false)
  })

  it('is for the person who ran it only', async () => {
    const run = await withCapture()
    useSession().setUser('admin', { isAdmin: true })
    expect(await useAnalyses().deleteScreenshot('a1', run.id)).toBe(false)
    expect(await useAnalyses().keepScreenshot('a1', run.id)).toBe(false)
    useSession().setUser('alice.martin')
    expect(current(run.id).screenshot).not.toBeNull()
  })

  it('says the backend cannot be reached', async () => {
    const run = await withCapture()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect(await useAnalyses().keepScreenshot('a1', run.id)).toBe(false)
    expect(useAnalyses().actionError.value).toBe('Le serveur est injoignable.')
  })
})
