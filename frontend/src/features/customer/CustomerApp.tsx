import { useState } from 'react'

import { ApiError } from '../../api/client'
import {
  useCancelHeld,
  useCreateTransfer,
  useOverview,
  useTransferStatus,
  useWarningResponse,
} from '../../api/hooks/customer'
import type { CustomerTransferIn } from '../../api/types'
import { useAuth } from '../../app/auth'
import { BANK_NAME } from '../../config/brand'
import { Button } from '../../components/Button'
import { LanguageToggle } from '../../components/LanguageToggle'
import { PhoneFrame } from '../../components/PhoneFrame'
import { ErrorBanner, SkeletonRows } from '../../components/States'
import { LangProvider, useLang, useT } from '../../i18n/lang'
import { formatINR, formatIST } from '../../lib/format'
import { HoldScreen } from './HoldScreen'
import { SendMoney } from './SendMoney'
import { Settings } from './Settings'
import { WarningScreen } from './WarningScreen'

type Screen =
  { name: 'home' } | { name: 'send' } | { name: 'settings' } | { name: 'transfer'; ref: string }

export function CustomerApp() {
  const overview = useOverview()
  // Tamil first when that is the customer's preference (DESIGN §1.4).
  return (
    <LangProvider
      key={overview.data?.customer_ref ?? 'loading'}
      initial={overview.data?.preferred_language ?? 'en'}
    >
      <CustomerAppScreens />
    </LangProvider>
  )
}

function CustomerAppScreens() {
  const t = useT()
  const { lang, setLang } = useLang()
  const { logout } = useAuth()
  const overview = useOverview()
  const [screen, setScreen] = useState<Screen>({ name: 'home' })
  const create = useCreateTransfer()
  const [serverError, setServerError] = useState<string | null>(null)

  async function submit(body: CustomerTransferIn) {
    setServerError(null)
    try {
      const out = await create.mutateAsync(body)
      setScreen({ name: 'transfer', ref: out.transfer_ref })
    } catch (e) {
      if (e instanceof ApiError && e.code === 'INSUFFICIENT_BALANCE')
        setServerError(t('cust.err.balance'))
      else setServerError(t('cust.err.unavailable'))
    }
  }

  return (
    <PhoneFrame>
      <header className="flex items-center justify-between gap-2 bg-gradient-to-r from-brand to-brand-2 px-4 py-3 text-white">
        <span className="font-bold">{t('cust.app', { bank: BANK_NAME })}</span>
        <LanguageToggle value={lang} onChange={setLang} />
      </header>
      <div lang={lang}>
        {overview.isPending ? (
          <SkeletonRows />
        ) : overview.isError ? (
          <div className="p-4">
            <ErrorBanner
              message={t('cust.err.unavailable')}
              onRetry={() => void overview.refetch()}
            />
          </div>
        ) : screen.name === 'send' ? (
          <SendMoney
            overview={overview.data}
            onSubmit={submit}
            busy={create.isPending}
            serverError={serverError}
            onBack={() => setScreen({ name: 'home' })}
          />
        ) : screen.name === 'settings' ? (
          <Settings overview={overview.data} onBack={() => setScreen({ name: 'home' })} />
        ) : screen.name === 'transfer' ? (
          <TransferOutcome transferRef={screen.ref} onDone={() => setScreen({ name: 'home' })} />
        ) : (
          <section className="space-y-5 p-5">
            <h2 className="text-[22px] font-bold tracking-tight">
              {t('cust.greeting', { name: overview.data.display_name })}
            </h2>
            <div className="rounded-[var(--radius-card)] bg-gradient-to-br from-primary to-primary-strong p-5 text-white shadow-[var(--shadow-card)]">
              <p className="text-sm text-white/80">{t('cust.total')}</p>
              <p className="text-[30px] font-bold tracking-tight tabular-nums">
                {formatINR(overview.data.accounts.reduce((sum, a) => sum + a.balance_paise, 0))}
              </p>
            </div>
            <ul className="space-y-2">
              {overview.data.accounts.map((a) => (
                <li
                  key={a.masked_number}
                  className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-border bg-surface-2 px-4 py-3"
                >
                  <span>
                    <span className="block text-sm font-semibold">{a.account_type}</span>
                    <span className="block text-sm text-text-muted">{a.masked_number}</span>
                  </span>
                  <span className="text-lg font-bold tabular-nums">
                    {formatINR(a.balance_paise)}
                  </span>
                </li>
              ))}
            </ul>
            <Button
              size="xl"
              className="w-full"
              onClick={() => {
                setServerError(null)
                setScreen({ name: 'send' })
              }}
            >
              {t('cust.send')}
            </Button>
            <div>
              <h3 className="mb-2 font-semibold">{t('cust.recent')}</h3>
              {overview.data.recent_transfers.length === 0 ? (
                <p className="text-text-muted">{t('cust.no_recent')}</p>
              ) : (
                <ul className="divide-y divide-border">
                  {overview.data.recent_transfers.map((tr) => (
                    <li
                      key={tr.transfer_ref}
                      className="flex items-center justify-between gap-2 py-2"
                    >
                      <span>
                        <span className="block font-semibold">{tr.payee_name}</span>
                        <span className="text-sm text-text-muted">
                          {formatIST(tr.initiated_at)} ·{' '}
                          {t(`status.${tr.transfer_status as 'HELD'}`)}
                        </span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="tabular-nums">{formatINR(tr.amount_paise)}</span>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setScreen({ name: 'transfer', ref: tr.transfer_ref })}
                        >
                          {t('cust.view')}
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setScreen({ name: 'settings' })}>
                {t('cust.settings')}
              </Button>
              <Button variant="ghost" onClick={logout}>
                {t('app.logout')}
              </Button>
            </div>
          </section>
        )}
      </div>
    </PhoneFrame>
  )
}

function TransferOutcome({ transferRef, onDone }: { transferRef: string; onDone: () => void }) {
  const t = useT()
  const status = useTransferStatus(transferRef)
  const warning = useWarningResponse(transferRef)
  const cancel = useCancelHeld(transferRef)
  const data = status.data
  if (!data) return <SkeletonRows />
  if (data.transfer_status === 'WARNED') {
    return (
      <WarningScreen
        busy={warning.isPending}
        onCancel={() => warning.mutate('CANCEL')}
        onContinue={() => warning.mutate('CONTINUE')}
      />
    )
  }
  if (data.transfer_status === 'HELD') {
    return <HoldScreen transfer={data} busy={cancel.isPending} onCancel={() => cancel.mutate()} />
  }
  const released = data.transfer_status === 'EXECUTED' && Boolean(data.hold_id)
  const cancelled = data.transfer_status === 'CANCELLED'
  return (
    <section className="space-y-5 p-5 text-center" aria-live="polite">
      <span
        aria-hidden="true"
        className={`text-6xl ${cancelled ? 'text-text-muted' : 'text-success'}`}
      >
        {cancelled ? '○' : '✓'}
      </span>
      <h2 className="text-[28px] font-bold">
        {cancelled ? t('result.cancelled') : released ? t('result.released') : t('result.executed')}
      </h2>
      <Button size="xl" className="w-full" onClick={onDone}>
        {t('result.done')}
      </Button>
    </section>
  )
}
