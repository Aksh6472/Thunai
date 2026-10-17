import { useState } from 'react'

import { ApiError } from '../../api/client'
import { useCreateReport, useMarkFiled, usePatchReport, useReport } from '../../api/hooks/reports'
import type { ReportOut } from '../../api/types'
import { Button } from '../../components/Button'
import { Field, inputClass } from '../../components/Field'
import { useToast } from '../../components/Toast'
import { useT } from '../../i18n/lang'
import { formatINR, formatIST } from '../../lib/format'

const ACK = /^[A-Za-z0-9/-]{1,64}$/

export function ReportSection({
  holdId,
  reportId,
  canFile,
}: {
  holdId: string
  reportId: string | null
  canFile: boolean
}) {
  const t = useT()
  const toast = useToast()
  const create = useCreateReport(holdId)
  const report = useReport(reportId ?? create.data?.id)
  const data = report.data ?? create.data
  if (!data) {
    return (
      <Button
        loading={create.isPending}
        onClick={() =>
          create.mutate(undefined, { onError: () => toast(t('app.error_generic'), 'error') })
        }
      >
        {t('report.generate')}
      </Button>
    )
  }
  // Remount when the saved report changes, so the form shows the stored values.
  return <ReportDraft key={data.updated_at} report={data} canFile={canFile} />
}

