import { useId, type ReactNode } from 'react'

export function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string
  error?: string | null
  hint?: ReactNode
  children: (props: { id: string; describedBy?: string; invalid: boolean }) => ReactNode
}) {
  const id = useId()
  const errorId = `${id}-error`
  const hintId = `${id}-hint`
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint && (
        <p id={hintId} className="text-xs text-text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-tier-very-high">
          {error}
        </p>
      )}
    </div>
  )
}

export const inputClass =
  'min-h-11 w-full rounded-[var(--radius-control)] border border-border bg-surface px-3 text-base text-text aria-[invalid=true]:border-tier-very-high'
