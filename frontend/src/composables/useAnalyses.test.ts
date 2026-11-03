import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetAnalyses, simulatePage, simulateTest, statsOf, useAnalyses } from './useAnalyses'
import { loadGroups } from './useGroups'
import { useSession } from './useSession'

describe('useAnalyses', () => {
  beforeAll(loadGroups)
  beforeEach(() => {
    resetAnalyses()
    useSession().login('alice.martin')
  })

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

  it('creates an analysis that is running, with nothing found yet, first in the list', () => {
    const { analyses, createAnalysis } = useAnalyses()
    const before = analyses.value.length
    const created = createAnalysis(input)
    expect(created).toMatchObject({ name: 'Contrats', description: 'Les contrats de l’année.', templateIds: ['t1', 't3'], status: 'running', matches: 0 })
    expect(created.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(analyses.value).toHaveLength(before + 1)
    expect(analyses.value[0].id).toBe(created.id)
  })

  it('keeps who it is shared with, as a copy', () => {
    const { createAnalysis } = useAnalyses()
    const created = createAnalysis(input)
    expect(created.isPublic).toBe(false)
    expect(created.shares).toEqual(input.shares)
    expect(created.shares).not.toBe(input.shares)
    expect(created.shares[0]).not.toBe(input.shares[0])
  })

  it('keeps no recipient for an analysis that is public: it is for everyone', () => {
    const { createAnalysis } = useAnalyses()
    const created = createAnalysis({ ...input, isPublic: true })
    expect(created.isPublic).toBe(true)
    expect(created.shares).toEqual([])
  })

  it('may have no description and no recipient', () => {
    const { createAnalysis } = useAnalyses()
    expect(createAnalysis({ ...input, description: '', shares: [] })).toMatchObject({ description: '', shares: [], isPublic: false })
  })

  it('counts them', () => {
    const { analyses, total, createAnalysis } = useAnalyses()
    const before = total.value
    createAnalysis(input)
    expect(total.value).toBe(before + 1)
    expect(total.value).toBe(analyses.value.length)
  })
})

describe('who can open an analysis', () => {
  beforeAll(loadGroups)
  beforeEach(() => resetAnalyses())

  const accessibleBy = (who: string | null) => {
    if (who === null) useSession().logout()
    else useSession().login(who)
    return useAnalyses().accessible.value.map((a) => a.id)
  }

  it('is its owner, whatever it is, and anyone when it is public', () => {
    // alice.martin made a1, a4 and a5; a5 is public.
    expect(accessibleBy('alice.martin')).toEqual(expect.arrayContaining(['a1', 'a4', 'a5']))
    expect(accessibleBy('chloe.petit')).toEqual(expect.arrayContaining(['a3', 'a7', 'a8', 'a5']))
    expect(accessibleBy('someone.new')).toEqual(['a5']) // only the public one
  })

  it('is the people it is shared with, by e-mail address', () => {
    // a7 is shared with dana@example.org; dana's address is made from her identifier.
    expect(accessibleBy('dana')).toContain('a7')
    expect(accessibleBy('bob.durand')).not.toContain('a7')
  })

  it('is the members of the groups it is shared with', () => {
    // a2 is shared with « Équipe courriers » (alice.martin, bob.durand), a6 with « Préfecture de Paris » (bob.durand, dana).
    expect(accessibleBy('alice.martin')).toContain('a2')
    expect(accessibleBy('dana')).toContain('a6')
    expect(accessibleBy('chloe.petit')).not.toContain('a2')
  })

  it('is everyone it is shared with, and no one it is not', () => {
    // a3 (private) is chloe.petit's alone.
    for (const who of ['alice.martin', 'bob.durand', 'dana']) expect(accessibleBy(who)).not.toContain('a3')
    expect(accessibleBy('chloe.petit')).toContain('a3')
  })

  it('is every analysis for an administrator', () => {
    expect(accessibleBy('admin')).toHaveLength(useAnalyses().total.value)
  })

  it('is none for no one signed in', () => {
    expect(accessibleBy(null)).toEqual([])
  })

  it('does not depend on the case of the address', () => {
    const { analyses, canAccess } = useAnalyses()
    useSession().login('Dana')
    const a7 = analyses.value.find((a) => a.id === 'a7')!
    a7.shares = [{ kind: 'email', value: 'DANA@Example.org' }]
    expect(canAccess(a7)).toBe(true)
  })

  it('knows the groups of the user', () => {
    useSession().login('bob.durand')
    expect(useAnalyses().myGroups.value).toEqual(['Équipe courriers', 'Préfecture de Paris'])
    useSession().logout()
    expect(useAnalyses().myGroups.value).toEqual([])
  })
})

describe('the views of an analysis', () => {
  beforeAll(loadGroups)
  beforeEach(() => resetAnalyses())

  it('counts one more each time someone who can open it looks at it', () => {
    useSession().login('alice.martin')
    const { find, registerView } = useAnalyses()
    expect(find('a1')!.views).toBe(42)
    expect(registerView('a1')).toBe(true)
    expect(registerView('a1')).toBe(true)
    expect(find('a1')!.views).toBe(44)
  })

  it('counts nothing for someone who cannot open it, or for an analysis that does not exist', () => {
    useSession().login('dana')
    const { find, registerView } = useAnalyses()
    expect(registerView('a1')).toBe(false)
    expect(find('a1')!.views).toBe(42)
    expect(registerView('nope')).toBe(false)
  })
})

describe('statsOf', () => {
  beforeEach(() => resetAnalyses())

  it('sums the views and the uses, and counts the uses by state', () => {
    const { analyses, find } = useAnalyses()
    expect(statsOf([find('a1')!])).toEqual({ views: 42, uses: 4, done: 3, running: 0, failed: 1 })
    expect(statsOf([find('a5')!])).toEqual({ views: 120, uses: 5, done: 3, running: 1, failed: 1 })
    expect(statsOf(analyses.value)).toEqual({ views: 251, uses: 20, done: 12, running: 3, failed: 5 })
  })

  it('is all zeros for nothing', () => {
    expect(statsOf([])).toEqual({ views: 0, uses: 0, done: 0, running: 0, failed: 0 })
  })

  it('has states that add up to the uses', () => {
    const s = statsOf(useAnalyses().analyses.value)
    expect(s.done + s.running + s.failed).toBe(s.uses)
  })
})

describe('simulateTest', () => {
  const analysis = { templateIds: ['t1', 't2', 't3', 't4'] }
  const file = { name: 'courrier.png', size: 1234 }
  const names = Array.from({ length: 30 }, (_, i) => `document-${i}.png`)

  it('says the same thing of the same file, and something else of another', () => {
    expect(simulateTest(analysis, file)).toEqual(simulateTest(analysis, file))
    const answers = names.map((name) => JSON.stringify(simulateTest(analysis, { name, size: 10 })))
    expect(new Set(answers).size).toBeGreaterThan(20)
  })

  it('gives each element a place on the page, as fractions, that stays inside it', () => {
    for (const name of names) {
      for (const d of simulateTest(analysis, { name, size: 5 })) {
        expect(d.zone.page).toBe(1)
        expect(d.zone.points.length).toBeGreaterThanOrEqual(4)
        for (const p of d.zone.points) {
          expect(p.x).toBeGreaterThanOrEqual(0)
          expect(p.x).toBeLessThanOrEqual(1)
          expect(p.y).toBeGreaterThanOrEqual(0)
          expect(p.y).toBeLessThanOrEqual(1)
        }
      }
    }
  })

  it('draws rectangles, and sometimes polygons with a corner cut', () => {
    const sizes = names.flatMap((name) => simulateTest(analysis, { name, size: 1 })).map((d) => d.zone.points.length)
    expect(sizes).toContain(4)
    expect(sizes).toContain(5)
    expect(sizes.every((n) => n === 4 || n === 5)).toBe(true)
  })

  it('numbers the elements from 1, in reading order: top to bottom, then left to right', () => {
    for (const name of names) {
      const found = simulateTest(analysis, { name, size: 7 })
      expect(found.map((d) => d.id)).toEqual(found.map((_, i) => `d${i + 1}`))
      const tops = found.map((d) => Math.min(...d.zone.points.map((p) => p.y)))
      expect([...tops].sort((a, b) => a - b)).toEqual(tops)
    }
  })

  it('gives each element every class it could be, the likeliest first, adding up to 100 %', () => {
    for (const name of names) {
      for (const d of simulateTest(analysis, { name, size: 3 })) {
        const sum = d.classifications.reduce((n, c) => n + Math.round(c.confidence * 100), 0)
        expect(sum).toBe(100)
        const confidences = d.classifications.map((c) => c.confidence)
        expect([...confidences].sort((a, b) => b - a)).toEqual(confidences)
        expect(confidences[0]).toBeGreaterThanOrEqual(0.62)
        expect(confidences[0]).toBeLessThanOrEqual(0.98)
      }
    }
  })

  it('offers the models of the analysis as classes, and « other », each once', () => {
    for (const name of names) {
      for (const d of simulateTest(analysis, { name, size: 3 })) {
        const classes = d.classifications.map((c) => c.templateId)
        expect(new Set(classes).size).toBe(classes.length)
        expect([...classes].sort((a, b) => String(a).localeCompare(String(b)))).toEqual([null, 't1', 't2', 't3', 't4'])
      }
    }
  })

  it('finds each model in most documents and misses it in some', () => {
    const counts = names.map((name) => simulateTest({ templateIds: ['t1'] }, { name, size: 0 }).length)
    expect(counts.some((n) => n === 0)).toBe(true)
    expect(counts.some((n) => n > 0)).toBe(true)
    expect(Math.max(...counts)).toBeLessThanOrEqual(3)
  })

  it('has « other » as the only other class for an analysis of one model', () => {
    const d = names.flatMap((name) => simulateTest({ templateIds: ['t1'] }, { name, size: 0 })).find(Boolean)!
    expect(d.classifications.map((c) => c.templateId).sort()).toEqual([null, 't1'])
  })

  it('has nothing to say for an analysis with no model', () => {
    expect(simulateTest({ templateIds: [] }, file)).toEqual([])
  })
})

describe('an analysis just made', () => {
  beforeEach(() => resetAnalyses())

  it('belongs to whoever made it, with no view and its first use, running', () => {
    useSession().login('dana')
    const created = useAnalyses().createAnalysis({ name: 'À moi', description: '', templateIds: ['t1'], isPublic: false, shares: [] })
    expect(created).toMatchObject({ ownerId: 'dana', views: 0, status: 'running' })
    expect(created.runs).toHaveLength(1)
    expect(created.runs[0]).toMatchObject({ userId: 'dana', status: 'running', matches: 0 })
    expect(statsOf([created])).toEqual({ views: 0, uses: 1, done: 0, running: 1, failed: 0 })
  })

  it('can be opened by its owner and by no one else, when it is not shared', async () => {
    await loadGroups()
    useSession().login('dana')
    const { createAnalysis, canAccess } = useAnalyses()
    const created = createAnalysis({ name: 'À moi', description: '', templateIds: ['t1'], isPublic: false, shares: [] })
    expect(canAccess(created)).toBe(true)
    useSession().login('bob.durand')
    expect(canAccess(created)).toBe(false)
  })

  it('goes back to the demo data on reset', () => {
    useSession().login('dana')
    const { analyses, createAnalysis } = useAnalyses()
    const before = analyses.value.length
    createAnalysis({ name: 'x', description: '', templateIds: ['t1'], isPublic: false, shares: [] })
    expect(analyses.value).toHaveLength(before + 1)
    resetAnalyses()
    expect(analyses.value).toHaveLength(before)
  })
})

describe('trying an analysis on a document', () => {
  const png = (name = 'scan.png') => new File(['x'], name, { type: 'image/png' })
  const pdf = (name = 'scan.pdf') => new File(['x'], name, { type: 'application/pdf' })
  const analysisOf = (id: string) => useAnalyses().find(id)!

  beforeAll(loadGroups)
  beforeEach(() => {
    resetAnalyses()
    URL.createObjectURL = vi.fn(() => 'blob:capture')
    URL.revokeObjectURL = vi.fn()
    useSession().login('alice.martin')
  })
  afterEach(() => vi.restoreAllMocks())

  describe('startRun', () => {
    it('makes a use of it, own and done, with what was found still to be looked at', () => {
      const before = analysisOf('a1').runs.length
      const run = useAnalyses().startRun('a1', png(), { saveScreenshot: true })!
      expect(analysisOf('a1').runs).toHaveLength(before + 1)
      expect(analysisOf('a1').runs[0].id).toBe(run.id)
      expect(run).toMatchObject({ userId: 'alice.martin', status: 'done', fileName: 'scan.png' })
      expect(run.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      expect(run.matches).toBe(run.detections!.length)
      for (const d of run.detections!) expect(d.review).toEqual({ status: 'pending' })
    })

    it('finds what simulateTest finds, for that document', () => {
      const file = png('exemple.png')
      const run = useAnalyses().startRun('a1', file, { saveScreenshot: false })!
      const expected = simulateTest(analysisOf('a1'), file)
      expect(run.detections!.map((d) => [d.id, d.zone, d.classifications])).toEqual(expected.map((d) => [d.id, d.zone, d.classifications]))
    })

    it('keeps a capture of an image when asked to', () => {
      const run = useAnalyses().startRun('a1', png(), { saveScreenshot: true })!
      expect(run.screenshot).toEqual({ name: 'scan.png', type: 'image/png', url: 'blob:capture' })
    })

    it('keeps no capture when not asked to', () => {
      const run = useAnalyses().startRun('a1', png(), { saveScreenshot: false })!
      expect(run.screenshot).toBeNull()
      expect(URL.createObjectURL).not.toHaveBeenCalled()
    })

    it('keeps no capture of a PDF, which has nothing to show', () => {
      const run = useAnalyses().startRun('a1', pdf(), { saveScreenshot: true })!
      expect(run.screenshot).toBeNull()
      expect(run.detections).toBeDefined() // but it is still tried
    })

    it('counts as a use of the analysis', () => {
      const before = statsOf([analysisOf('a1')])
      useAnalyses().startRun('a1', png(), { saveScreenshot: false })
      const after = statsOf([analysisOf('a1')])
      expect(after.uses).toBe(before.uses + 1)
      expect(after.done).toBe(before.done + 1)
    })

    it('is for whoever can open the analysis: by a group, public, or all of them for an administrator', () => {
      useSession().login('dana')
      expect(useAnalyses().startRun('a5', png(), { saveScreenshot: false })).not.toBeNull() // public
      expect(useAnalyses().startRun('a6', png(), { saveScreenshot: false })).not.toBeNull() // her group
      useSession().login('admin')
      expect(useAnalyses().startRun('a3', png(), { saveScreenshot: false })).not.toBeNull()
    })

    it('is refused to anyone who cannot open the analysis, or no one, or for an analysis that does not exist', () => {
      const before = analysisOf('a3').runs.length
      useSession().login('dana')
      expect(useAnalyses().startRun('a3', png(), { saveScreenshot: true })).toBeNull()
      expect(analysisOf('a3').runs).toHaveLength(before)
      expect(useAnalyses().startRun('nope', png(), { saveScreenshot: true })).toBeNull()
      useSession().logout()
      expect(useAnalyses().startRun('a5', png(), { saveScreenshot: true })).toBeNull()
    })

    it('is refused for a document that is not an image or a PDF', () => {
      const before = analysisOf('a1').runs.length
      expect(useAnalyses().startRun('a1', new File(['x'], 'notes.txt', { type: 'text/plain' }), { saveScreenshot: true })).toBeNull()
      expect(analysisOf('a1').runs).toHaveLength(before)
    })
  })

  describe('who sees the result of a use', () => {
    const own = () => analysisOf('a1').runs.find((r) => r.id === 'r1')! // alice.martin's, with a result
    const without = () => analysisOf('a1').runs.find((r) => r.id === 'r3')! // alice.martin's, with none

    it('is the person who ran it', () => {
      const { canSeeResult, ownsRun } = useAnalyses()
      expect(ownsRun(own())).toBe(true)
      expect(canSeeResult(own())).toBe(true)
    })

    it('is not someone else, who can open the analysis', () => {
      useSession().login('dana')
      expect(useAnalyses().canSeeResult(analysisOf('a5').runs.find((r) => r.id === 'r12')!)).toBe(false) // alice's, public analysis
    })

    it('is not an administrator either, though they can open the analysis', () => {
      useSession().login('admin')
      const { canAccess, canSeeResult, ownsRun } = useAnalyses()
      expect(canAccess(analysisOf('a1'))).toBe(true)
      expect(ownsRun(own())).toBe(false)
      expect(canSeeResult(own())).toBe(false)
    })

    it('is an administrator for the uses they ran themselves', () => {
      useSession().login('admin')
      const run = useAnalyses().startRun('a1', png(), { saveScreenshot: false })!
      expect(useAnalyses().canSeeResult(run)).toBe(true)
    })

    it('is no one, signed out', () => {
      useSession().logout()
      expect(useAnalyses().canSeeResult(own())).toBe(false)
    })

    it('has nothing to see for a use that stored no result', () => {
      expect(useAnalyses().canSeeResult(without())).toBe(false)
    })

    it('has the demo uses that name a document carry a result, and the others none', () => {
      expect(own().detections).toBeDefined()
      expect(analysisOf('a1').runs.find((r) => r.id === 'r2')!.detections).toBeDefined()
      expect(without().detections).toBeUndefined()
    })

    it('has the first demo use keep a capture, with its first element already confirmed', () => {
      expect(own().screenshot).toMatchObject({ name: 'courrier-octobre-1.svg', type: 'image/svg+xml' })
      expect(own().detections![0].review).toEqual({ status: 'validated' })
      expect(analysisOf('a1').runs.find((r) => r.id === 'r2')!.screenshot).toBeNull()
    })
  })

  describe('looking at the predictions', () => {
    const fresh = () => useAnalyses().startRun('a1', png('revue.png'), { saveScreenshot: false })!

    /** A document in which the demo analysis finds at least two elements. */
    const rich = () => {
      const name = Array.from({ length: 300 }, (_, i) => `revue-${i}.png`).find((n) => simulateTest(analysisOf('a1'), { name: n, size: 1 }).length >= 2)!
      return useAnalyses().startRun('a1', png(name), { saveScreenshot: false })!
    }

    it('confirms a prediction, or rejects it', () => {
      const { reviewDetection } = useAnalyses()
      const run = rich()
      expect(reviewDetection('a1', run.id, 'd1', { status: 'validated' })).toBe(true)
      expect(run.detections![0].review).toEqual({ status: 'validated' })
      expect(reviewDetection('a1', run.id, 'd2', { status: 'invalidated' })).toBe(true)
      expect(run.detections![1].review).toEqual({ status: 'invalidated' })
    })

    it('annotates with a model of the analysis', () => {
      const run = rich()
      expect(useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'annotated', templateId: 't6' })).toBe(true)
      expect(run.detections![0].review).toEqual({ status: 'annotated', templateId: 't6' })
    })

    it('refuses to annotate with a model that is not one of the analysis, or with none', () => {
      const { reviewDetection } = useAnalyses()
      const run = rich()
      expect(reviewDetection('a1', run.id, 'd1', { status: 'annotated', templateId: 't3' })).toBe(false) // in the catalogue, not in a1
      expect(reviewDetection('a1', run.id, 'd1', { status: 'annotated', templateId: 'nope' })).toBe(false)
      expect(reviewDetection('a1', run.id, 'd1', { status: 'annotated' })).toBe(false)
      expect(run.detections![0].review).toEqual({ status: 'pending' })
    })

    it('keeps no model with a decision that is not an annotation', () => {
      const run = rich()
      useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'annotated', templateId: 't1' })
      useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'validated', templateId: 't1' })
      expect(run.detections![0].review).toEqual({ status: 'validated' })
    })

    it('takes a decision back, or changes it', () => {
      const { reviewDetection } = useAnalyses()
      const run = rich()
      reviewDetection('a1', run.id, 'd1', { status: 'validated' })
      reviewDetection('a1', run.id, 'd1', { status: 'invalidated' })
      expect(run.detections![0].review.status).toBe('invalidated')
      reviewDetection('a1', run.id, 'd1', { status: 'pending' })
      expect(run.detections![0].review).toEqual({ status: 'pending' })
    })

    it('is for one\'s own results only: not for someone else, an administrator included', () => {
      const run = rich()
      useSession().login('admin')
      expect(useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'validated' })).toBe(false)
      useSession().login('dana')
      expect(useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'validated' })).toBe(false)
      expect(run.detections![0].review).toEqual({ status: 'pending' })
    })

    it('refuses an element, a use or an analysis that does not exist', () => {
      const { reviewDetection } = useAnalyses()
      const run = rich()
      expect(reviewDetection('a1', run.id, 'nope', { status: 'validated' })).toBe(false)
      expect(reviewDetection('a1', 'nope', 'd1', { status: 'validated' })).toBe(false)
      expect(reviewDetection('nope', run.id, 'd1', { status: 'validated' })).toBe(false)
    })

    it('counts how many predictions have been looked at', () => {
      const { reviewDetection, reviewProgress } = useAnalyses()
      const run = rich()
      const total = run.detections!.length + 1 // its elements, and its page
      expect(reviewProgress(run)).toEqual({ total, reviewed: 0 })
      reviewDetection('a1', run.id, 'd1', { status: 'validated' })
      reviewDetection('a1', run.id, 'd2', { status: 'annotated', templateId: 't1' })
      expect(reviewProgress(run)).toEqual({ total, reviewed: 2 })
      reviewDetection('a1', run.id, 'd2', { status: 'pending' })
      expect(reviewProgress(run).reviewed).toBe(1)
    })

    it('has no prediction to look at in a use that stored no result', () => {
      expect(useAnalyses().reviewProgress(analysisOf('a1').runs.find((r) => r.id === 'r3')!)).toEqual({ total: 0, reviewed: 0 })
      expect(fresh().detections).toBeDefined()
    })
  })

  describe('deleting or keeping the document', () => {
    const withCapture = () => useAnalyses().startRun('a1', png(), { saveScreenshot: true })!

    it('deletes the capture, and keeps what was found and decided', () => {
      const run = withCapture()
      useAnalyses().reviewDetection('a1', run.id, 'd1', { status: 'validated' })
      expect(useAnalyses().deleteScreenshot('a1', run.id)).toBe(true)
      expect(run.screenshot).toBeNull()
      expect(run.fileDecision).toBe('deleted')
      expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:capture')
      expect(run.detections!.length).toBeGreaterThan(0)
      if (run.detections![0]) expect(run.detections![0].review.status).toBe('validated')
    })

    it('does not try to release a capture that is not a blob', () => {
      const run = analysisOf('a1').runs.find((r) => r.id === 'r1')! // the demo capture is a data: URL
      expect(useAnalyses().deleteScreenshot('a1', 'r1')).toBe(true)
      expect(URL.revokeObjectURL).not.toHaveBeenCalled()
      expect(run.screenshot).toBeNull()
    })

    it('says the capture is kept, which stops asking', () => {
      const run = withCapture()
      expect(useAnalyses().keepScreenshot('a1', run.id)).toBe(true)
      expect(run.fileDecision).toBe('kept')
      expect(run.screenshot).not.toBeNull()
    })

    it('has nothing to delete or keep when no capture was kept', () => {
      const run = useAnalyses().startRun('a1', png(), { saveScreenshot: false })!
      expect(useAnalyses().deleteScreenshot('a1', run.id)).toBe(false)
      expect(useAnalyses().keepScreenshot('a1', run.id)).toBe(false)
      expect(run.fileDecision).toBeUndefined()
    })

    it('is for the person who ran it only', () => {
      const run = withCapture()
      useSession().login('admin')
      expect(useAnalyses().deleteScreenshot('a1', run.id)).toBe(false)
      expect(useAnalyses().keepScreenshot('a1', run.id)).toBe(false)
      expect(run.screenshot).not.toBeNull()
    })

    it('cannot delete twice', () => {
      const run = withCapture()
      useAnalyses().deleteScreenshot('a1', run.id)
      expect(useAnalyses().deleteScreenshot('a1', run.id)).toBe(false)
    })
  })
})

