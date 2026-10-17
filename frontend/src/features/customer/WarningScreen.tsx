import { useEffect, useState } from 'react'

import { Button } from '../../components/Button'
import { useT } from '../../i18n/lang'

export const READ_DELAY_SECONDS = 3

/** MEDIUM: bilingual warning, 1930 first, deliberate 3 s read delay on "continue" (FR-10). */
export function WarningScreen({
  onCancel,
  onContinue,
  busy,
}: {
  onCancel: () => void
  onContinue: () => void
  busy?: boolean
}) {
  const t = useT()
  const [left, setLeft] = useState(READ_DELAY_SECONDS)
  useEffect(() => {
    if (left <= 0) return
    const id = setTimeout(() => setLeft((s) => s - 1), 1000)
    return () => clearTimeout(id)
  }, [left])
  return (
    <section className="space-y-5 p-5" aria-labelledby="warn-title">
      <span aria-hidden="true" className="text-5xl text-tier-medium">
        ▲
      </span>
      <h2 id="warn-title" className="text-[28px] font-bold leading-tight">
        {t('warn.title')}
      </h2>
      <p className="text-[18px] leading-relaxed">{t('warn.no_digital_arrest')}</p>
      <div className="flex flex-col gap-3">
        <a
          href="tel:1930"
          className="flex min-h-14 items-center justify-center rounded-[var(--radius-control)] bg-primary px-4 text-lg font-bold text-white"
        >
          {t('warn.call_1930')}
        </a>
        <Button size="xl" variant="secondary" onClick={onCancel} disabled={busy}>
          {t('warn.cancel')}
        </Button>
        <Button size="xl" variant="ghost" onClick={onContinue} disabled={left > 0 || busy}>
          {left > 0 ? t('warn.continue_in', { s: left }) : t('warn.continue')}
        </Button>
      </div>
    </section>
  )
}
