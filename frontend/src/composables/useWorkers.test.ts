import { describe, expect, it } from 'vitest'
import { workerTask } from '../test/fakeBackend'
import { ago, compareVersions, groupServices } from './useWorkers'

describe('groupServices', () => {
  it('makes a worker of the instances that have tasks, with its status', () => {
    const services = groupServices([
      workerTask('ocr.read_document', '1.25.0', [['ocr-1', true]]),
      workerTask('template_matching.ping', '1.25.0', [['tm-1', true], ['tm-2', false]]),
      workerTask('gliner.find_entities', '1.25.0', [['gl-1', false]]),
    ])

    expect(services.map((s) => [s.name, s.status, s.instances.length])).toEqual([
      ['gliner', 'offline', 1],
      ['ocr', 'online', 1],
      ['template_matching', 'partial', 2],
    ])
  })

  it('gives each instance the versions and the tasks it has, and lists the tasks once for the worker', () => {
    const [service] = groupServices([
      workerTask('ocr.read_document', '1.25.0', [['ocr-1', true], ['ocr-2', true]]),
      workerTask('ocr.ping', '1.25.0', [['ocr-1', true]]),
    ])

    expect(service?.instances.map((i) => [i.id, i.versions, i.tasks.length])).toEqual([
      ['ocr-1', ['1.25.0'], 2],
      ['ocr-2', ['1.25.0'], 1],
    ])
    expect(service?.tasks.map((t) => t.name)).toEqual(['ocr.ping', 'ocr.read_document'])
  })

  it('orders versions as numbers, the newest last, when a worker runs two', () => {
    const [service] = groupServices([
      workerTask('template_matching.ping', '1.10.0', [['tm-new', true]]),
      workerTask('template_matching.ping', '1.9.0', [['tm-old', true]]),
    ])

    expect(service?.versions).toEqual(['1.9.0', '1.10.0'])
    expect(service?.tasks.map((t) => t.version)).toEqual(['1.9.0', '1.10.0'])
  })

  it('has nothing for no task', () => {
    expect(groupServices([])).toEqual([])
  })
})

describe('compareVersions', () => {
  it('compares numbers as numbers', () => {
    expect(['1.10.0', '1.9.0', '2.0.0', '1.9.1'].sort(compareVersions)).toEqual(['1.9.0', '1.9.1', '1.10.0', '2.0.0'])
    expect(compareVersions('1.0.0', '1.0.0')).toBe(0)
  })
})

describe('ago', () => {
  const now = Date.parse('2026-11-10T12:00:00Z')
  const before = (seconds: number) => new Date(now - seconds * 1000).toISOString()

  it('says how long ago, in the unit that fits', () => {
    expect(ago(before(2), now)).toBe('à l’instant')
    expect(ago(before(12), now)).toBe('il y a 12 s')
    expect(ago(before(150), now)).toBe('il y a 2 min')
    expect(ago(before(2 * 3600 + 5), now)).toBe('il y a 2 h')
    expect(ago(before(5 * 86_400), now)).toBe('il y a 5 j')
    expect(ago(before(-30), now)).toBe('à l’instant') // a clock a little behind the backend's
  })
})
