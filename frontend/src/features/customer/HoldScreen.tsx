import type { CustomerTransferOut } from '../../api/types'
import { Button } from '../../components/Button'
import { useT } from '../../i18n/lang'

/** HIGH/VERY_HIGH: one generic line only; never the score or reasons (ADR-013, SECURITY T-19). */
export function HoldScreen({
  transfer,
  onCancel,
  busy,
}: {
  transfer: CustomerTransferOut
  onCancel: () => void
  busy?: boolean
}) {
  const t = useT()
  const asked = transfer.contact_asked
  return (
    <section className="space-y-5 p-5" aria-labelledby="hold-title" aria-live="polite">
      <span aria-hidden="true" className="text-5xl text-primary">
        ⏸
      </span>
      <h2 id="hold-title" className="text-[28px] font-bold leading-tight">
        {t('hold.title')}
      </h2>
      <p className="text-[18px]">{t('hold.generic_reason')}</p>
      <p className="text-[18px] font-semibold">
        {asked && transfer.hold_status === 'AWAITING_CONTACT'
          ? t('hold.contact_asked', { name: asked.display_name, relationship: asked.relationship })
          : t('hold.officer')}
      </p>
      <p className="text-[18px] text-text-muted">{t('hold.next')}</p>
      <div className="flex flex-col gap-3">
        <a
          href="tel:1930"
          className="flex min-h-14 items-center justify-center rounded-[var(--radius-control)] bg-primary px-4 text-lg font-bold text-white"
        >
          {t('warn.call_1930')}
        </a>
        <Button size="xl" variant="secondary" onClick={onCancel} loading={busy}>
          {t('decision.cancel')}
        </Button>
      </div>
    </section>
  )
}
