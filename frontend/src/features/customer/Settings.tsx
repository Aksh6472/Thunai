import { useState } from 'react'

import { ApiError } from '../../api/client'
import { useConsent, useRegisterContact } from '../../api/hooks/customer'
import type { CustomerOverview, Lang } from '../../api/types'
import { Button } from '../../components/Button'
import { Field, inputClass } from '../../components/Field'
import { useToast } from '../../components/Toast'
import { useT } from '../../i18n/lang'
import { formatIST } from '../../lib/format'

const E164 = /^\+[1-9]\d{7,14}$/

/** FR-23 consents and FR-24 trusted contact (72 h activation delay). */
export function Settings({ overview, onBack }: { overview: CustomerOverview; onBack: () => void }) {
  const t = useT()
  const toast = useToast()
  const consent = useConsent()
  const register = useRegisterContact()
  const [name, setName] = useState('')
  const [relationship, setRelationship] = useState('')
  const [phone, setPhone] = useState('')
  const [lang, setLang] = useState<Lang>('ta')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const contact = overview.trusted_contact

  function toggle(type: 'CALL_SIGNAL' | 'TRUSTED_CONTACT_SHARING', granted: boolean) {
    consent.mutate(
      {
        consent_type: type,
        granted,
        text_version: type === 'CALL_SIGNAL' ? 'call_signal_v1' : 'trusted_contact_sharing_v1',
      },
      {
        onSuccess: () => toast(t('consent.saved')),
        onError: () => toast(t('app.error_generic'), 'error'),
      },
    )
  }

  async function save() {
    const next: Record<string, string> = {}
    if (!name.trim()) next.name = t('tc.err.required')
    if (!relationship.trim()) next.relationship = t('tc.err.required')
    if (!E164.test(phone.trim())) next.phone = t('tc.err.phone')
    setErrors(next)
    if (Object.keys(next).length) return
    try {
      const out = await register.mutateAsync({
        display_name: name.trim(),
        relationship: relationship.trim(),
        phone_e164: phone.trim(),
        preferred_language: lang,
      })
      toast(t('tc.active_from', { time: formatIST(out.effective_from) }))
      setName('')
      setRelationship('')
      setPhone('')
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setErrors({ phone: t('tc.err.phone') })
      else toast(t('app.error_generic'), 'error')
    }
  }

  return (
    <section className="space-y-5 p-5">
      <h2 className="text-[22px] font-bold">{t('consent.title')}</h2>
      {(['CALL_SIGNAL', 'TRUSTED_CONTACT_SHARING'] as const).map((type) => {
        const on = Boolean(overview.consents[type])
        const key = type === 'CALL_SIGNAL' ? 'call' : 'contact'
        return (
          <div key={type} className="rounded border border-border p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="font-semibold">{t(`consent.${key}.title`)}</p>
              <button
                type="button"
                role="switch"
                aria-checked={on}
                onClick={() => toggle(type, !on)}
                className={`min-h-11 min-w-20 rounded-full px-3 font-semibold ${on ? 'bg-success text-white' : 'bg-border text-text'}`}
              >
                {on ? t('consent.on') : t('consent.off')}
              </button>
            </div>
            <p className="mt-1 text-base text-text-muted">{t(`consent.${key}.text`)}</p>
          </div>
        )
      })}
      <div className="space-y-3 rounded border border-border p-3">
        <h3 className="font-semibold">{t('tc.title')}</h3>
        {contact && (
          <p className="text-base">
            {t('tc.current', {
              name: contact.display_name,
              relationship: contact.relationship,
              last4: contact.phone_last4,
            })}{' '}
            ·{' '}
            {contact.status === 'ACTIVE'
              ? t('tc.active')
              : t('tc.active_from', { time: formatIST(contact.effective_from) })}
          </p>
        )}
        <p className="text-sm text-text-muted">{t('tc.delay_note')}</p>
        <Field label={t('tc.name')} error={errors.name}>
          {(p) => (
            <input
              id={p.id}
              aria-invalid={p.invalid}
              aria-describedby={p.describedBy}
              className={inputClass}
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('tc.relationship')} error={errors.relationship}>
          {(p) => (
            <input
              id={p.id}
              aria-invalid={p.invalid}
              aria-describedby={p.describedBy}
              className={inputClass}
              value={relationship}
              maxLength={40}
              onChange={(e) => setRelationship(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('tc.phone')} error={errors.phone}>
          {(p) => (
            <input
              id={p.id}
              type="tel"
              placeholder="+91…"
              aria-invalid={p.invalid}
              aria-describedby={p.describedBy}
              className={inputClass}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('tc.language')}>
          {(p) => (
            <select
              id={p.id}
              className={inputClass}
              value={lang}
              onChange={(e) => setLang(e.target.value as Lang)}
            >
              <option value="ta">{t('lang.ta')}</option>
              <option value="en">{t('lang.en')}</option>
            </select>
          )}
        </Field>
        <Button size="xl" onClick={save} loading={register.isPending}>
          {t('tc.save')}
        </Button>
      </div>
      <Button size="xl" variant="ghost" onClick={onBack}>
        {t('app.back')}
      </Button>
    </section>
  )
}
