import { useEffect, useRef, type ReactNode } from 'react'

import { useT } from '../i18n/lang'
import { Button } from './Button'

interface Props {
  open: boolean
  title: string
  children?: ReactNode
  confirmLabel: string
  confirmVariant?: 'primary' | 'danger' | 'success'
  onConfirm: () => void
  onClose: () => void
  busy?: boolean
}

export function Dialog({
  open,
  title,
  children,
  confirmLabel,
  confirmVariant = 'primary',
  onConfirm,
  onClose,
  busy,
}: Props) {
  const t = useT()
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className="w-full max-w-md rounded-[var(--radius-card)] bg-surface p-5 shadow-[0_10px_30px_rgb(0_0_0/0.2)]"
      >
        <h2 id="dialog-title" className="text-lg font-semibold">
          {title}
        </h2>
        {children && <div className="mt-2 text-text-muted">{children}</div>}
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button ref={cancelRef} variant="secondary" onClick={onClose} disabled={busy}>
            {t('app.cancel')}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
