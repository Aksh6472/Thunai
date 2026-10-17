import { useState } from 'react'
import { useParams } from 'react-router'

import { ApiError } from '../../api/client'
import { useTrustedRespond, useTrustedView } from '../../api/hooks/trusted'
import type { ContactResponse, TrustedResponseOut } from '../../api/types'
import { BANK_NAME, PRODUCT_NAME } from '../../config/brand'
import { Button } from '../../components/Button'
import { LanguageToggle } from '../../components/LanguageToggle'
import { Skeleton } from '../../components/States'
import { LangProvider, useLang, useT } from '../../i18n/lang'

const OPTIONS: {
  response: ContactResponse
  key: 'contact.genuine' | 'contact.scam' | 'contact.unreachable'
  variant: 'success' | 'danger' | 'secondary'
  icon: string
}[] = [
  { response: 'CONFIRM_GENUINE', key: 'contact.genuine', variant: 'success', icon: '✓' },
  { response: 'REPORT_SUSPICIOUS', key: 'contact.scam', variant: 'danger', icon: '⚠' },
  { response: 'CANNOT_REACH', key: 'contact.unreachable', variant: 'secondary', icon: '✗' },
]

/** Standalone, mobile-first, light (DESIGN §5.7). Shows only first name, amount and channel. */
export function TrustedContactPage() {
  const { token } = useParams()
  const view = useTrustedView(token)
  return (
    <LangProvider key={view.data ? 'loaded' : 'loading'} initial={view.data?.language ?? 'en'}>
      <TrustedContactContent token={token} />
    </LangProvider>
  )
}

function TrustedContactContent({ token }: { token: string | undefined }) {
  const t = useT()
  const { lang, setLang } = useLang()
  const view = useTrustedView(token)
  const respond = useTrustedRespond(token ?? '')
  const [pending, setPending] = useState<ContactResponse | null>(null)
  const [result, setResult] = useState<TrustedResponseOut | null>(null)
  const [submitError, setSubmitError] = useState<'expired' | 'resolved' | 'network' | null>(null)

  const name = view.data?.customer_first_name ?? ''

  async function submit() {
    if (!pending) return
    try {
      setResult(await respond.mutateAsync(pending))
    } catch (e) {
      if (e instanceof ApiError && (e.status === 410 || e.status === 404)) setSubmitError('expired')
      else if (e instanceof ApiError && e.status === 409) setSubmitError('resolved')
      else setSubmitError('network')
    } finally {
      setPending(null)
    }
  }

  let body: React.ReactNode
  const loadError = view.error instanceof ApiError ? view.error : null
  if (view.isPending) {
    body = (
      <div className="space-y-3" role="status" aria-label={t('app.loading')}>
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    )
  } else if (loadError?.status === 410 || submitError === 'expired') {
    body = <p className="text-[22px] font-semibold">{t('contact.expired')}</p>
  } else if (loadError?.status === 404) {
    body = <p className="text-[22px] font-semibold">{t('contact.invalid')}</p>
  } else if (loadError?.status === 429) {
    body = <p className="text-[22px] font-semibold">{t('contact.too_many')}</p>
  } else if (view.isError) {
    body = (
      <div className="space-y-3">
        <p className="text-[22px] font-semibold">{t('contact.network')}</p>
        <Button size="xl" onClick={() => void view.refetch()}>
          {t('app.retry')}
        </Button>
      </div>
    )
  } else if (submitError === 'resolved') {
    body = <p className="text-[22px] font-semibold">{t('contact.resolved')}</p>
  } else if (result) {
    body = (
      <p className="text-[22px] font-semibold" role="status">
        {t(`contact.result.${result.result_key}`, { name })}
      </p>
    )
  } else if (view.data) {
    body = (
      <div className="space-y-5">
        <h1 className="text-[28px] font-bold leading-tight">
          {t('contact.title', { name, amount: view.data.amount_display })}
        </h1>
        <p className="text-[22px] font-semibold">
          {t('contact.call_now')} <span className="font-normal">({t('contact.not_given')})</span>
        </p>
        {submitError === 'network' && (
          <p role="alert" className="text-tier-very-high">
            {t('contact.network')}
          </p>
        )}
        <div className="flex flex-col gap-3">
          {OPTIONS.map((o) => (
            <Button
              key={o.response}
              size="xl"
              variant={o.variant}
              onClick={() => setPending(o.response)}
            >
              <span aria-hidden="true">{o.icon}</span> {t(o.key)}
            </Button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div
      className="mx-auto min-h-screen max-w-[480px] bg-surface px-4 py-5 text-[18px]"
      lang={lang}
    >
      <header className="mb-5 flex flex-wrap items-center justify-between gap-2">
        <span className="text-base font-semibold">
          {t('contact.safety_check', { product: PRODUCT_NAME, bank: BANK_NAME })}
        </span>
        <LanguageToggle value={lang} onChange={setLang} large />
      </header>
      <main>{body}</main>
      <footer className="mt-8 space-y-2 border-t border-border pt-4 text-base text-text-muted">
        <p>{t('contact.never_share')}</p>
        <p>
          {t('contact.questions', {
            phone: view.data?.bank_helpline ?? '1800-XXX-XXXX (fictional)',
          })}
        </p>
      </footer>
      {pending && (
        <div
          className="fixed inset-0 z-40 flex items-end bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div className="w-full space-y-4 rounded-t-[var(--radius-card)] bg-surface p-5">
            <p id="confirm-title" className="text-[22px] font-semibold">
              {t(`contact.confirm.${pending}`, { name })}
            </p>
            <Button
              size="xl"
              className="w-full"
              variant={
                pending === 'REPORT_SUSPICIOUS'
                  ? 'danger'
                  : pending === 'CONFIRM_GENUINE'
                    ? 'success'
                    : 'primary'
              }
              loading={respond.isPending}
              onClick={submit}
            >
              {t('app.confirm')}
            </Button>
            <Button
              size="xl"
              className="w-full"
              variant="secondary"
              onClick={() => setPending(null)}
            >
              {t('app.cancel')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
