import { expect, test } from '@playwright/test'

import { latestContactLink, login, resetDemo, runScenario } from './helpers.ts'

test('J3 HIGH hold released by the trusted contact; the customer sees Released', async ({
  browser,
  page,
}) => {
  const admin = await resetDemo()
  const [transfer] = await runScenario(admin, 'N4')
  expect(transfer.tier).toBe('HIGH')

  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'cust.meena')
  await page.getByRole('button', { name: 'View' }).first().click()
  await expect(
    page.getByRole('heading', { name: 'Your transfer is paused for your safety' }),
  ).toBeVisible()
  await expect(page.getByText('We have messaged Priya (sister).')).toBeVisible()
  await expect(
    page.getByText('This transfer looks like patterns used in phone scams.'),
  ).toBeVisible()
  // Customer-safe: no score, tier or reasons on screen.
  await expect(page.getByText(/score|raw|NEW_PAYEE/i)).toHaveCount(0)

  const link = await latestContactLink(admin)
  const phoneCtx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
  })
  const phone = await phoneCtx.newPage()
  await phone.goto(link.replace(/^https?:\/\/[^/]+/, ''))
  await phone.getByRole('button', { name: /I spoke to them — it's genuine/ }).click()
  await phone.getByRole('button', { name: 'Confirm' }).click()
  await expect(phone.getByText('Thank you — the transfer has been released.')).toBeVisible()

  await expect(page.getByText('Your transfer has been released.')).toBeVisible({ timeout: 10_000 })
  await phoneCtx.close()
})
