import { useState } from 'react'

import type { CustomerOverview, CustomerTransferIn } from '../../api/types'
import { Button } from '../../components/Button'
import { Field, inputClass } from '../../components/Field'
import { useT } from '../../i18n/lang'
import { formatINR, groupRupees, parseRupees } from '../../lib/format'

type Rail = CustomerTransferIn['rail']
const RAILS: Rail[] = ['IMPS', 'NEFT', 'RTGS', 'UPI']

export function newTransferRef(): string {
  return `APP-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`.toUpperCase()
}

export function SendMoney({
  overview,
  onSubmit,
  busy,
  serverError,
  onBack,
}: {
  overview: CustomerOverview
  onSubmit: (body: CustomerTransferIn) => void
  busy: boolean
  serverError: string | null
  onBack: () => void
}) {
  const t = useT()
  const accounts = overview.accounts.filter(
    (a) => (a.account_type === 'SAVINGS' || a.account_type === 'CURRENT') && a.status === 'ACTIVE',
  )
  const [from, setFrom] = useState(accounts[0]?.masked_number ?? '')
  const [payee, setPayee] = useState('')
  const [amount, setAmount] = useState('')
  const [rail, setRail] = useState<Rail>('IMPS')
  const [errors, setErrors] = useState<{ payee?: string; amount?: string }>({})
  const balance = accounts.find((a) => a.masked_number === from)?.balance_paise ?? 0

  function validate(): number | null {
    const next: typeof errors = {}
    const rupees = parseRupees(amount)
    if (!payee) next.payee = t('cust.err.payee')
    if (rupees === null) next.amount = t('cust.err.amount')
    else if (rupees * 100 > balance) next.amount = t('cust.err.balance')
    setErrors(next)
    return Object.keys(next).length ? null : rupees
  }

  return (
    <form
      className="space-y-4 p-5"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        const rupees = validate()
        if (rupees !== null)
          onSubmit({
            transfer_ref: newTransferRef(),
            from_account: from,
            payee_ref: payee,
            amount_paise: rupees * 100,
            rail,
          })
      }}
    >
      <h2 className="text-[22px] font-bold">{t('cust.send')}</h2>
      <Field label={t('cust.from')}>
        {(p) => (
          <select
            id={p.id}
            className={inputClass}
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          >
            {accounts.map((a) => (
              <option key={a.masked_number} value={a.masked_number}>
                {a.masked_number} · {formatINR(a.balance_paise)}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field label={t('cust.payee')} error={errors.payee}>
        {(p) => (
          <select
            id={p.id}
            aria-invalid={p.invalid}
            aria-describedby={p.describedBy}
            className={inputClass}
            value={payee}
            onChange={(e) => setPayee(e.target.value)}
          >
            <option value="">{t('cust.payee_select')}</option>
            {overview.payees.map((py) => (
              <option key={py.payee_ref} value={py.payee_ref}>
                {py.display_name} · {py.masked_account}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field label={t('cust.amount')} error={errors.amount}>
        {(p) => (
          <input
            id={p.id}
            inputMode="numeric"
            autoComplete="off"
            aria-invalid={p.invalid}
            aria-describedby={p.describedBy}
            className={`${inputClass} text-[22px] tabular-nums`}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            onBlur={() => {
              const rupees = parseRupees(amount)
              if (rupees !== null) setAmount(groupRupees(rupees))
              validate()
            }}
          />
        )}
      </Field>
      <Field label={t('cust.rail')}>
        {(p) => (
          <select
            id={p.id}
            className={inputClass}
            value={rail}
            onChange={(e) => setRail(e.target.value as Rail)}
          >
            {RAILS.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        )}
      </Field>
      {serverError && (
        <p role="alert" className="text-base text-tier-very-high">
          {serverError}
        </p>
      )}
      <div className="flex flex-col gap-3">
        <Button type="submit" size="xl" loading={busy}>
          {busy ? t('cust.sending') : t('cust.continue')}
        </Button>
        <Button size="xl" variant="ghost" onClick={onBack}>
          {t('app.back')}
        </Button>
      </div>
    </form>
  )
}
