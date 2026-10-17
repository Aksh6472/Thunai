import type { Reason } from '../api/types'
import { useT } from '../i18n/lang'
import { reasonGroup, type ReasonGroup } from './reasons'

const COLORS: Record<Exclude<ReasonGroup, 'info'>, string> = {
  stage: 'bg-tier-high',
  signal: 'bg-simulated',
  teller: 'bg-primary',
  dampener: 'bg-success',
}
const ORDER: Exclude<ReasonGroup, 'info'>[] = ['stage', 'signal', 'teller', 'dampener']

export function ScoreBreakdownBar({ reasons }: { reasons: Reason[] }) {
  const t = useT()
  const totals = Object.fromEntries(ORDER.map((g) => [g, 0])) as Record<
    (typeof ORDER)[number],
    number
  >
  for (const r of reasons) {
    const g = reasonGroup(r)
    if (g !== 'info') totals[g] += Math.abs(r.points)
  }
  const scale = Math.max(
    100,
    ORDER.reduce((s, g) => s + totals[g], 0),
  )
  return (
    <figure>
      <div className="flex h-4 w-full overflow-hidden rounded bg-bg" aria-hidden="true">
        {ORDER.map((g) =>
          totals[g] ? (
            <div key={g} className={COLORS[g]} style={{ width: `${(totals[g] / scale) * 100}%` }} />
          ) : null,
        )}
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {ORDER.filter((g) => totals[g]).map((g) => (
          <span key={g} className="inline-flex items-center gap-1">
            <span className={`inline-block size-3 rounded-sm ${COLORS[g]}`} aria-hidden="true" />
            {t(`group.${g}`)}: {g === 'dampener' ? '−' : '+'}
            {totals[g]}
          </span>
        ))}
      </figcaption>
    </figure>
  )
}
