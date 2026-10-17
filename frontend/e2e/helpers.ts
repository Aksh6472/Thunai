import { expect, request, type APIRequestContext, type Page } from '@playwright/test'

import { API_PORT, SEED_PASSWORD } from './env.ts'

export const API = `http://localhost:${API_PORT}/api/v1`

export async function apiAs(username: string): Promise<APIRequestContext> {
  const ctx = await request.newContext({ baseURL: `${API}/` })
  const r = await ctx.post('auth/login', { data: { username, password: SEED_PASSWORD } })
  expect(r.ok()).toBeTruthy()
  const { access_token } = await r.json()
  await ctx.dispose()
  return request.newContext({
    baseURL: `${API}/`,
    extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
  })
}

/** POST /demo/reset as admin.demo. */
export async function resetDemo(): Promise<APIRequestContext> {
  const admin = await apiAs('admin.demo')
  const r = await admin.post('demo/reset')
  expect(r.ok()).toBeTruthy()
  return admin
}

/** Run a scenario at maximum speed and wait for it to finish. */
export async function runScenario(
  admin: APIRequestContext,
  id: string,
): Promise<Record<string, unknown>[]> {
  const r = await admin.post(`demo/scenarios/${id}/run`, { data: { speed: 10_000_000 } })
  expect(r.status()).toBe(202)
  const runId = (await r.json()).run_id
  for (let i = 0; i < 200; i++) {
    const runs = await (await admin.get('demo/runs')).json()
    const run = runs.find((x: { run_id: string }) => x.run_id === runId)
    if (run && run.status !== 'RUNNING') {
      expect(run.status, run.error ?? '').toBe('DONE')
      return run.transfers
    }
    await new Promise((res) => setTimeout(res, 100))
  }
  throw new Error(`scenario ${id} did not finish`)
}

export async function latestContactLink(admin: APIRequestContext): Promise<string> {
  const messages = await (await admin.get('demo/console-messages')).json()
  expect(messages.length).toBeGreaterThan(0)
  return messages[0].link
}

export async function login(page: Page, username: string) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(SEED_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
}
