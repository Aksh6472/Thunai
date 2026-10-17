import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { WarningScreen } from './WarningScreen'

describe('WarningScreen (FR-10)', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('puts 1930 first as a real tel: link', () => {
    render(<WarningScreen onCancel={() => undefined} onContinue={() => undefined} />)
    expect(screen.getByRole('link', { name: /Call 1930/ })).toHaveAttribute('href', 'tel:1930')
    expect(screen.getByText(/no "digital arrest" in Indian law/)).toBeInTheDocument()
  })

  it('enables continue only after a 3 second read delay', () => {
    const onContinue = vi.fn()
    render(<WarningScreen onCancel={() => undefined} onContinue={onContinue} />)
    const button = screen.getByRole('button', { name: /I understand, continue \(3\)/ })
    expect(button).toBeDisabled()
    act(() => vi.advanceTimersByTime(1000))
    expect(screen.getByRole('button', { name: /continue \(2\)/ })).toBeDisabled()
    act(() => vi.advanceTimersByTime(1000))
    act(() => vi.advanceTimersByTime(1000))
    const ready = screen.getByRole('button', { name: 'I understand, continue' })
    expect(ready).toBeEnabled()
    fireEvent.click(ready)
    expect(onContinue).toHaveBeenCalledOnce()
  })

  it('cancel works immediately', () => {
    const onCancel = vi.fn()
    render(<WarningScreen onCancel={onCancel} onContinue={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel this transfer' }))
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
