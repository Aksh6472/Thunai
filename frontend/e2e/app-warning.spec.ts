import { expect, test } from '@playwright/test'

import { login, resetDemo } from './helpers.ts'

test('J2 app warning: MEDIUM transfer → warning, 3 s delay, cancel', async ({ page }) => {
  await resetDemo()
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'cust.meena')
  await page.getByRole('button', { name: 'Send money' }).click()
  await page.getByLabel('Payee').selectOption({ label: 'Online Seller (fictional) · XXXXXX9159' })
  await page.getByLabel('Amount (₹)').fill('300000')
  await page.getByLabel('Amount (₹)').blur()
  await expect(page.getByLabel('Amount (₹)')).toHaveValue('3,00,000')
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(
    page.getByRole('heading', { name: 'Please pause before you send this money' }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: /Call 1930/ })).toHaveAttribute('href', 'tel:1930')
  const continueButton = page.getByRole('button', { name: /I understand, continue/ })
  await expect(continueButton).toBeDisabled()
  await expect(page.getByRole('button', { name: 'I understand, continue' })).toBeEnabled({
    timeout: 5000,
  })
  await page.getByRole('button', { name: 'Cancel this transfer' }).click()
  await expect(
    page.getByText('Transfer cancelled. Your money stays in your account.'),
  ).toBeVisible()
})
