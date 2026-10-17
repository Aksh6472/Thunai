import { describe, expect, it } from 'vitest'

import { demoDay, formatINR, formatIST, groupRupees, parseRupees, timeLeft } from './format'

describe('format', () => {
  it('formats INR with Indian grouping (T-032 acceptance)', () => {
    expect(formatINR(460000000)).toBe('₹46,00,000')
    expect(formatINR(4000000)).toBe('₹40,000')
    expect(formatINR(0)).toBe('₹0')
    expect(groupRupees(1234567)).toBe('12,34,567')
  })

  it('parses rupee input', () => {
    expect(parseRupees('46,00,000')).toBe(4600000)
    expect(parseRupees('₹ 300000')).toBe(300000)
    expect(parseRupees('0')).toBeNull()
    expect(parseRupees('12.5')).toBeNull()
    expect(parseRupees('abc')).toBeNull()
  })

  it('formats times in IST', () => {
    expect(formatIST('2026-10-03T05:50:00Z')).toBe('03 Oct, 11:20')
  })

  it('labels simulated days', () => {
    expect(demoDay('2026-10-01T04:35:00Z')).toBe(1)
    expect(demoDay('2026-10-03T05:50:00Z')).toBe(3)
    expect(demoDay('2026-09-30T19:00:00Z')).toBe(1) // 00:30 IST on 1 Oct
  })

  it('shows time left', () => {
    const now = Date.parse('2026-10-03T05:50:00Z')
    expect(timeLeft('2026-10-03T09:02:00Z', now)).toBe('3h 12m')
    expect(timeLeft('2026-10-03T05:59:00Z', now)).toBe('9m')
    expect(timeLeft('2026-10-03T05:00:00Z', now)).toBeNull()
  })
})
