// Visual review aid, not a gate: SCREENSHOTS=1 SHOT_DIR=/path npx playwright test screenshots
import { expect, test } from '@playwright/test'

import { latestContactLink, login, resetDemo, runScenario } from './helpers.ts'

test.skip(!process.env.SCREENSHOTS, 'set SCREENSHOTS=1 to capture review screenshots')

const dir = process.env.SHOT_DIR ?? 'test-results/screens'

test('capture every surface', async ({ browser, page }) => {
  const admin = await resetDemo()
  await page.goto('/login')
  await page.screenshot({ path: `${dir}/01-login.png` })
  await runScenario(admin, 'P1')
  await runScenario(admin, 'N4')
  await login(page, 'officer.rao')
  await expect(page.getByRole('option').first()).toBeVisible()
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${dir}/02-ops.png`, fullPage: true })
  await page.getByRole('option').first().dblclick()
  await expect(page.getByText('Why this was paused')).toBeVisible()
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${dir}/03-hold.png`, fullPage: true })

  const tctx = await browser.newContext({ viewport: { width: 1366, height: 768 } })
  const teller = await tctx.newPage()
  await login(teller, 'teller.priya')
  await teller.getByRole('button', { name: /R\. Kamala/ }).click()
  await teller.keyboard.press('1')
  await teller.keyboard.press('4')
  await teller.getByRole('button', { name: 'Apply observations' }).click()
  await expect(teller.getByText(/Score 100/)).toBeVisible()
  await teller.screenshot({ path: `${dir}/04-teller.png`, fullPage: true })

  const link = await latestContactLink(admin)
  const pctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true })
  const phone = await pctx.newPage()
  await phone.goto(link.replace(/^https?:\/\/[^/]+/, ''))
  await expect(phone.getByRole('heading')).toBeVisible()
  await phone.screenshot({ path: `${dir}/05-contact.png`, fullPage: true })

  const cctx = await browser.newContext({ viewport: { width: 1366, height: 900 } })
  const cust = await cctx.newPage()
  await login(cust, 'cust.meena')
  await expect(cust.getByRole('button', { name: 'Send money' })).toBeVisible()
  await cust.screenshot({ path: `${dir}/06-customer-home.png` })
  await cust.getByRole('button', { name: 'View' }).first().click()
  await expect(cust.getByRole('heading', { name: /paused/ })).toBeVisible()
  await cust.screenshot({ path: `${dir}/07-customer-hold.png` })

  const actx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const demo = await actx.newPage()
  await login(demo, 'admin.demo')
  await expect(demo.getByText('Run log')).toBeVisible()
  await demo.waitForTimeout(800)
  await demo.screenshot({ path: `${dir}/08-demo.png`, fullPage: true })
})