export function ReportDraft({ report, canFile }: { report: ReportOut; canFile: boolean }) {
  const t = useT()
  const toast = useToast()
  const patch = usePatchReport(report.id)
  const markFiled = useMarkFiled(report.id)
  const reported = report.customer_reported as {
    claimed_agency?: string
    platform?: string
    scammer_numbers_given_by_customer?: string[]
  }
  const [agency, setAgency] = useState(reported.claimed_agency ?? '')
  const [platform, setPlatform] = useState(reported.platform ?? '')
  const [numbers, setNumbers] = useState(
    (reported.scammer_numbers_given_by_customer ?? []).join(', '),
  )
  const [narrative, setNarrative] = useState(report.narrative_text)
  const [ack, setAck] = useState('')
  const [ackError, setAckError] = useState<string | null>(null)
  const filed = report.status === 'FILED_EXTERNALLY'
  const fields = report.structured_fields as {
    incident_category: string
    transaction: Record<string, string | number>
    timeline: { at: string; what: string }[]
    helpline: string
    portal: string
  }
  const tx = fields.transaction

  async function save(status?: 'READY') {
    const numberList = numbers
      .split(',')
      .map((n) => n.trim())
      .filter(Boolean)
    try {
      await patch.mutateAsync({
        customer_reported: {
          claimed_agency: agency || null,
          platform: platform || null,
          scammer_numbers_given_by_customer: numberList,
        },
        ...(narrative !== report.narrative_text ? { narrative_text: narrative } : {}),
        ...(status ? { status } : {}),
      })
      toast(t('report.saved'))
    } catch (e) {
      toast(e instanceof ApiError ? e.message : t('app.error_generic'), 'error')
    }
  }

  async function file() {
    if (!ACK.test(ack)) {
      setAckError(t('report.ack_invalid'))
      return
    }
    setAckError(null)
    try {
      await markFiled.mutateAsync(ack)
      toast(t('report.filed'))
    } catch (e) {
      toast(e instanceof ApiError ? e.message : t('app.error_generic'), 'error')
    }
  }

  const copyText = [
    fields.incident_category,
    `${t('report.field.amount')}: ${formatINR(Number(tx.amount_paise))} (${tx.rail})`,
    `${t('report.field.initiated')}: ${formatIST(String(tx.initiated_at))}`,
    `${t('report.field.status')}: ${tx.status}`,
    `${t('report.field.from')}: ${tx.from_account_masked}`,
    `${t('report.field.bank')}: ${tx.beneficiary_bank} (${tx.beneficiary_ifsc})`,
    `${t('report.field.beneficiary')}: ${tx.beneficiary_account_masked}`,
    ...fields.timeline.map((e) => `${formatIST(e.at)}: ${e.what}`),
    '',
    narrative,
  ].join('\n')

  return (
    <div className="space-y-4 text-sm">
      <p className="text-text-muted">
        {t('report.status', {
          status: t(`report.status.${report.status}`),
          source: t(`report.source.${report.narrative_source}`),
        })}
      </p>
      <div>
        <p className="mb-1 text-xs font-semibold uppercase text-text-muted">{t('report.fields')}</p>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <dt className="text-text-muted">{t('report.field.category')}</dt>
          <dd>{fields.incident_category}</dd>
          <dt className="text-text-muted">{t('report.field.amount')}</dt>
          <dd className="font-semibold">
            {formatINR(Number(tx.amount_paise))} · {String(tx.rail)}
          </dd>
          <dt className="text-text-muted">{t('report.field.initiated')}</dt>
          <dd>{formatIST(String(tx.initiated_at))}</dd>
          <dt className="text-text-muted">{t('report.field.status')}</dt>
          <dd>{String(tx.status)}</dd>
          <dt className="text-text-muted">{t('report.field.from')}</dt>
          <dd>{String(tx.from_account_masked)}</dd>
          <dt className="text-text-muted">{t('report.field.bank')}</dt>
          <dd>{String(tx.beneficiary_bank)}</dd>
          <dt className="text-text-muted">{t('report.field.ifsc')}</dt>
          <dd>{String(tx.beneficiary_ifsc)}</dd>
          <dt className="text-text-muted">{t('report.field.beneficiary')}</dt>
          <dd>{String(tx.beneficiary_account_masked)}</dd>
          <dt className="text-text-muted">{t('report.field.helpline')}</dt>
          <dd>
            <a className="font-bold text-primary underline" href={`tel:${fields.helpline}`}>
              {fields.helpline}
            </a>
          </dd>
          <dt className="text-text-muted">{t('report.field.portal')}</dt>
          <dd>
            <a
              className="text-primary underline"
              href={fields.portal}
              target="_blank"
              rel="noreferrer"
            >
              {fields.portal}
            </a>
          </dd>
        </dl>
        {fields.timeline.length > 0 && (
          <>
            <p className="mb-1 mt-3 text-xs font-semibold uppercase text-text-muted">
              {t('report.timeline')}
            </p>
            <ul className="list-disc pl-5">
              {fields.timeline.map((e) => (
                <li key={e.at + e.what}>
                  {formatIST(e.at)}: {e.what}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
      <fieldset disabled={filed} className="space-y-2">
        <legend className="text-xs font-semibold uppercase text-text-muted">
          {t('report.reported')}
        </legend>
        <Field label={t('report.claimed_agency')}>
          {(p) => (
            <input
              id={p.id}
              className={inputClass}
              value={agency}
              maxLength={64}
              onChange={(e) => setAgency(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('report.platform')}>
          {(p) => (
            <input
              id={p.id}
              className={inputClass}
              value={platform}
              maxLength={64}
              onChange={(e) => setPlatform(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('report.numbers')}>
          {(p) => (
            <input
              id={p.id}
              className={inputClass}
              value={numbers}
              onChange={(e) => setNumbers(e.target.value)}
            />
          )}
        </Field>
        <Field label={t('report.narrative')}>
          {(p) => (
            <textarea
              id={p.id}
              className={`${inputClass} py-2`}
              rows={7}
              maxLength={4000}
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
            />
          )}
        </Field>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" loading={patch.isPending} onClick={() => save()}>
            {t('report.save')}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => save('READY')}>
            {t('report.mark_ready')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              void navigator.clipboard?.writeText(copyText).then(() => toast(t('app.copied')))
            }
          >
            {t('report.copy')}
          </Button>
        </div>
      </fieldset>
      {canFile && !filed && (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Field label={t('report.ack')} error={ackError}>
              {(p) => (
                <input
                  id={p.id}
                  aria-describedby={p.describedBy}
                  aria-invalid={p.invalid}
                  className={inputClass}
                  value={ack}
                  maxLength={64}
                  onChange={(e) => setAck(e.target.value)}
                />
              )}
            </Field>
          </div>
          <Button size="sm" variant="secondary" loading={markFiled.isPending} onClick={file}>
            {t('report.mark_filed')}
          </Button>
        </div>
      )}
      {filed && (
        <p className="font-semibold text-success">
          {t('report.status.FILED_EXTERNALLY')}: {report.acknowledgement_number}
        </p>
      )}
      <p className="text-xs text-text-muted">{report.disclaimer}</p>
    </div>
  )
}
