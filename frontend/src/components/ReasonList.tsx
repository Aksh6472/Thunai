import type { Lang, Reason } from '../api/types'
import { useT } from '../i18n/lang'
import { isSimulated, sortReasons } from './reasons'
import { SimulatedChip } from './SimulatedChip'

export function ReasonList({
  reasons,
  lang = 'en',
  max,
}: {
  reasons: Reason[]
  lang?: Lang
  max?: number
}) {
  const t = useT()
  const sorted = sortReasons(reasons).slice(0, max ?? reasons.length)
  return (
    <ul className="divide-y divide-border">
      {sorted.map((r) => {
        const negative = r.points < 0
        return (
          <li key={r.code} className="flex items-start gap-3 py-2" data-testid="reason">
            <span
              className={`w-12 shrink-0 text-right font-mono text-sm font-bold tabular-nums ${negative ? 'text-success' : r.points === 0 ? 'text-text-muted' : 'text-text'}`}
            >
              {r.points > 0 ? `+${r.points}` : r.points}
            </span>
            <span className="flex-1">
              <span lang={lang}>{lang === 'ta' ? r.text_ta : r.text_en}</span>
              {negative && (
                <span className="ml-2 text-xs font-semibold text-success">
                  ({t('reason.reduces')})
                </span>
              )}
            </span>
            <span className="flex shrink-0 items-center gap-1">
              {r.stage && (
                <span className="rounded bg-bg px-1.5 text-xs font-semibold text-text-muted">
                  {r.stage}
                </span>
              )}
              {isSimulated(r) && <SimulatedChip />}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
