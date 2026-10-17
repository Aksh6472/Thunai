import { expect, test } from '@playwright/test'

import { latestContactLink, login, resetDemo, runScenario } from './helpers.ts'

test('J1 hero: watch → VERY_HIGH hold → teller → report → contact → officer cancels', async ({
  browser,
  page,
}) => {
  const admin = await resetDemo()
  const [transfer] = await runScenario(admin, 'P1')
  expect(transfer.tier).toBe('VERY_HIGH')
  expect(transfer.raw_score).toBe(115)

  // Officer sees the hold at the top of the queue.
  await login(page, 'officer.rao')
  await expect(page).toHaveURL(/\/ops$/)
  const row = page.getByRole('option').filter({ hasText: 'R. Kamala (fictional)' })
  await expect(row.first()).toContainText('₹46,00,000')
  await expect(row.first()).toContainText('Hold — urgent')

  // The teller at the counter applies observations with hotkeys 1 and 4.
  const tellerCtx = await browser.newContext({ viewport: { width: 1366, height: 768 } })
  const teller = await tellerCtx.newPage()
  await login(teller, 'teller.priya')
  await expect(teller.getByRole('alert').first()).toContainText('Pause before processing')
  await teller.getByRole('button', { name: /R\. Kamala/ }).click()
  await expect(teller.getByRole('button', { name: /On a call now/ })).toBeVisible()
  await teller.keyboard.press('1')
  await teller.keyboard.press('4')
  await expect(teller.getByRole('button', { name: /On a call now/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await teller.getByRole('button', { name: 'Apply observations' }).click()
  await expect(teller.getByText(/Teller: the customer mentions police/)).toBeVisible()
  await expect(teller.getByText('Score 100 · Hold — urgent')).toBeVisible()
  // Tamil script is the default for this customer's counter case.
  await expect(teller.getByText(/டிஜிட்டல் கைது/)).toBeVisible()
  await teller.getByRole('button', { name: 'English' }).click()
  await expect(teller.getByText(/There is no 'digital arrest' in Indian law/)).toBeVisible()
  await teller.getByRole('button', { name: 'Generate report draft' }).click()
  await expect(teller.getByText('https://cybercrime.gov.in').first()).toBeVisible()
  await expect(teller.getByRole('link', { name: '1930' })).toBeVisible()

  // Trusted contact on a phone: reports a scam.
  const link = await latestContactLink(admin)
  const phoneCtx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
  })
  const phone = await phoneCtx.newPage()
  await phone.goto(link.replace(/^https?:\/\/[^/]+/, ''))
  await expect(phone.getByRole('heading', { name: /கமலா|Kamala/ })).toBeVisible()
  await phone.getByRole('button', { name: 'English' }).click()
  await phone.getByRole('button', { name: /This looks like a scam/ }).click()
  await phone.getByRole('button', { name: 'Confirm' }).click()
  await expect(phone.getByText(/a bank officer will contact Kamala now/)).toBeVisible()

  // Officer sees the response and cancels with a note.
  await row.first().dblclick()
  // 115 initially, plus the teller's ON_CALL (8) and MENTIONS_AUTHORITY (15) = 138.
  await expect(page.getByText('Score 100 (raw 138)')).toBeVisible()
  await expect(page.getByText(/Response: Contact says it looks like a scam/)).toBeVisible()
  await page.getByLabel(/Note \(required/).fill('Customer confirmed a CBI "digital arrest" call.')
  await page.getByRole('button', { name: 'Cancel transfer' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel transfer' }).click()
  await expect(page.getByText(/Transfer cancelled\. Report draft ready\./)).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByText('Cancelled').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Release transfer' })).toHaveCount(0)

  await tellerCtx.close()
  await phoneCtx.close()
})
