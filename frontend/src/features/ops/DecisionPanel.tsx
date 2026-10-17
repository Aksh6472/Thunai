import { useState } from 'react'

import { ApiError } from '../../api/client'
import { useOfficerDecision, useResendContact } from '../../api/hooks/ops'
import type { HoldDetail, OfficerDecisionIn } from '../../api/types'
import { Button } from '../../components/Button'
import { Dialog } from '../../components/Dialog'
import { inputClass } from '../../components/Field'
import { useToast } from '../../components/Toast'
import { useT } from '../../i18n/lang'
import { formatINR, formatIST } from '../../lib/format'

type Decision = OfficerDecisionIn['decision']
const NOTE_MIN = 10
const NOTE_MAX = 1000

export function DecisionPanel({
  hold,
  canDecide,
  canResend,
}: {
  hold: HoldDetail
  canDecide: boolean
  canResend: boolean
}) {
  const t = useT()
  const toast = useToast()
  const decide = useOfficerDecision(hold.id)
  const resend = useResendContact(hold.id)
  const [note, setNote] = useState('')
  const [pending, setPending] = useState<Decision | null>(null)
  const resolved = hold.status === 'RELEASED' || hold.status === 'CANCELLED'
  const noteValid = note.trim().length >= NOTE_MIN && note.length <= NOTE_MAX
  const amount = formatINR(hold.transfer.amount_paise)

  async function confirm() {
    if (!pending) return
    try {
      await decide.mutateAsync({ decision: pending, note: note.trim() })
      toast(t(`decision.done.${pending}`))
      setPending(null)
      setNote('')
    } catch (e) {
      setPending(null)
      toast(e instanceof ApiError ? e.message : t('app.error_generic'), 'error')
    }
  }

  return (
    <div className="space-y-4">
      <ContactStatus hold={hold} />
      {canResend && !resolved && hold.trusted_contact?.active && (
        <Button
          size="sm"
          variant="secondary"
          loading={resend.isPending}
          onClick={() =>
            resend.mutate(undefined, {
              onSuccess: () => toast(t('decision.resent')),
              onError: (e) =>
                toast(e instanceof ApiError ? e.message : t('app.error_generic'), 'error'),
            })
          }
        >
          {t('decision.resend')}
        </Button>
      )}
      {resolved ? (
        <p className="rounded bg-bg p-3 text-sm" role="status">
          {t('decision.resolved', {
            status: t(`status.${hold.status}`),
            by: hold.resolved_by_type ? t(`decision.by.${hold.resolved_by_type as 'OFFICER'}`) : '',
            time: hold.resolved_at ? formatIST(hold.resolved_at) : '',
          })}
          {hold.resolution_note && (
            <span className="mt-1 block text-text-muted">“{hold.resolution_note}”</span>
          )}
        </p>
      ) : canDecide ? (
        <div className="space-y-3">
          <label className="block text-sm font-semibold" htmlFor="officer-note">
            {t('decision.note')}
          </label>
          <textarea
            id="officer-note"
            value={note}
            maxLength={NOTE_MAX}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            aria-describedby="officer-note-count"
            className={`${inputClass} py-2`}
          />
          <p id="officer-note-count" className="text-right text-xs text-text-muted">
            {t('decision.note_count', { n: note.length })}
          </p>
          <div className="flex flex-col gap-2">
            <Button
              variant="danger"
              disabled={!noteValid}
              onClick={() => setPending('CANCEL_TRANSFER')}
            >
              {t('decision.cancel')}
            </Button>
            <Button variant="secondary" disabled={!noteValid} onClick={() => setPending('RELEASE')}>
              {t('decision.release')}
            </Button>
            <Button
              variant="ghost"
              disabled={!noteValid}
              onClick={() => setPending('KEEP_HOLDING')}
            >
              {t('decision.keep')}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-text-muted">{t('decision.officer_only')}</p>
      )}
      <Dialog
        open={pending !== null}
        title={pending ? t(`decision.confirm.${pending}`, { amount }) : ''}
        confirmLabel={
          pending === 'CANCEL_TRANSFER'
            ? t('decision.cancel')
            : pending === 'RELEASE'
              ? t('decision.release')
              : t('decision.keep')
        }
        confirmVariant={pending === 'CANCEL_TRANSFER' ? 'danger' : 'primary'}
        onConfirm={confirm}
        onClose={() => setPending(null)}
        busy={decide.isPending}
      >
        “{note.trim()}”
      </Dialog>
    </div>
  )
}

function ContactStatus({ hold }: { hold: HoldDetail }) {
  const t = useT()
  const contact = hold.trusted_contact
  const latest = hold.contact_requests[hold.contact_requests.length - 1]
  return (
    <div className="rounded border border-border p-3 text-sm">
      <p className="text-xs font-semibold uppercase text-text-muted">{t('decision.contact')}</p>
      {!contact ? (
        <p>{t('decision.contact_none')}</p>
      ) : (
        <>
          <p className="font-semibold">
            {contact.display_name} ({contact.relationship}) · …{contact.phone_last4}
          </p>
          {!contact.active && (
            <p className="text-tier-medium">
              {t('decision.contact_pending', { time: formatIST(contact.effective_from) })}
            </p>
          )}
        </>
      )}
      {latest && (
        <ul className="mt-2 space-y-1">
          <li>
            ●{' '}
            {latest.delivery_status === 'FAILED'
              ? t('decision.delivery.FAILED', { error: latest.delivery_error ?? '' })
              : latest.delivery_status === 'SENT'
                ? t('decision.delivery.SENT', { time: formatIST(latest.sent_at) })
                : t('decision.delivery.QUEUED')}
          </li>
          {latest.opened_at && (
            <li>● {t('decision.opened', { time: formatIST(latest.opened_at) })}</li>
          )}
          <li>
            ●{' '}
            {hold.contact_response
              ? t('decision.response', {
                  response: t(`response.${hold.contact_response}`),
                  time: latest.responded_at ? formatIST(latest.responded_at) : '',
                })
              : t('decision.no_response')}
          </li>
        </ul>
      )}
    </div>
  )
}
