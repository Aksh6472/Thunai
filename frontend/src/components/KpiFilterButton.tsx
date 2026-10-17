import { Icon, type IconName } from './Icon'

type Tone = 'very-high' | 'high' | 'medium' | 'primary'

const TILE: Record<Tone, string> = {
  'very-high': 'bg-tier-very-high/10 text-tier-very-high',
  high: 'bg-tier-high/10 text-tier-high',
  medium: 'bg-tier-medium/10 text-tier-medium',
  primary: 'bg-lilac text-primary',
}

/** Stat card that doubles as a queue filter: pastel icon tile, label, number, note. */
export function KpiFilterButton({
  label,
  count,
  active,
  onClick,
  tone = 'primary',
  icon,
  note,
}: {
  label: string
  count: number
  active: boolean
  onClick: () => void
  tone?: Tone
  icon?: IconName
  note?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`flex items-center gap-4 rounded-[var(--radius-card)] border bg-surface p-5 text-left shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 ${active ? 'border-primary ring-4 ring-primary/15' : 'border-transparent'}`}
    >
      {icon && (
        <span className={`grid h-14 w-14 shrink-0 place-items-center rounded-[16px] ${TILE[tone]}`}>
          <Icon name={icon} className="h-6 w-6" />
        </span>
      )}
      <span className="flex min-w-0 flex-col">
        <span className="text-sm text-text-muted">{label}</span>
        <span className="text-3xl font-bold leading-tight tabular-nums">{count}</span>
        {note && <span className="text-xs text-text-muted">{note}</span>}
      </span>
    </button>
  )
}