describe('the classification of the page', () => {
  const analysis = { templateIds: ['t1', 't2', 't3'] }
  const names = Array.from({ length: 30 }, (_, i) => `page-${i}.png`)

  describe('simulatePage', () => {
    it('says the same of the same document, and something else of another', () => {
      const file = { name: 'a.png', size: 5 }
      expect(simulatePage(analysis, file)).toEqual(simulatePage(analysis, file))
      const answers = names.map((name) => JSON.stringify(simulatePage(analysis, { name, size: 1 })))
      expect(new Set(answers).size).toBeGreaterThan(1)
    })

    it('gives every class the page could be, the likeliest first, adding up to 100 %', () => {
      for (const name of names) {
        const classes = simulatePage(analysis, { name, size: 1 })
        expect(classes.reduce((n, c) => n + Math.round(c.confidence * 100), 0)).toBe(100)
        const confidences = classes.map((c) => c.confidence)
        expect([...confidences].sort((a, b) => b - a)).toEqual(confidences)
        expect(confidences[0]).toBeGreaterThanOrEqual(0.62)
        expect([...classes.map((c) => c.templateId)].sort((a, b) => String(a).localeCompare(String(b)))).toEqual([null, 't1', 't2', 't3'])
      }
    })

    it('says the page is one of the models of the analysis, not « other », and uses all of them over many documents', () => {
      const best = names.map((name) => simulatePage(analysis, { name, size: 1 })[0].templateId)
      expect(best.every((t) => t !== null && analysis.templateIds.includes(t))).toBe(true)
      expect(new Set(best).size).toBe(3)
    })

    it('does not follow what is found in the page', () => {
      const same = names.filter((name) => simulatePage(analysis, { name, size: 1 })[0].templateId === simulateTest(analysis, { name, size: 1 })[0]?.classifications[0].templateId)
      expect(same.length).toBeLessThan(names.length)
    })

    it('has « other » alone when the analysis has no model', () => {
      expect(simulatePage({ templateIds: [] }, { name: 'a.png', size: 1 })).toEqual([{ templateId: null, confidence: 1 }])
    })
  })
})

