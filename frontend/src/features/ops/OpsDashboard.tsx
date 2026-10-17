import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { useAlerts, useSummary, type AlertKind } from '../../api/hooks/ops'
import type { AlertItem, Tier } from '../../api/types'
import { HoldStatusChip } from '../../components/HoldStatusChip'
import { KpiFilterButton } from '../../components/KpiFilterButton'
import { Card, EmptyState, ErrorBanner, SkeletonRows } from '../../components/States'
import { TierBadge } from '../../components/TierBadge'
import { useT } from '../../i18n/lang'
import { formatINR, secondsSince, timeLeft } from '../../lib/format'

type Tab = 'ALL' | AlertKind
type Kpi = 'AWAITING_OFFICER' | 'AWAITING_CONTACT' | 'WARN' | 'WATCH' | null
const TABS: {
  id: Tab
  key: 'ops.tab.all' | 'ops.tab.holds' | 'ops.tab.warnings' | 'ops.tab.watchlist'
}[] = [
  { id: 'ALL', key: 'ops.tab.all' },
  { id: 'HOLD', key: 'ops.tab.holds' },
  { id: 'WARN', key: 'ops.tab.warnings' },
  { id: 'WATCH', key: 'ops.tab.watchlist' },
]

const ROW_EDGE: Record<Tier, string> = {
  LOW: 'border-l-tier-low',
  MEDIUM: 'border-l-tier-medium',
  HIGH: 'border-l-tier-high',
  VERY_HIGH: 'border-l-tier-very-high',
}
const TIERS: Tier[] = ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW']
const BAR: Record<Tier, string> = {
  LOW: 'bg-tier-low',
  MEDIUM: 'bg-tier-medium',
  HIGH: 'bg-tier-high',
  VERY_HIGH: 'bg-tier-very-high',
}

export function alertHref(item: AlertItem): string {
  if (item.kind === 'HOLD' && item.hold_id) return `/ops/holds/${item.hold_id}`
  return `/ops/customers/${item.customer.id}`
}

