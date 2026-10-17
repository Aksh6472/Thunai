import type { ContactResponse } from '../api/types'
import { useT } from '../i18n/lang'
import { hasKey } from '../i18n/t'

const STYLE: Record<string, string> = {
  AWAITING_CONTACT: 'border-tier-medium text-tier-medium',
  AWAITING_OFFICER: 'border-tier-very-high text-tier-very-high',
  RELEASED: 'border-success text-success',
  CANCELLED: 'border-text-muted text-text-muted',
  WARNED: 'border-tier-medium text-tier-medium',
  WATCHLIST: 'border-tier-medium text-tier-medium',
}

export function HoldStatusChip({
  status,
  contactResponse,
}: {
  status: string
  contactResponse?: ContactResponse | null
}) {
  const t = useT()
  const key = `status.${status}`
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <span
        className={`rounded border px-1.5 text-xs font-semibold ${STYLE[status] ?? 'border-border'}`}
      >
        {hasKey(key) ? t(key) : status}
      </span>
      {contactResponse && (
        <span className="rounded border border-border px-1.5 text-xs">
          {t(`response.${contactResponse}`)}
        </span>
      )}
    </span>
  )
}
