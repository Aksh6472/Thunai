import type { ReactNode } from 'react'

type Tone = 'very-high' | 'high' | 'medium' | 'primary'

const TONE: Record<Tone, { bar: string; icon: string }> = {
  'very-high': { bar: 'bg-tier-very-high', icon: 'bg-tier-very-high/10 text-tier-very-high' },
  high: { bar: 'bg-tier-high', icon: 'bg-tier-high/10 text-tier-high' },
  medium: { bar: 'bg-tier-medium', icon: 'bg-tier-medium/10 text-tier-medium' },
  primary: { bar: 'bg-primary', icon: 'bg-primary/10 text-primary' },
}

export function KpiFilterButton({
  label,
  count,
  active,
  onClick,
  tone = 'primary',
  icon,
}: {
  label: string
  count: number
  active: boolean
  onClick: () => void
  tone?: Tone
  icon?: ReactNode
}) {
  const c = TONE[tone]
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`relative flex min-h-20 items-center gap-3 overflow-hidden rounded-[var(--radius-card)] border bg-surface px-4 py-3 text-left shadow-[var(--shadow-card)] transition hover:-translate-y-px ${active ? 'border-primary ring-2 ring-primary/30' : 'border-border'}`}
    >
      <span aria-hidden="true" className={`absolute inset-y-0 left-0 w-1 ${c.bar}`} />
      {icon && (
        <span
          aria-hidden="true"
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-full text-lg ${c.icon}`}
        >
          {icon}
        </span>
      )}
      <span className="flex flex-col">
        <span className="text-3xl font-bold leading-none tabular-nums">{count}</span>
        <span className="mt-1 text-sm text-text-muted">{label}</span>
      </span>
    </button>
  )
}
