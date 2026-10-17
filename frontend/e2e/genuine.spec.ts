import { expect, test } from '@playwright/test'

import { login, resetDemo, runScenario } from './helpers.ts'

test('J4 genuine: N1 is allowed and nothing new appears in the queue', async ({ page }) => {
  const admin = await resetDemo()
  const [transfer] = await runScenario(admin, 'N1')
  expect(transfer.decision).toBe('ALLOW')
  expect(transfer.transfer_status).toBe('EXECUTED')
  await login(page, 'officer.rao')
  await page.getByRole('tab', { name: 'Holds' }).click()
  await expect(page.getByText('No customers need attention right now.')).toBeVisible()
})
