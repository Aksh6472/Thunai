import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fakeApi, renderRoutes, signIn } from '../../test/utils'

const demo = vi.hoisted(() => ({ password: 'demo-pass-123' }))
vi.mock('../../config/demo', () => ({
  DEMO_MODE: true,
  get DEMO_AUTOFILL_PASSWORD() {
    return demo.password
  },
}))

const { LoginPage } = await import('./LoginPage')

describe('LoginPage demo accounts', () => {
  afterEach(() => {
    signIn(null)
    demo.password = 'demo-pass-123'
  })

  it('fills the username and the password when autofill is configured', async () => {
    renderRoutes([{ path: '/login', element: <LoginPage /> }], '/login', fakeApi({}))
    fireEvent.click(await screen.findByRole('button', { name: /officer\.rao/ }))
    expect(screen.getByLabelText('Username')).toHaveValue('officer.rao')
    expect(screen.getByLabelText('Password')).toHaveValue('demo-pass-123')
  })

  it('fills only the username when autofill is not configured', async () => {
    demo.password = ''
    renderRoutes([{ path: '/login', element: <LoginPage /> }], '/login', fakeApi({}))
    fireEvent.click(await screen.findByRole('button', { name: /teller\.priya/ }))
    expect(screen.getByLabelText('Username')).toHaveValue('teller.priya')
    expect(screen.getByLabelText('Password')).toHaveValue('')
  })
})