describe('the page and the elements added by hand', () => {
  const png = (name = 'scan.png') => new File(['x'], name, { type: 'image/png' })
  const square = { page: 1, points: [{ x: 0.1, y: 0.1 }, { x: 0.4, y: 0.1 }, { x: 0.4, y: 0.4 }, { x: 0.1, y: 0.4 }] }
  const analysisOf = (id: string) => useAnalyses().find(id)!

  beforeAll(loadGroups)
  beforeEach(() => {
    resetAnalyses()
    URL.createObjectURL = vi.fn(() => 'blob:capture')
    URL.revokeObjectURL = vi.fn()
    useSession().login('alice.martin')
  })
  afterEach(() => vi.restoreAllMocks())

  const fresh = () => useAnalyses().startRun('a1', png(), { saveScreenshot: true })!

  describe('the page of a use', () => {
    it('comes with the use, still to be looked at', () => {
      const run = fresh()
      expect(run.page!.review).toEqual({ status: 'pending' })
      expect(run.page!.classifications).toEqual(simulatePage(analysisOf('a1'), png()))
    })

    it('is there for the demo uses that name a document', () => {
      expect(analysisOf('a1').runs.find((r) => r.id === 'r1')!.page).toBeDefined()
      expect(analysisOf('a1').runs.find((r) => r.id === 'r3')!.page).toBeUndefined()
    })

    it('is confirmed, rejected, or annotated with a model of the analysis', () => {
      const { reviewPage } = useAnalyses()
      const run = fresh()
      expect(reviewPage('a1', run.id, { status: 'validated' })).toBe(true)
      expect(run.page!.review).toEqual({ status: 'validated' })
      expect(reviewPage('a1', run.id, { status: 'invalidated' })).toBe(true)
      expect(run.page!.review).toEqual({ status: 'invalidated' })
      expect(reviewPage('a1', run.id, { status: 'annotated', templateId: 't6' })).toBe(true)
      expect(run.page!.review).toEqual({ status: 'annotated', templateId: 't6' })
    })

    it('takes a decision back', () => {
      const run = fresh()
      useAnalyses().reviewPage('a1', run.id, { status: 'validated' })
      useAnalyses().reviewPage('a1', run.id, { status: 'pending' })
      expect(run.page!.review).toEqual({ status: 'pending' })
    })

    it('refuses a model that is not one of the analysis', () => {
      const run = fresh()
      expect(useAnalyses().reviewPage('a1', run.id, { status: 'annotated', templateId: 't3' })).toBe(false)
      expect(useAnalyses().reviewPage('a1', run.id, { status: 'annotated' })).toBe(false)
      expect(run.page!.review).toEqual({ status: 'pending' })
    })

    it('is for the person who ran the use only, an administrator included', () => {
      const run = fresh()
      useSession().login('admin')
      expect(useAnalyses().reviewPage('a1', run.id, { status: 'validated' })).toBe(false)
      useSession().login('dana')
      expect(useAnalyses().reviewPage('a1', run.id, { status: 'validated' })).toBe(false)
      expect(run.page!.review).toEqual({ status: 'pending' })
    })

    it('has nothing to look at in a use with no page, or for a use that does not exist', () => {
      expect(useAnalyses().reviewPage('a1', 'r3', { status: 'validated' })).toBe(false)
      expect(useAnalyses().reviewPage('a1', 'nope', { status: 'validated' })).toBe(false)
      expect(useAnalyses().reviewPage('nope', 'r1', { status: 'validated' })).toBe(false)
    })

    it('counts in what has been looked at, with the elements', () => {
      const run = fresh()
      const total = run.detections!.length + 1
      useAnalyses().reviewPage('a1', run.id, { status: 'validated' })
      expect(useAnalyses().reviewProgress(run)).toEqual({ total, reviewed: 1 })
    })
  })

  describe('addElement', () => {
    it('adds by hand a zone annotated with a model of the analysis', () => {
      const run = fresh()
      const before = run.detections!.length
      const element = useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't6' })!
      expect(run.detections).toHaveLength(before + 1)
      expect(run.detections!.at(-1)!.id).toBe(element.id)
      expect(element).toMatchObject({
        id: 'm1',
        source: 'manual',
        zone: square,
        review: { status: 'annotated', templateId: 't6' },
        classifications: [{ templateId: 't6', confidence: 1 }],
      })
    })

    it('numbers the elements added by hand, one after the other', () => {
      const run = fresh()
      const { addElement, removeElement } = useAnalyses()
      expect(addElement('a1', run.id, { zone: square, templateId: 't1' })!.id).toBe('m1')
      expect(addElement('a1', run.id, { zone: square, templateId: 't1' })!.id).toBe('m2')
      removeElement('a1', run.id, 'm1')
      expect(addElement('a1', run.id, { zone: square, templateId: 't1' })!.id).toBe('m3') // never an identifier already used
    })

    it('counts as looked at: it is a decision already', () => {
      const run = fresh()
      const before = useAnalyses().reviewProgress(run)
      useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't1' })
      expect(useAnalyses().reviewProgress(run)).toEqual({ total: before.total + 1, reviewed: before.reviewed + 1 })
    })

    it('keeps its own copy of the zone', () => {
      const run = fresh()
      const zone = { page: 1, points: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }] }
      const element = useAnalyses().addElement('a1', run.id, { zone, templateId: 't1' })!
      zone.points[0].x = 0.5
      expect(element.zone.points[0].x).toBe(0)
    })

    it('refuses a model that is not one of the analysis', () => {
      const run = fresh()
      const before = run.detections!.length
      expect(useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't3' })).toBeNull()
      expect(useAnalyses().addElement('a1', run.id, { zone: square, templateId: 'nope' })).toBeNull()
      expect(run.detections).toHaveLength(before)
    })

    it('refuses something that is not a zone', () => {
      const run = fresh()
      expect(useAnalyses().addElement('a1', run.id, { zone: { page: 1, points: [{ x: 0, y: 0 }, { x: 1, y: 1 }] }, templateId: 't1' })).toBeNull()
      expect(useAnalyses().addElement('a1', run.id, { zone: { page: 1, points: [] }, templateId: 't1' })).toBeNull()
    })

    it('is for the person who ran the use only, an administrator included', () => {
      const run = fresh()
      const before = run.detections!.length
      useSession().login('admin')
      expect(useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't1' })).toBeNull()
      expect(run.detections).toHaveLength(before)
    })

    it('has nowhere to add to in a use that stored no result', () => {
      expect(useAnalyses().addElement('a1', 'r3', { zone: square, templateId: 't1' })).toBeNull()
      expect(useAnalyses().addElement('a1', 'nope', { zone: square, templateId: 't1' })).toBeNull()
      expect(useAnalyses().addElement('nope', 'r1', { zone: square, templateId: 't1' })).toBeNull()
    })
  })

  describe('removeElement', () => {
    it('takes away an element that was added by hand', () => {
      const run = fresh()
      const before = run.detections!.length
      const added = useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't1' })!
      expect(useAnalyses().removeElement('a1', run.id, added.id)).toBe(true)
      expect(run.detections).toHaveLength(before)
    })

    it('cannot take away what the analysis found: it is rejected instead', () => {
      const name = Array.from({ length: 300 }, (_, i) => `x-${i}.png`).find((n) => simulateTest(analysisOf('a1'), { name: n, size: 1 }).length > 0)!
      const run = useAnalyses().startRun('a1', png(name), { saveScreenshot: false })!
      expect(useAnalyses().removeElement('a1', run.id, 'd1')).toBe(false)
      expect(run.detections![0].id).toBe('d1')
    })

    it('is for the person who ran the use only, an administrator included', () => {
      const run = fresh()
      const added = useAnalyses().addElement('a1', run.id, { zone: square, templateId: 't1' })!
      useSession().login('admin')
      expect(useAnalyses().removeElement('a1', run.id, added.id)).toBe(false)
      expect(run.detections!.some((d) => d.id === added.id)).toBe(true)
    })

    it('has nothing to take away for an element, a use or an analysis that does not exist', () => {
      const run = fresh()
      expect(useAnalyses().removeElement('a1', run.id, 'm9')).toBe(false)
      expect(useAnalyses().removeElement('a1', 'nope', 'm1')).toBe(false)
      expect(useAnalyses().removeElement('nope', run.id, 'm1')).toBe(false)
    })
  })
})
