import { Link, useParams } from 'react-router'

import { useHold } from '../../api/hooks/ops'
import type { HoldDetail } from '../../api/types'
import { useAuth } from '../../app/auth'
import { EpisodeTimeline } from '../../components/EpisodeTimeline'
import { HoldStatusChip } from '../../components/HoldStatusChip'
import { ReasonList } from '../../components/ReasonList'
import { ScoreBreakdownBar } from '../../components/ScoreBreakdownBar'
import { Card, ErrorBanner, SkeletonRows } from '../../components/States'
import { TierBadge } from '../../components/TierBadge'
import { WatchScoreChart } from '../../components/WatchScoreChart'
import { useT } from '../../i18n/lang'
import { formatINR, formatIST } from '../../lib/format'
import { DecisionPanel } from './DecisionPanel'
import { ReportSection } from './ReportDraft'

function payeeAge(hold: HoldDetail): string {
  const hours = Math.floor(
    (Date.parse(hold.transfer.initiated_at) - Date.parse(hold.payee.added_at)) / 3_600_000,
  )
  if (hours < 1) return '< 1 h'
  return hours < 48 ? `${hours} h` : `${Math.floor(hours / 24)} d`
}

export function HoldDetailPage({ backTo = '/ops' }: { backTo?: string }) {
  const t = useT()
  const { holdId } = useParams()
  const { user } = useAuth()
  const query = useHold(holdId)
  if (query.isPending) return <SkeletonRows rows={8} />
  if (query.isError && !query.data)
    return (
      <main className="p-4">
        <ErrorBanner message={query.error.message} onRetry={() => void query.refetch()} />
      </main>
    )
  const hold = query.data
  const latest = hold.assessments[hold.assessments.length - 1]
  return (
    <main className="mx-auto max-w-[1440px] space-y-4 p-4">
      <Link to={backTo} className="text-sm text-primary underline">
        {t('case.back')}
      </Link>
      {query.isError && <ErrorBanner message={t('app.reconnecting')} />}
      <header className="flex flex-wrap items-center gap-3">
        <TierBadge tier={hold.tier} size="lg" />
        <h1 className="text-xl font-bold">
          {t('case.header', {
            amount: formatINR(hold.transfer.amount_paise),
            rail: hold.transfer.rail,
            age: payeeAge(hold),
          })}
        </h1>
        <HoldStatusChip status={hold.status} contactResponse={hold.contact_response} />
        <Link to={`/ops/customers/${hold.customer.id}`} className="text-sm text-primary underline">
          {t('case.customer', { name: hold.customer.display_name })}
        </Link>
      </header>
      <div className="grid gap-4 lg:grid-cols-[65fr_35fr]">
        <div className="space-y-4">
          <Card
            title={t('case.why')}
            actions={
              <span className="text-sm font-semibold">
                {t('case.score', { score: latest.score, raw: latest.raw_score })}
              </span>
            }
          >
            <ReasonList reasons={latest.reasons} />
            <div className="mt-4">
              <p className="mb-1 text-xs font-semibold uppercase text-text-muted">
                {t('case.breakdown')}
              </p>
              <ScoreBreakdownBar reasons={latest.reasons} />
            </div>
          </Card>
          {hold.episode && (
            <>
              <Card title={t('case.timeline')}>
                <EpisodeTimeline episode={hold.episode} id="episode-timeline" />
              </Card>
              <Card title={t('case.watch_chart')}>
                <p id="watch-chart-desc" className="sr-only">
                  {t('case.watch_chart_desc')}
                </p>
                <WatchScoreChart
                  history={hold.episode.watch_history}
                  describedBy="watch-chart-desc"
                />
              </Card>
            </>
          )}
          <Card title={t('case.history')}>
            <ol className="space-y-1 text-sm">
              {hold.assessments.map((a) => (
                <li key={a.assessment_id} className="flex flex-wrap items-center gap-2">
                  <span className="text-text-muted">{formatIST(a.assessed_at)}</span>
                  <span className="font-semibold">
                    {t(`case.trigger.${a.trigger as 'INITIAL'}`)}
                  </span>
                  <TierBadge tier={a.tier} size="sm" />
                  <span>
                    {a.decision} · {a.score}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
          <Card title={t('case.payee')}>
            <p className="text-sm">
              {hold.payee.display_name} · {hold.payee.bank_name} · {hold.payee.ifsc} ·{' '}
              {hold.payee.masked_account}
              {hold.payee.linked_msisdn_last4 && ` · ☎ …${hold.payee.linked_msisdn_last4}`}
            </p>
          </Card>
        </div>
        <div className="space-y-4">
          <Card title={t('decision.title')}>
            <DecisionPanel
              hold={hold}
              canDecide={user?.role === 'OFFICER'}
              canResend={user?.role === 'OFFICER' || user?.role === 'TELLER'}
            />
          </Card>
          <Card title={t('report.title')}>
            {user?.role === 'ADMIN' ? (
              <p className="text-sm text-text-muted">
                {hold.report_id ? t('report.status.DRAFT') : '—'}
              </p>
            ) : (
              <ReportSection
                holdId={hold.id}
                reportId={hold.report_id ?? null}
                canFile={user?.role === 'OFFICER'}
              />
            )}
          </Card>
          <Card title={t('case.audit')}>
            <ol className="space-y-1 text-xs">
              {hold.audit.slice(0, 5).map((a, i) => (
                <li key={i}>
                  <span className="text-text-muted">{formatIST(a.occurred_at)}</span> {a.action} ·{' '}
                  {a.actor_type}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </main>
  )
}
