import type { Reason } from '../api/types'

export type ReasonGroup = 'stage' | 'signal' | 'teller' | 'dampener' | 'info'

const SIGNALS = new Set(['FRI_RISK', 'LONG_CALL_UNKNOWN', 'TRUSTED_CONTACT_RECENTLY_CHANGED'])

export function reasonGroup(reason: Reason): ReasonGroup {
  if (reason.points < 0) return 'dampener'
  if (reason.points === 0) return 'info'
  if (reason.code.startsWith('TELLER_')) return 'teller'
  if (SIGNALS.has(reason.code)) return 'signal'
  return 'stage'
}

/** Highest points first; negative (risk-reducing) after positive; zero-point info last. */
export function sortReasons(reasons: Reason[]): Reason[] {
  const rank = (r: Reason) => (r.points > 0 ? 0 : r.points < 0 ? 1 : 2)
  return [...reasons].sort(
    (a, b) =>
      rank(a) - rank(b) || Math.abs(b.points) - Math.abs(a.points) || a.code.localeCompare(b.code),
  )
}

export function isSimulated(reason: Reason): boolean {
  return (reason.evidence as { source?: string } | undefined)?.source === 'SIMULATED'
}
