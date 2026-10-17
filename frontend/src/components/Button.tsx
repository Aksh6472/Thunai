import type { ButtonHTMLAttributes, Ref } from 'react'

import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'success'
type Size = 'sm' | 'md' | 'lg' | 'xl'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:opacity-90',
  secondary: 'border border-border bg-surface text-text hover:bg-bg',
  danger: 'bg-tier-very-high text-white hover:opacity-90',
  success: 'bg-success text-white hover:opacity-90',
  ghost: 'text-primary underline-offset-2 hover:underline',
}
const SIZES: Record<Size, string> = {
  sm: 'min-h-9 px-3 text-sm',
  md: 'min-h-11 px-4 text-base',
  lg: 'min-h-12 px-5 text-lg',
  xl: 'min-h-14 px-6 text-lg', // customer and contact pages: ≥ 56 px targets
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  ref?: Ref<HTMLButtonElement>
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </button>
  )
}
