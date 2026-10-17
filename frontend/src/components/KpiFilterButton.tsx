export function KpiFilterButton({
  label,
  count,
  active,
  onClick,
}: {
  label: string
  count: number
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`flex min-h-16 min-w-36 flex-col items-start rounded-[var(--radius-card)] border px-4 py-2 text-left ${active ? 'border-primary bg-primary/10' : 'border-border bg-surface'}`}
    >
      <span className="text-2xl font-bold tabular-nums">{count}</span>
      <span className="text-sm text-text-muted">{label}</span>
    </button>
  )
}
