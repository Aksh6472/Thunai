import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { ApiError } from '../../api/client'
import { fakeApi, renderRoutes } from '../../test/utils'
import { TrustedContactPage } from './TrustedContactPage'

const TOKEN = 'tok_abcdefghijklmnopqrstuvwxyz'
const routes = [{ path: '/t/:token', element: <TrustedContactPage /> }]
const view = {
  customer_first_name: 'Kamala',
  amount_display: '₹46,00,000',
  channel: 'BRANCH',
  held_at: '2026-10-03T05:50:00Z',
  bank_helpline: '1800-XXX-XXXX (fictional)',
  language: 'en',
  already_responded: false,
}

describe('TrustedContactPage (T-037)', () => {
  it('shows the minimal facts and submits a confirmed response', async () => {
    const api = fakeApi({
      [`GET /trusted/${TOKEN}`]: view,
      [`POST /trusted/${TOKEN}/response`]: { result_key: 'SENT_TO_OFFICER', message: 'x' },
    })
    renderRoutes(routes, `/t/${TOKEN}`, api)
    expect(
      await screen.findByRole('heading', { name: /Kamala's transfer of ₹46,00,000 is paused/ }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /This looks like a scam/ }))
    expect(screen.getByRole('dialog')).toHaveTextContent('a bank officer should step in')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(await screen.findByText(/a bank officer will contact Kamala now/)).toBeInTheDocument()
    expect(api.calls.at(-1)?.body).toEqual({ response: 'REPORT_SUSPICIOUS' })
  })

  it('shows the expired state for a used or expired link (410)', async () => {
    const api = fakeApi({
      [`GET /trusted/${TOKEN}`]: new ApiError(410, {
        code: 'CONTACT_LINK_EXPIRED',
        message: 'gone',
      }),
    })
    renderRoutes(routes, `/t/${TOKEN}`, api)
    expect(await screen.findByText(/This link has expired or was already used/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /genuine/ })).not.toBeInTheDocument()
  })

  it('uses the language from the link', async () => {
    const api = fakeApi({ [`GET /trusted/${TOKEN}`]: { ...view, language: 'ta' } })
    renderRoutes(routes, `/t/${TOKEN}`, api)
    expect(
      await screen.findByRole('button', { name: /இது மோசடி போல் தெரிகிறது/ }),
    ).toBeInTheDocument()
  })
})
