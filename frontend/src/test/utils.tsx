import { render, type RenderResult } from '@testing-library/react'
import type { ReactNode } from 'react'
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router'

import { ApiError, type ApiClient } from '../api/client'
import { tokenStore } from '../api/tokenStore'
import type { Role, User } from '../api/types'
import { Providers } from '../app/providers'

type Handler = (body?: unknown) => unknown
export type Routes = Record<string, Handler | unknown>

/** A fake API client: keys are "METHOD /path" (exact) mapped to a value or a function. */
export function fakeApi(
  routes: Routes,
): ApiClient & { calls: { method: string; path: string; body?: unknown }[] } {
  const calls: { method: string; path: string; body?: unknown }[] = []
  async function request<T>(method: string, path: string, body?: unknown) {
    calls.push({ method, path, body })
    const handler = routes[`${method} ${path}`]
    if (handler === undefined)
      throw new ApiError(404, { code: 'NOT_FOUND', message: `no fake for ${method} ${path}` })
    const data = typeof handler === 'function' ? (handler as Handler)(body) : handler
    if (data instanceof ApiError) throw data
    return { data: (await data) as T, status: 200, headers: new Headers() }
  }
  return {
    calls,
    request,
    get: async (path) => (await request('GET', path)).data as never,
    post: async (path, body) => (await request('POST', path, body ?? {})).data as never,
    patch: async (path, body) => (await request('PATCH', path, body)).data as never,
  }
}

export function signIn(role: Role | null) {
  if (!role) {
    tokenStore.set(null)
    return
  }
  const user: User = {
    id: 'u1',
    role,
    display_name: `${role} (fictional)`,
    branch_code: 'CHN001',
    customer_ref: null,
  }
  tokenStore.set({ token: 't', user, expiresAt: Date.now() + 3_600_000 })
}

export function renderWith(ui: ReactNode, api: ApiClient): RenderResult {
  return render(<Providers api={api}>{ui}</Providers>)
}

export function renderRoutes(routes: RouteObject[], path: string, api: ApiClient): RenderResult {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <Providers api={api}>
      <RouterProvider router={router} />
    </Providers>,
  )
}
