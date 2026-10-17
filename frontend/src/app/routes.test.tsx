import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'

import { routes } from './routes'

function renderAt(path: string) {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

describe('route shell', () => {
  it('renders the login placeholder at /login', () => {
    renderAt('/login')
    expect(screen.getByRole('heading', { name: /Thunai: Sign in/ })).toBeInTheDocument()
  })

  it.each([
    ['/ops', 'Ops dashboard'],
    ['/teller', 'Teller console'],
    ['/customer', 'Customer app'],
    ['/t/abc', 'Trusted-contact safety check'],
    ['/demo', 'Demo control'],
    ['/nope', 'Page not found'],
  ])('renders %s', (path, label) => {
    renderAt(path)
    expect(screen.getByRole('heading', { name: new RegExp(label) })).toBeInTheDocument()
  })
})
