import { describe, expect, it } from 'vitest'
import { gridCapacity } from './useGridPaging'

describe('gridCapacity', () => {
  const base = { columns: 3, rowHeight: 200, gap: 16 }

  it('counts the whole rows that fit, times the columns', () => {
    expect(gridCapacity({ ...base, areaHeight: 440 })).toBe(6) // 2 rows: 200 + 16 + 200 = 416
    expect(gridCapacity({ ...base, areaHeight: 656 })).toBe(9) // 3 rows: 632
    expect(gridCapacity({ ...base, areaHeight: 1000 })).toBe(12) // 4 rows: 848
  })

  it('does not count a row that would be cut off', () => {
    expect(gridCapacity({ ...base, areaHeight: 415 })).toBe(3) // one pixel short of two rows
    expect(gridCapacity({ ...base, areaHeight: 416 })).toBe(6)
  })

  it('always shows one row, however little room there is', () => {
    expect(gridCapacity({ ...base, areaHeight: 50 })).toBe(3)
  })

  it('has nothing to say without something to measure', () => {
    expect(gridCapacity({ ...base, areaHeight: 0 })).toBe(0)
    expect(gridCapacity({ ...base, columns: 0, areaHeight: 500 })).toBe(0)
    expect(gridCapacity({ ...base, rowHeight: 0, areaHeight: 500 })).toBe(0)
  })

  it('follows the number of columns', () => {
    expect(gridCapacity({ ...base, columns: 1, areaHeight: 440 })).toBe(2)
    expect(gridCapacity({ ...base, columns: 4, areaHeight: 440 })).toBe(8)
  })
})
