import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { fakeApi, renderRoutes, signIn } from '../test/utils'
import { routes } from './routes'

const api = fakeApi({
  'GET /teller/queue': { items: [], next_cursor: null },
  'GET /demo/clock': { sim_now: '2026-10-01T03:30:00Z', speed: 0, running_scenario: null },
})

describe('route guards (T-011)', () => {
  afterEach(() => signIn(null))

  it('renders the login page', async () => {
    renderRoutes(routes, '/login', api)
    expect(await screen.findByRole('heading', { name: /Sign in to Thunai/ })).toBeInTheDocument()
  })

  it('sends anonymous users to login', async () => {
    renderRoutes(routes, '/ops', api)
    expect(await screen.findByRole('heading', { name: /Sign in to Thunai/ })).toBeInTheDocument()
  })

  it('shows the 403 page to a teller on /ops', async () => {
    signIn('TELLER')
    renderRoutes(routes, '/ops', api)
    expect(await screen.findByText(/don't have access/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to your home' })).toHaveAttribute('href', '/teller')
  })

  it('lets a teller into the teller console', async () => {
    signIn('TELLER')
    renderRoutes(routes, '/teller', api)
    expect(await screen.findByText('No branch transfers need attention.')).toBeInTheDocument()
  })

  it('keeps the trusted-contact page public', async () => {
    const contactApi = fakeApi({})
    renderRoutes(routes, '/t/abcdefghijklmnopqrstu', contactApi)
    expect(await screen.findByText(/This link is not valid/)).toBeInTheDocument()
  })
})
