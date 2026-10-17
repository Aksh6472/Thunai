import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { fakeApi, renderRoutes, signIn } from '../../test/utils'
import { TellerConsole } from './TellerConsole'

const item = {
  id: null,
  transfer_ref: 'TRF-X',
  customer: { id: 'c1', external_ref: 'CUST-0099', display_name: 'Test (fictional)' },
  amount_paise: 30000000,
  tier: 'MEDIUM',
  status: 'WARNED',
  transfer_status: 'WARNED',
  channel: 'BRANCH',
  contact_response: null,
  top_reasons: [],
  created_at: '2026-10-03T05:50:00Z',
  cooling_off_until: null,
}

describe('TellerConsole (T-035)', () => {
  afterEach(() => signIn(null))

  it('toggles observations with keys 1–4 (aria-pressed)', async () => {
    signIn('TELLER')
    const api = fakeApi({ 'GET /teller/queue': { items: [item], next_cursor: null } })
    renderRoutes([{ path: '/teller', element: <TellerConsole /> }], '/teller', api)
    const onCall = await screen.findByRole('button', { name: /On a call now/ })
    expect(onCall).toHaveAttribute('aria-pressed', 'false')
    fireEvent.keyDown(window, { key: '1' })
    expect(onCall).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(window, { key: '4' })
    expect(screen.getByRole('button', { name: /Mentions police/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    fireEvent.keyDown(window, { key: '1' })
    expect(onCall).toHaveAttribute('aria-pressed', 'false')
  })

  it('does not toggle while typing in the customer-said box', async () => {
    signIn('TELLER')
    const api = fakeApi({ 'GET /teller/queue': { items: [item], next_cursor: null } })
    renderRoutes([{ path: '/teller', element: <TellerConsole /> }], '/teller', api)
    const box = await screen.findByLabelText(/Customer said/)
    fireEvent.keyDown(box, { key: '2' })
    expect(screen.getByRole('button', { name: /Seems distressed/ })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })
})
