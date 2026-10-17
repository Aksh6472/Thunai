import { Link, useParams } from 'react-router'

import { useCustomerRisk, useTimeline } from '../../api/hooks/ops'
import { EpisodeTimeline } from '../../components/EpisodeTimeline'
import { Card, ErrorBanner, SkeletonRows } from '../../components/States'
import { TierBadge } from '../../components/TierBadge'
import { WatchScoreChart } from '../../components/WatchScoreChart'
import { useT } from '../../i18n/lang'
import { formatINR, formatIST } from '../../lib/format'

export function CustomerRiskPage() {
  const t = useT()
  const { id } = useParams()
  const risk = useCustomerRisk(id)
  const timeline = useTimeline(id)
  if (risk.isPending) return <SkeletonRows rows={8} />
  if (risk.isError)
    return (
      <main className="p-4">
        <ErrorBanner message={risk.error.message} onRetry={() => void risk.refetch()} />
      </main>
    )
  const r = risk.data
  return (
    <main className="mx-auto max-w-[1440px] space-y-4 p-4">
      <Link to="/ops" className="text-sm text-primary underline">
        {t('case.back')}
      </Link>
      <header>
        <h1 className="text-xl font-bold">
          {r.customer.display_name}{' '}
          <span className="text-base font-normal text-text-muted">{r.customer.external_ref}</span>
        </h1>
        <p className="text-sm text-text-muted">
          {t('customer.language', { lang: t(`lang.${r.preferred_language as 'en'}`) })} ·{' '}
          {r.accounts.map((a) => `${a.account_type} ${a.masked_number}`).join(' · ')}
        </p>
      </header>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={t('customer.baseline')}>
          {r.baseline ? (
            <dl className="space-y-1 text-sm">
              <dt className="text-text-muted">{t('customer.median')}</dt>
              <dd className="text-lg font-semibold">
                {formatINR(r.baseline.median_outbound_paise)}
              </dd>
              <dd>
                {t('customer.history', {
                  days: r.baseline.history_days,
                  count: r.baseline.qualifying_transfer_count,
                })}
              </dd>
              <dd>{t(`customer.confidence.${r.baseline.confidence as 'OK'}`)}</dd>
            </dl>
          ) : (
            <p className="text-sm text-text-muted">—</p>
          )}
        </Card>
        <Card title={t('customer.episode')} className="lg:col-span-2">
          {r.episode ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <TierBadge tier={r.episode.watch_tier} />
                <span className="text-sm">
                  {t('ops.watch_score', { score: r.episode.watch_score })} · {r.episode.status}
                </span>
              </div>
              <WatchScoreChart history={r.episode.watch_history} height={160} />
              <EpisodeTimeline episode={r.episode} />
            </div>
          ) : (
            <p className="text-sm text-text-muted">{t('customer.no_episode')}</p>
          )}
        </Card>
      </div>
      <Card title={t('customer.recent')}>
        <ul className="divide-y divide-border text-sm">
          {r.recent_assessments.map((a) => (
            <li
              key={a.transfer_ref + a.assessed_at}
              className="flex flex-wrap items-center gap-2 py-2"
            >
              <span className="text-text-muted">{formatIST(a.assessed_at)}</span>
              <span className="font-semibold">{a.transfer_ref}</span>
              <span className="tabular-nums">{formatINR(a.amount_paise)}</span>
              <TierBadge tier={a.tier} size="sm" />
              <span>
                {a.decision} · {a.score}
              </span>
              {a.hold_id && (
                <Link className="text-primary underline" to={`/ops/holds/${a.hold_id}`}>
                  {t('ops.preview.open')}
                </Link>
              )}
            </li>
          ))}
        </ul>
      </Card>
      <Card title={t('customer.timeline', { days: 14 })}>
        <table className="w-full text-left text-sm">
          <tbody>
            {(timeline.data ?? []).map((item, i) => (
              <tr key={i} className="border-b border-border">
                <td className="whitespace-nowrap py-1 pr-3 text-text-muted">
                  {formatIST(item.at)}
                </td>
                <td className="pr-3 text-xs">{item.kind}</td>
                <td className="pr-3">{item.title}</td>
                <td className="pr-3 text-xs">{item.stage}</td>
                <td className="tabular-nums">
                  {item.amount_paise != null ? formatINR(item.amount_paise) : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </main>
  )
}