export function OpsDashboard() {
  const t = useT()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('ALL')
  const [kpi, setKpi] = useState<Kpi>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const summary = useSummary()
  const alerts = useAlerts(tab === 'ALL' ? undefined : tab)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const items = useMemo(() => {
    const all = alerts.data?.items ?? []
    if (kpi === 'AWAITING_OFFICER' || kpi === 'AWAITING_CONTACT')
      return all.filter((a) => a.kind === 'HOLD' && a.status === kpi)
    if (kpi === 'WARN' || kpi === 'WATCH') return all.filter((a) => a.kind === kpi)
    return all
  }, [alerts.data, kpi])
  const current = items.find((i) => i.id === selected) ?? items[0]
  // Highlight rows that arrived since the previous poll (DESIGN §5.2).
  const ids = items.map((i) => i.id)
  const [snapshot, setSnapshot] = useState<{ ids: string[]; fresh: string[] }>({
    ids: [],
    fresh: [],
  })
  if (ids.join('|') !== snapshot.ids.join('|')) {
    setSnapshot({
      ids,
      fresh: snapshot.ids.length ? ids.filter((id) => !snapshot.ids.includes(id)) : [],
    })
  }
  const fresh = new Set(snapshot.fresh)

  function onKeyDown(e: React.KeyboardEvent) {
    if (!items.length) return
    const index = Math.max(
      0,
      items.findIndex((i) => i.id === current?.id),
    )
    if (e.key === 'ArrowDown') setSelected(items[Math.min(items.length - 1, index + 1)].id)
    else if (e.key === 'ArrowUp') setSelected(items[Math.max(0, index - 1)].id)
    else if (e.key === 'Enter' && current) navigate(alertHref(current))
    else return
    e.preventDefault()
  }

  const s = summary.data
  const toggle = (k: Exclude<Kpi, null>) => setKpi(kpi === k ? null : k)
  return (
    <main className="mx-auto max-w-[1440px] space-y-5 p-4 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t('ops.title')}</h1>
          <p className="text-sm text-text-muted">{t('ops.subtitle')}</p>
        </div>
        <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 text-xs font-bold tracking-wide text-text-muted">
          {t('app.synthetic')}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiFilterButton
          label={t('ops.kpi.awaiting_officer')}
          count={s?.awaiting_officer ?? 0}
          active={kpi === 'AWAITING_OFFICER'}
          onClick={() => toggle('AWAITING_OFFICER')}
          tone="very-high"
          icon="◆"
        />
        <KpiFilterButton
          label={t('ops.kpi.awaiting_contact')}
          count={s?.awaiting_contact ?? 0}
          active={kpi === 'AWAITING_CONTACT'}
          onClick={() => toggle('AWAITING_CONTACT')}
          tone="high"
          icon="☎"
        />
        <KpiFilterButton
          label={t('ops.kpi.warnings_today')}
          count={s?.warnings_today ?? 0}
          active={kpi === 'WARN'}
          onClick={() => toggle('WARN')}
          tone="medium"
          icon="▲"
        />
        <KpiFilterButton
          label={t('ops.kpi.watchlist')}
          count={s?.watchlist_count ?? 0}
          active={kpi === 'WATCH'}
          onClick={() => toggle('WATCH')}
          tone="primary"
          icon="◎"
        />
        <div className="col-span-2 flex min-h-20 flex-col justify-center rounded-[var(--radius-card)] bg-gradient-to-br from-brand to-brand-2 px-5 py-3 text-brand-text shadow-[var(--shadow-card)] md:col-span-1">
          <span className="text-xs font-semibold uppercase tracking-[0.08em] text-brand-muted">
            {t('ops.kpi.amount_on_hold_label')}
          </span>
          <span className="mt-1 text-2xl font-bold tabular-nums text-white">
            {s ? formatINR(s.amount_on_hold_paise) : '—'}
          </span>
          <span className="sr-only">
            {s && t('ops.kpi.amount_on_hold', { amount: formatINR(s.amount_on_hold_paise) })}
          </span>
        </div>
      </div>
      {(alerts.isError || summary.isError) && (
        <ErrorBanner message={t('app.reconnecting')} onRetry={() => void alerts.refetch()} />
      )}
      <div className="grid items-start gap-5 lg:grid-cols-[3fr_2fr]">
        <Card
          title={t('ops.queue')}
          actions={
            alerts.dataUpdatedAt ? (
              <span className="text-xs text-text-muted">
                {t('app.updated_ago', { s: secondsSince(alerts.dataUpdatedAt, now) })}
              </span>
            ) : null
          }
        >
          <div role="tablist" className="mb-3 flex gap-1 border-b border-border">
            {TABS.map((tb) => (
              <button
                key={tb.id}
                role="tab"
                aria-selected={tab === tb.id}
                onClick={() => {
                  setTab(tb.id)
                  setKpi(null)
                }}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-semibold ${tab === tb.id ? 'border-primary text-primary' : 'border-transparent text-text-muted'}`}
              >
                {t(tb.key)}
              </button>
            ))}
          </div>
          {alerts.isPending ? (
            <SkeletonRows />
          ) : items.length === 0 ? (
            <EmptyState title={t('ops.empty')} detail={t('ops.empty_sub', { n: 50 })} />
          ) : (
            <ul
              role="listbox"
              aria-label={t('ops.queue')}
              aria-activedescendant={current ? `alert-${current.id}` : undefined}
              tabIndex={0}
              onKeyDown={onKeyDown}
              className={`space-y-1 outline-none ${alerts.isError ? 'opacity-60' : ''}`}
              aria-live="polite"
            >
              {items.map((item) => (
                <li
                  key={item.id}
                  id={`alert-${item.id}`}
                  role="option"
                  aria-selected={item.id === current?.id}
                  onClick={() => setSelected(item.id)}
                  onDoubleClick={() => navigate(alertHref(item))}
                  className={`flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-[var(--radius-control)] border-l-4 px-3 py-3 transition-colors ${ROW_EDGE[item.tier]} ${item.id === current?.id ? 'bg-primary/8' : 'hover:bg-surface-2'} ${fresh.has(item.id) ? 'animate-pulse' : ''}`}
                >
                  <TierBadge tier={item.tier} size="sm" />
                  <span className="font-semibold">{item.customer.display_name}</span>
                  {item.amount_paise != null && (
                    <span className="tabular-nums">{formatINR(item.amount_paise)}</span>
                  )}
                  {item.watch_score != null && (
                    <span className="text-sm text-text-muted">
                      {t('ops.watch_score', { score: item.watch_score })}
                    </span>
                  )}
                  <HoldStatusChip
                    status={item.status}
                    contactResponse={item.contact_response as never}
                  />
                  {item.channel && (
                    <span className="text-xs text-text-muted">{t(`channel.${item.channel}`)}</span>
                  )}
                  {item.cooling_off_until &&
                    item.status === 'AWAITING_CONTACT' &&
                    timeLeft(item.cooling_off_until, now) && (
                      <span className="text-xs text-text-muted">
                        {t('ops.time_left', { time: timeLeft(item.cooling_off_until, now) ?? '' })}
                      </span>
                    )}
                  {item.top_reason && (
                    <span className="basis-full truncate text-sm text-text-muted">
                      {item.top_reason.text_en}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-text-muted">{t('ops.keyboard_hint')}</p>
        </Card>
        <div className="space-y-5 lg:sticky lg:top-20">
          <Card title={current ? t(`ops.kind.${current.kind}`) : undefined}>
            {current ? (
              <Preview item={current} />
            ) : (
              <p className="text-sm text-text-muted">{t('ops.preview.none')}</p>
            )}
          </Card>
          <Card title={t('ops.mix.title')}>
            <TierMix items={alerts.data?.items ?? []} />
          </Card>
        </div>
      </div>
    </main>
  )
}

function Preview({ item }: { item: AlertItem }) {
  const t = useT()
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <TierBadge tier={item.tier} />
        <span className="text-lg font-semibold">{item.customer.display_name}</span>
        <span className="text-sm text-text-muted">{item.customer.external_ref}</span>
      </div>
      {item.amount_paise != null && (
        <p className="text-3xl font-bold tracking-tight tabular-nums">
          {formatINR(item.amount_paise)}
        </p>
      )}
      {item.top_reason && (
        <p className="rounded-[var(--radius-control)] bg-surface-2 p-3 text-sm">
          {item.top_reason.text_en}
        </p>
      )}
      {item.watch_score != null && (
        <p className="text-sm">{t('ops.watch_score', { score: item.watch_score })}</p>
      )}
      <div className="flex flex-wrap gap-3">
        {item.kind === 'HOLD' && item.hold_id && (
          <Link
            to={`/ops/holds/${item.hold_id}`}
            className="inline-flex min-h-10 items-center rounded-[var(--radius-control)] bg-primary px-4 text-sm font-semibold text-white hover:bg-primary-strong"
          >
            {t('ops.preview.open')}
          </Link>
        )}
        <Link
          to={`/ops/customers/${item.customer.id}`}
          className="inline-flex min-h-10 items-center rounded-[var(--radius-control)] border border-border px-4 text-sm font-semibold hover:bg-surface-2"
        >
          {t('ops.preview.customer')}
        </Link>
      </div>
    </div>
  )
}

/** How the open queue splits by risk level (counts only; tiers come from the API). */
function TierMix({ items }: { items: AlertItem[] }) {
  const t = useT()
  if (!items.length) return <p className="text-sm text-text-muted">{t('ops.mix.empty')}</p>
  const max = Math.max(...TIERS.map((tier) => items.filter((i) => i.tier === tier).length), 1)
  return (
    <ul className="space-y-3">
      {TIERS.map((tier) => {
        const n = items.filter((i) => i.tier === tier).length
        return (
          <li key={tier} className="grid grid-cols-[7.5rem_1fr_2rem] items-center gap-3 text-sm">
            <TierBadge tier={tier} size="sm" />
            <span className="h-2.5 overflow-hidden rounded-full bg-surface-2">
              <span
                className={`block h-full rounded-full ${BAR[tier]}`}
                style={{ width: `${(n / max) * 100}%` }}
              />
            </span>
            <span className="text-right font-semibold tabular-nums">{n}</span>
          </li>
        )
      })}
    </ul>
  )
}
