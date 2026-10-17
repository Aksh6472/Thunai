import type { ReactNode } from 'react'

import { useT } from '../i18n/lang'
import { Button } from './Button'

export function EmptyState({
  title,
  detail,
  icon = '✓',
}: {
  title: string
  detail?: string
  icon?: string
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <span
        aria-hidden="true"
        className="grid h-14 w-14 place-items-center rounded-full bg-primary/10 text-2xl text-primary"
      >
        {icon}
      </span>
      <p className="font-semibold">{title}</p>
      {detail && <p className="text-sm text-text-muted">{detail}</p>}
    </div>
  )
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const t = useT()
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-tier-very-high/40 bg-tier-very-high/10 px-4 py-2 text-sm text-tier-very-high"
    >
      <span>{message}</span>
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          {t('app.retry')}
        </Button>
      )}
    </div>
  )
}

export function Skeleton({ className = 'h-4 w-full' }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded bg-border ${className}`} />
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  const t = useT()
  return (
    <div role="status" aria-label={t('app.loading')} className="space-y-3 p-4">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}

export function Card({
  title,
  actions,
  children,
  className = '',
}: {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={`rounded-[var(--radius-card)] border border-border bg-surface shadow-[var(--shadow-card)] ${className}`}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2 border-b border-border px-5 py-3">
          {title && (
            <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em] text-text-muted before:h-3.5 before:w-1 before:rounded-full before:bg-primary before:content-['']">
              {title}
            </h2>
          )}
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}
