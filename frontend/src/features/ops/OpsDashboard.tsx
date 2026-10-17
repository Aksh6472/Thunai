import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { useAlerts, useSummary, type AlertKind } from '../../api/hooks/ops'
import type { AlertItem, Tier } from '../../api/types'
import { useAuth } from '../../app/auth'
import { HoldStatusChip } from '../../components/HoldStatusChip'
import { Icon } from '../../components/Icon'
import { KpiFilterButton } from '../../components/KpiFilterButton'
import { ShieldIllustration } from '../../components/ShieldIllustration'
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
  const { user } = useAuth()
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
  const firstHold = (alerts.data?.items ?? []).find((i) => i.kind === 'HOLD')
  const toggle = (k: Exclude<Kpi, null>) => setKpi(kpi === k ? null : k)
  return (
    <main className="mx-auto max-w-[1440px] space-y-6 p-4 md:p-8 md:pt-4">
      <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-lilac via-surface-2 to-blush px-6 py-8 md:px-10 md:py-10">
        <span
          aria-hidden="true"
          className="absolute -right-10 -top-16 h-56 w-56 rounded-full bg-accent/20 blur-2xl"
        />
        <div className="relative grid items-center gap-6 md:grid-cols-[1.4fr_1fr]">
          <div className="space-y-4">
            <p className="text-sm font-semibold text-primary">
              {t('ops.hero.hello', { name: user?.display_name ?? '' })}
            </p>
            <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-brand md:text-[40px]">
              {t('ops.hero.title')}{' '}
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                {t('ops.hero.title_accent')}
              </span>
            </h1>
            <p className="max-w-[560px] text-lg text-text-muted">
              {t('ops.hero.body', { n: s?.awaiting_officer ?? 0 })}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {firstHold ? (
                <Link
                  to={alertHref(firstHold)}
                  className="inline-flex min-h-12 items-center gap-2 rounded-full bg-brand px-6 font-semibold text-white shadow-[var(--shadow-raised)] hover:bg-brand-2"
                >
                  {t('ops.hero.cta')}
                  <Icon name="arrow" className="h-4 w-4" />
                </Link>
              ) : null}
              <span className="inline-flex items-center gap-3 rounded-full bg-surface/85 py-1.5 pl-1.5 pr-4 shadow-[var(--shadow-card)]">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-success/10 text-success">
                  <Icon name="rupee" className="h-4 w-4" />
                </span>
                <span className="leading-tight">
                  <span className="block text-xs text-text-muted">
                    {t('ops.kpi.amount_on_hold_label')} · {t('app.synthetic')}
                  </span>
                  <span className="block font-bold tabular-nums">
                    {s ? formatINR(s.amount_on_hold_paise) : '—'}
                  </span>
                </span>
                <span className="sr-only">
                  {s && t('ops.kpi.amount_on_hold', { amount: formatINR(s.amount_on_hold_paise) })}
                </span>
              </span>
            </div>
          </div>
          <div className="relative hidden flex-col items-end gap-3 md:flex">
            <ShieldIllustration className="h-[170px] w-auto" />
            <p className="max-w-[260px] rounded-[18px] bg-surface/85 px-4 py-3 text-right text-sm italic text-text-muted shadow-[var(--shadow-card)] backdrop-blur">
              {t('ops.hero.quote')}
            </p>
          </div>
        </div>
      </section>
      <p className="sr-only">{t('ops.subtitle')}</p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiFilterButton
          label={t('ops.kpi.awaiting_officer')}
          count={s?.awaiting_officer ?? 0}
          active={kpi === 'AWAITING_OFFICER'}
          onClick={() => toggle('AWAITING_OFFICER')}
          tone="very-high"
          icon="alert"
          note={t('ops.kpi.note.officer')}
        />
        <KpiFilterButton
          label={t('ops.kpi.awaiting_contact')}
          count={s?.awaiting_contact ?? 0}
          active={kpi === 'AWAITING_CONTACT'}
          onClick={() => toggle('AWAITING_CONTACT')}
          tone="high"
          icon="phone"
          note={t('ops.kpi.note.contact')}
        />
        <KpiFilterButton
          label={t('ops.kpi.warnings_today')}
          count={s?.warnings_today ?? 0}
          active={kpi === 'WARN'}
          onClick={() => toggle('WARN')}
          tone="medium"
          icon="shield"
          note={t('ops.kpi.note.warn')}
        />
        <KpiFilterButton
          label={t('ops.kpi.watchlist')}
          count={s?.watchlist_count ?? 0}
          active={kpi === 'WATCH'}
          onClick={() => toggle('WATCH')}
          tone="primary"
          icon="eye"
          note={t('ops.kpi.note.watch')}
        />
      </div>
      {(alerts.isError || summary.isError) && (
        <ErrorBanner message={t('app.reconnecting')} onRetry={() => void alerts.refetch()} />
      )}
      <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
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
          <div role="tablist" className="mb-4 inline-flex gap-1 rounded-full bg-surface-2 p-1">
            {TABS.map((tb) => (
              <button
                key={tb.id}
                role="tab"
                aria-selected={tab === tb.id}
                onClick={() => {
                  setTab(tb.id)
                  setKpi(null)
                }}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${tab === tb.id ? 'bg-surface text-primary shadow-sm' : 'text-text-muted hover:text-text'}`}
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
                  className={`flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-[16px] border-l-4 px-4 py-3.5 transition-colors ${ROW_EDGE[item.tier]} ${item.id === current?.id ? 'bg-lilac' : 'hover:bg-surface-2'} ${fresh.has(item.id) ? 'animate-pulse' : ''}`}
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
        <div className="space-y-6 lg:sticky lg:top-6">
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
            className="inline-flex min-h-10 items-center rounded-full bg-primary px-5 text-sm font-semibold text-white hover:bg-primary-strong"
          >
            {t('ops.preview.open')}
          </Link>
        )}
        <Link
          to={`/ops/customers/${item.customer.id}`}
          className="inline-flex min-h-10 items-center rounded-full border border-primary/30 px-5 text-sm font-semibold text-primary hover:bg-lilac"
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
