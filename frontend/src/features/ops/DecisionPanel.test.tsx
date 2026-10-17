import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { HoldDetail } from '../../api/types'
import { fakeApi, renderWith } from '../../test/utils'
import { DecisionPanel } from './DecisionPanel'

const hold = {
  id: 'h1',
  tier: 'VERY_HIGH',
  status: 'AWAITING_OFFICER',
  contact_response: 'REPORT_SUSPICIOUS',
  created_at: '2026-10-03T05:50:00Z',
  cooling_off_until: '2026-10-03T09:50:00Z',
  resolved_at: null,
  resolved_by_type: null,
  resolution_note: null,
  customer: { id: 'c1', external_ref: 'CUST-0007', display_name: 'R. Kamala (fictional)' },
  transfer: {
    transfer_ref: 'TRF-P1-0001',
    amount_paise: 460000000,
    rail: 'RTGS',
    channel: 'BRANCH',
    status: 'HELD',
    initiated_at: '2026-10-03T05:50:00Z',
    decided_at: null,
    executed_at: null,
    from_account_masked: 'XXXXXX2201',
    cancelled_reason: null,
  },
  payee: {
    payee_ref: 'P',
    display_name: 'X',
    bank_name: 'Example Bank',
    ifsc: 'EXMP0001234',
    masked_account: 'XXXXXX4821',
    linked_msisdn_last4: null,
    added_at: '2026-10-03T03:42:00Z',
  },
  assessments: [],
  episode: null,
  trusted_contact: {
    display_name: 'Arun',
    relationship: 'son',
    phone_last4: '0101',
    status: 'ACTIVE',
    effective_from: '2026-01-01T00:00:00Z',
    active: true,
  },
  contact_requests: [],
  report_id: null,
  audit: [],
} as unknown as HoldDetail

describe('DecisionPanel (T-034)', () => {
  it('keeps decision buttons disabled until the note has 10 characters', async () => {
    const api = fakeApi({ 'POST /holds/h1/officer-decision': { ...hold, status: 'CANCELLED' } })
    renderWith(<DecisionPanel hold={hold} canDecide canResend />, api)
    const cancel = screen.getByRole('button', { name: 'Cancel transfer' })
    expect(cancel).toBeDisabled()
    await userEvent.type(screen.getByLabelText(/Note \(required/), 'too short')
    expect(cancel).toBeDisabled()
    await userEvent.type(screen.getByLabelText(/Note \(required/), '!!')
    expect(cancel).toBeEnabled()
  })

  it('confirms the action and the amount before deciding', async () => {
    const api = fakeApi({ 'POST /holds/h1/officer-decision': { ...hold, status: 'CANCELLED' } })
    renderWith(<DecisionPanel hold={hold} canDecide canResend />, api)
    await userEvent.type(screen.getByLabelText(/Note \(required/), 'Customer confirmed a CBI call.')
    await userEvent.click(screen.getByRole('button', { name: 'Cancel transfer' }))
    expect(
      screen.getByRole('dialog', { name: 'Cancel the ₹46,00,000 transfer?' }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Cancel transfer' })[1])
    expect(api.calls.at(-1)).toEqual({
      method: 'POST',
      path: '/holds/h1/officer-decision',
      body: { decision: 'CANCEL_TRANSFER', note: 'Customer confirmed a CBI call.' },
    })
  })

  it('shows the contact response to the officer', () => {
    renderWith(<DecisionPanel hold={hold} canDecide canResend />, fakeApi({}))
    expect(screen.getByText(/Arun \(son\)/)).toBeInTheDocument()
  })

  it('is read-only for non-officers', () => {
    renderWith(<DecisionPanel hold={hold} canDecide={false} canResend />, fakeApi({}))
    expect(screen.queryByRole('button', { name: 'Release transfer' })).not.toBeInTheDocument()
    expect(screen.getByText('Only an officer can decide on a hold.')).toBeInTheDocument()
  })
})
