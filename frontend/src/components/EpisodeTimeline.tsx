import type { EpisodeOut } from '../api/types'
import { useT } from '../i18n/lang'
import { demoDay, formatINR, formatISTTime } from '../lib/format'

const STAGE_KEY = {
  S1_LIQUIDATION: 'stage.S1',
  S2_POOLING: 'stage.S2',
  S3_NEW_PAYEE: 'stage.S3',
  S4_HIGH_VALUE: 'stage.S4',
} as const
const ICON = {
  S1_LIQUIDATION: '🏦',
  S2_POOLING: '⇢',
  S3_NEW_PAYEE: '＋',
  S4_HIGH_VALUE: '₹',
} as const

/** Day lanes in simulated time; also the text equivalent of the watch chart (DESIGN §12). */
export function EpisodeTimeline({ episode, id }: { episode: EpisodeOut; id?: string }) {
  const t = useT()
  type Item = { at: string; label: string; icon: string; detail?: string }
  const items: Item[] = [
    ...episode.stages.map((s) => ({
      at: s.occurred_at,
      label: t(STAGE_KEY[s.stage as keyof typeof STAGE_KEY] ?? 'stage.S1'),
      icon: ICON[s.stage as keyof typeof ICON] ?? '•',
      detail: s.amount_paise ? formatINR(s.amount_paise) : undefined,
    })),
    ...episode.watch_history
      .filter((p) => p.trigger_event_id.startsWith('SIG-'))
      .map((p) => ({ at: p.at, label: t('ops.watch_score', { score: p.score }), icon: '☎' })),
  ].sort((a, b) => a.at.localeCompare(b.at))
  const days = [...new Set(items.map((i) => demoDay(i.at)))]
  return (
    <div id={id} className="flex gap-3 overflow-x-auto pb-2">
      {days.map((day) => (
        <section key={day} className="min-w-44 flex-1 rounded border border-border p-2">
          <h3 className="mb-2 text-xs font-bold uppercase text-text-muted">
            {t('app.day', { n: day })}
          </h3>
          <ol className="space-y-1.5">
            {items
              .filter((i) => demoDay(i.at) === day)
              .map((i, idx) => (
                <li key={`${i.at}-${idx}`} className="flex items-baseline gap-2 text-sm">
                  <span aria-hidden="true">{i.icon}</span>
                  <span className="tabular-nums text-text-muted">{formatISTTime(i.at)}</span>
                  <span className="font-semibold">{i.label}</span>
                  {i.detail && <span className="text-text-muted">{i.detail}</span>}
                </li>
              ))}
          </ol>
        </section>
      ))}
    </div>
  )
}
