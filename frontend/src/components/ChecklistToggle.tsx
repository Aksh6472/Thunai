export function ChecklistToggle({
  label,
  pressed,
  hotkey,
  disabled,
  onToggle,
}: {
  label: string
  pressed: boolean
  hotkey: number
  disabled?: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      aria-keyshortcuts={String(hotkey)}
      disabled={disabled}
      onClick={onToggle}
      className={`flex min-h-14 items-center gap-3 rounded-[var(--radius-control)] border-2 px-3 text-left font-semibold disabled:opacity-50 ${pressed ? 'border-tier-very-high bg-tier-very-high/10 text-tier-very-high' : 'border-border bg-surface'}`}
    >
      <kbd className="rounded border border-border bg-bg px-1.5 font-mono text-xs text-text">
        {hotkey}
      </kbd>
      <span>{label}</span>
      <span aria-hidden="true" className="ml-auto">
        {pressed ? '✓' : ''}
      </span>
    </button>
  )
}
