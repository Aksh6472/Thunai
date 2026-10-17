import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Reason } from '../api/types'
import { LangProvider } from '../i18n/lang'
import { ReasonList } from './ReasonList'
import { sortReasons } from './reasons'
import { TierBadge } from './TierBadge'

const reason = (code: string, points: number, extra: Partial<Reason> = {}): Reason => ({
  code,
  points,
  stage: null,
  evidence: {},
  text_en: `${code} text`,
  text_ta: `${code} தமிழ்`,
  ...extra,
})

describe('ReasonList', () => {
  const reasons = [
    reason('BALANCE_DRAIN', 5),
    reason('ESTABLISHED_PAYEE', -25),
    reason('NEW_PAYEE', 20, { stage: 'S3' }),
    reason('BASELINE_LOW_CONFIDENCE', 0),
    reason('FRI_RISK', 20, { evidence: { source: 'SIMULATED' } }),
  ]

  it('sorts by points with risk reducers after positive reasons', () => {
    expect(sortReasons(reasons).map((r) => r.code)).toEqual([
      'FRI_RISK',
      'NEW_PAYEE',
      'BALANCE_DRAIN',
      'ESTABLISHED_PAYEE',
      'BASELINE_LOW_CONFIDENCE',
    ])
  })

  it('styles negative points as reducing risk and tags simulated signals', () => {
    render(<ReasonList reasons={reasons} />)
    const rows = screen.getAllByTestId('reason')
    expect(rows[0]).toHaveTextContent('+20')
    expect(within(rows[0]).getByText('SIMULATED')).toBeInTheDocument()
    expect(within(rows[1]).getByText('S3')).toBeInTheDocument()
    expect(rows[3]).toHaveTextContent('-25')
    expect(within(rows[3]).getByText('(reduces risk)')).toBeInTheDocument()
  })

  it('shows Tamil text with a lang attribute', () => {
    render(<ReasonList reasons={[reason('NEW_PAYEE', 20)]} lang="ta" />)
    expect(screen.getByText('NEW_PAYEE தமிழ்')).toHaveAttribute('lang', 'ta')
  })
})

describe('TierBadge', () => {
  it('always has a text label, never colour alone', () => {
    render(<TierBadge tier="VERY_HIGH" />)
    expect(screen.getByText('Hold — urgent')).toBeInTheDocument()
  })

  it('translates the label', () => {
    render(
      <LangProvider initial="ta">
        <TierBadge tier="MEDIUM" />
      </LangProvider>,
    )
    expect(screen.getByText('எச்சரிக்கை')).toBeInTheDocument()
  })
})
