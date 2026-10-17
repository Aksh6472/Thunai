import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { ApiError } from '../../api/client'
import { useHold } from '../../api/hooks/ops'
import { useChecklist, useScript, useTellerQueue, type TellerItem } from '../../api/hooks/teller'
import type { HoldListItem, Lang, Reason } from '../../api/types'
import { useAuth } from '../../app/auth'
import { Button } from '../../components/Button'
import { ChecklistToggle } from '../../components/ChecklistToggle'
import { inputClass } from '../../components/Field'
import { LanguageToggle } from '../../components/LanguageToggle'
import { ReasonList } from '../../components/ReasonList'
import { sortReasons } from '../../components/reasons'
import { ScriptPanel } from '../../components/ScriptPanel'
import { Card, EmptyState, ErrorBanner, SkeletonRows } from '../../components/States'
import { TierBadge } from '../../components/TierBadge'
import { useToast } from '../../components/Toast'
import { useT } from '../../i18n/lang'
import { formatINR } from '../../lib/format'
import { ReportSection } from '../ops/ReportDraft'

const ITEMS: TellerItem[] = [
  'ON_CALL',
  'DISTRESSED',
  'FOLLOWING_INSTRUCTIONS',
  'MENTIONS_AUTHORITY',
]

export function TellerConsole() {
  const t = useT()
  const { holdId } = useParams()
  const navigate = useNavigate()
  const queue = useTellerQueue()
  const items = queue.data?.items ?? []
  const [selectedRef, setSelectedRef] = useState<string | null>(null)
  const selected = holdId
    ? items.find((i) => i.id === holdId)
    : (items.find((i) => i.transfer_ref === selectedRef) ?? items[0])
  const urgent = items.find((i) => i.tier === 'VERY_HIGH' && i.transfer_status === 'HELD')

  return (
    <main className="mx-auto max-w-[1440px] space-y-4 p-4">
      <h1 className="sr-only">{t('teller.title')}</h1>
      <div aria-live="assertive" role="alert" className="min-h-0">
        {urgent && (
          <div className="flex items-center gap-3 rounded-[var(--radius-card)] border-2 border-tier-very-high bg-tier-very-high/10 px-4 py-3 font-semibold text-tier-very-high">
            <span aria-hidden="true" className="text-xl">
              ⚠
            </span>
            {t('teller.alert', {
              name: urgent.customer.display_name,
              amount: formatINR(urgent.amount_paise),
            })}
          </div>
        )}
      </div>
      {queue.isError && (
        <ErrorBanner message={t('app.reconnecting')} onRetry={() => void queue.refetch()} />
      )}
      <div className="grid gap-4 lg:grid-cols-[1fr_3fr]">
        <Card title={t('teller.queue')}>
          {queue.isPending ? (
            <SkeletonRows rows={3} />
          ) : items.length === 0 ? (
            <EmptyState title={t('teller.empty')} />
          ) : (
            <ul className="space-y-2" aria-live="polite">
              {items.map((item) => (
                <li key={item.transfer_ref}>
                  <button
                    type="button"
                    onClick={() =>
                      item.id
                        ? navigate(`/teller/holds/${item.id}`)
                        : setSelectedRef(item.transfer_ref)
                    }
                    aria-current={selected?.transfer_ref === item.transfer_ref || undefined}
                    className={`w-full rounded border px-3 py-2 text-left ${selected?.transfer_ref === item.transfer_ref ? 'border-primary bg-primary/10' : 'border-border'}`}
                  >
                    <span className="flex items-center gap-2">
                      <TierBadge tier={item.tier} size="sm" />
                      <span className="font-semibold">{item.customer.display_name}</span>
                    </span>
                    <span className="text-sm tabular-nums">{formatINR(item.amount_paise)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        {selected ? <CaseAtCounter key={selected.transfer_ref} item={selected} /> : null}
      </div>
    </main>
  )
}

function CaseAtCounter({ item }: { item: HoldListItem }) {
  const t = useT()
  const toast = useToast()
  const { user } = useAuth()
  const hold = useHold(item.id ?? undefined)
  const checklist = useChecklist(item.transfer_ref)
  const [pressed, setPressed] = useState<Set<TellerItem>>(new Set())
  const [said, setSaid] = useState('')
  const [scriptLang, setScriptLang] = useState<Lang>('ta')
  const script = useScript(item.id ?? undefined, scriptLang)
  const latestFromHold = hold.data?.assessments[hold.data.assessments.length - 1]
  const result = checklist.data ?? latestFromHold
  const allReasons: Reason[] = result?.reasons ?? item.top_reasons
  // Top 5 engine reasons, plus every teller observation once applied (DESIGN §5.5).
  const isTeller = (r: Reason) => r.code.startsWith('TELLER_')
  const reasons = [
    ...sortReasons(allReasons.filter((r) => !isTeller(r))).slice(0, 5),
    ...allReasons.filter(isTeller),
  ]
  const busy = checklist.isPending
  const done = item.transfer_status === 'EXECUTED' || item.transfer_status === 'CANCELLED'

  function toggle(i: TellerItem) {
    setPressed((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
      const index = Number(e.key) - 1
      if (index >= 0 && index < ITEMS.length && !busy) toggle(ITEMS[index])
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy])

  async function apply() {
    try {
      const out = await checklist.mutateAsync({
        items: [...pressed],
        ...(said.trim() ? { customer_said: said.trim() } : {}),
      })
      toast(t('teller.applied', { score: out.score }))
    } catch (e) {
      const msg =
        e instanceof ApiError && e.status === 409
          ? t('teller.completed', { status: t(`status.${item.transfer_status}`) })
          : e instanceof ApiError
            ? e.message
            : t('app.error_generic')
      toast(msg, 'error')
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[55fr_45fr]">
      <div className="space-y-4">
        <Card title={t('teller.noticed')}>
          <div className="mb-2 flex items-center gap-2">
            <TierBadge tier={result?.tier ?? item.tier} />
            <span className="font-semibold">{item.customer.display_name}</span>
            <span className="tabular-nums">{formatINR(item.amount_paise)}</span>
          </div>
          <ReasonList reasons={reasons} />
        </Card>
        <Card title={t('teller.observe')}>
          <div className="grid gap-2 sm:grid-cols-2">
            {ITEMS.map((i, idx) => (
              <ChecklistToggle
                key={i}
                label={t(`teller.item.${i}`)}
                hotkey={idx + 1}
                pressed={pressed.has(i)}
                disabled={busy || done}
                onToggle={() => toggle(i)}
              />
            ))}
          </div>
          <label htmlFor="customer-said" className="mt-4 block text-sm font-semibold">
            {t('teller.customer_said')}
          </label>
          <textarea
            id="customer-said"
            className={`${inputClass} mt-1 py-2`}
            rows={2}
            maxLength={500}
            value={said}
            onChange={(e) => setSaid(e.target.value)}
            aria-describedby="customer-said-note"
            disabled={done}
          />
          <p id="customer-said-note" className="mt-1 text-xs text-text-muted">
            {t('teller.customer_said_note')} · {t('teller.chars', { n: said.length })}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={apply} loading={busy} disabled={done}>
              {t('teller.apply')}
            </Button>
            {result && (
              <span className="text-sm font-semibold" aria-live="polite">
                {t('teller.score', { score: result.score, tier: t(`tier.${result.tier}`) })}
              </span>
            )}
          </div>
        </Card>
      </div>
      <div className="space-y-4">
        <Card
          title={t('teller.script')}
          actions={<LanguageToggle value={scriptLang} onChange={setScriptLang} />}
        >
          {!item.id ? (
            <p className="text-sm text-text-muted">—</p>
          ) : script.data ? (
            <ScriptPanel script={script.data} lang={scriptLang} />
          ) : (
            <SkeletonRows rows={3} />
          )}
        </Card>
        {item.id && (
          <Card title={t('report.title')}>
            <ReportSection
              holdId={item.id}
              reportId={hold.data?.report_id ?? null}
              canFile={user?.role === 'OFFICER'}
            />
            {user?.role === 'OFFICER' && (
              <Link
                to={`/ops/holds/${item.id}`}
                className="mt-3 inline-block text-sm text-primary underline"
              >
                {t('ops.preview.open')}
              </Link>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
