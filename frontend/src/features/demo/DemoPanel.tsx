import { useState } from 'react'

import { ApiError } from '../../api/client'
import {
  useClock,
  useConsoleMessages,
  useResetDemo,
  useRunScenario,
  useRuns,
  useScenarios,
  useSetFri,
} from '../../api/hooks/demo'
import { Button } from '../../components/Button'
import { Dialog } from '../../components/Dialog'
import { Field, inputClass } from '../../components/Field'
import { QrCode } from '../../components/QrCode'
import { Card, EmptyState } from '../../components/States'
import { useToast } from '../../components/Toast'
import { useT } from '../../i18n/lang'
import { demoDay, formatIST } from '../../lib/format'

const SPEEDS = [1, 60, 1440, 4320]
const E164 = /^\+[1-9]\d{7,14}$/

/** FR-17: the presenter runs the whole demo from here (DEMO_SCRIPT.md). */
export function DemoPanel() {
  const t = useT()
  const toast = useToast()
  const clock = useClock()
  const scenarios = useScenarios()
  const runs = useRuns()
  const messages = useConsoleMessages()
  const reset = useResetDemo()
  const run = useRunScenario()
  const setFri = useSetFri()
  const [speed, setSpeed] = useState(4320)
  const [confirmReset, setConfirmReset] = useState(false)
  const [msisdn, setMsisdn] = useState('')
  const [rating, setRating] = useState<'MEDIUM' | 'HIGH' | 'VERY_HIGH'>('HIGH')
  const [friError, setFriError] = useState<string | null>(null)
  const latest = messages.data?.[0]

  return (
    <main className="mx-auto max-w-[1440px] space-y-4 p-4">
      <h1 className="text-xl font-bold">{t('demo.title')}</h1>
      <p className="text-sm text-text-muted">{t('demo.honesty')}</p>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={t('demo.clock')}>
          {clock.data && (
            <div className="space-y-1">
              <p className="text-3xl font-bold tabular-nums">{formatIST(clock.data.sim_now)}</p>
              <p className="text-lg">{t('app.day', { n: demoDay(clock.data.sim_now) })}</p>
              <p className="text-sm text-text-muted">
                {clock.data.running_scenario
                  ? t('demo.running', { id: clock.data.running_scenario })
                  : t('demo.idle')}
              </p>
            </div>
          )}
          <fieldset className="mt-4">
            <legend className="text-sm font-semibold">{t('demo.speed')}</legend>
            <div className="mt-1 flex flex-wrap gap-1">
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={speed === s}
                  onClick={() => setSpeed(s)}
                  className={`min-h-9 rounded border px-3 text-sm font-semibold ${speed === s ? 'border-primary bg-primary text-white' : 'border-border'}`}
                >
                  {t('app.speed', { speed: s })}
                </button>
              ))}
            </div>
          </fieldset>
          <Button variant="danger" className="mt-4" onClick={() => setConfirmReset(true)}>
            {t('demo.reset')}
          </Button>
          <div className="mt-4">
            <p className="text-sm font-semibold">{t('demo.open_tabs')}</p>
            <div className="mt-1 flex flex-wrap gap-3 text-sm">
              <a className="text-primary underline" href="/ops" target="_blank" rel="noreferrer">
                {t('demo.open_ops')}
              </a>
              <a className="text-primary underline" href="/teller" target="_blank" rel="noreferrer">
                {t('demo.open_teller')}
              </a>
              <a
                className="text-primary underline"
                href="/customer"
                target="_blank"
                rel="noreferrer"
              >
                {t('demo.open_customer')}
              </a>
            </div>
          </div>
        </Card>
        <Card title={t('demo.console')} className="lg:col-span-2">
          {!latest ? (
            <EmptyState title={t('demo.console_empty')} icon="✉" />
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row">
              {latest.link && <QrCode value={latest.link} label={t('demo.qr')} size={200} />}
              <div className="min-w-0 space-y-2">
                <p className="text-sm text-text-muted">{t('demo.console_hint')}</p>
                {latest.link && (
                  <a
                    href={latest.link}
                    target="_blank"
                    rel="noreferrer"
                    className="block break-all text-lg font-semibold text-primary underline"
                  >
                    {latest.link}
                  </a>
                )}
                <ul className="space-y-1 text-sm">
                  {messages.data?.map((m, i) => (
                    <li key={i} className="rounded bg-bg p-2">
                      <span className="text-text-muted">
                        {formatIST(m.at)} → {m.to}:{' '}
                      </span>
                      {m.text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>
      </div>
      <Card title={t('demo.scenarios')}>
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {scenarios.data?.map((s) => (
            <li key={s.id} className="flex flex-col gap-2 rounded border border-border p-3">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold">{s.id}</span>
                <span
                  className={`rounded px-1.5 text-xs font-bold ${s.label === 'coercion' ? 'bg-tier-very-high/10 text-tier-very-high' : 'bg-success/10 text-success'}`}
                >
                  {t(`demo.label.${s.label}`)}
                </span>
                {s.held_out && (
                  <span className="text-xs text-text-muted">({t('demo.held_out')})</span>
                )}
              </div>
              <p className="font-semibold">{s.title}</p>
              <p className="text-sm text-text-muted">
                {s.customer_name} · {s.customer_ref}
              </p>
              <p className="text-sm">{s.description}</p>
              <p className="text-sm">
                {t('demo.expected', {
                  decision: `${s.expected_decision}${s.expected_tier ? ` (${s.expected_tier})` : ''}`,
                })}
              </p>
              <Button
                size="sm"
                className="mt-auto self-start"
                loading={run.isPending && run.variables?.id === s.id}
                onClick={() =>
                  run.mutate(
                    { id: s.id, speed },
                    {
                      onSuccess: () => toast(t('demo.run_started', { id: s.id }), 'info'),
                      onError: (e) => toast(e.message, 'error'),
                    },
                  )
                }
              >
                {t('demo.run')} {s.id}
              </Button>
            </li>
          ))}
        </ul>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t('demo.runs')}>
          {!runs.data?.length ? (
            <p className="text-sm text-text-muted">{t('demo.no_runs')}</p>
          ) : (
            <ul className="space-y-3">
              {runs.data.map((r) => (
                <li key={r.run_id} className="text-sm">
                  <p className="font-semibold">
                    {r.scenario_id} · {r.status} · {t('app.speed', { speed: r.speed })}
                  </p>
                  {r.error && <p className="text-tier-very-high">{r.error}</p>}
                  <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-bg p-2 font-mono text-xs">
                    {r.lines.join('\n')}
                  </pre>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('demo.fri')}>
          <form
            className="space-y-3"
            noValidate
            onSubmit={(e) => {
              e.preventDefault()
              if (!E164.test(msisdn.trim())) {
                setFriError(t('demo.fri_err'))
                return
              }
              setFriError(null)
              setFri.mutate(
                { linked_msisdn: msisdn.trim(), rating },
                {
                  onSuccess: () => toast(t('demo.fri_saved')),
                  onError: (e) =>
                    toast(e instanceof ApiError ? e.message : t('app.error_generic'), 'error'),
                },
              )
            }}
          >
            <Field label={t('demo.fri_number')} error={friError}>
              {(p) => (
                <input
                  id={p.id}
                  aria-invalid={p.invalid}
                  aria-describedby={p.describedBy}
                  className={inputClass}
                  value={msisdn}
                  placeholder="+919800000193"
                  onChange={(e) => setMsisdn(e.target.value)}
                />
              )}
            </Field>
            <Field label={t('demo.fri_rating')}>
              {(p) => (
                <select
                  id={p.id}
                  className={inputClass}
                  value={rating}
                  onChange={(e) => setRating(e.target.value as typeof rating)}
                >
                  <option>MEDIUM</option>
                  <option>HIGH</option>
                  <option>VERY_HIGH</option>
                </select>
              )}
            </Field>
            <Button type="submit" loading={setFri.isPending}>
              {t('demo.fri_save')}
            </Button>
          </form>
        </Card>
      </div>
      <Dialog
        open={confirmReset}
        title={t('demo.reset_confirm')}
        confirmLabel={t('demo.reset')}
        confirmVariant="danger"
        busy={reset.isPending}
        onClose={() => setConfirmReset(false)}
        onConfirm={() =>
          reset.mutate(undefined, {
            onSuccess: (out) => {
              toast(t('demo.reset_done', { s: out.seconds }))
              setConfirmReset(false)
            },
            onError: () => {
              toast(t('app.error_generic'), 'error')
              setConfirmReset(false)
            },
          })
        }
      />
    </main>
  )
}
