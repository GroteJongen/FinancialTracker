import { expect, test } from '@playwright/test'

test('shows live backend and seeded account', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('status')).toHaveText('Aplikacja i baza danych są połączone')
  await expect(page.getByRole('heading', { name: 'IKE — demonstracja' })).toBeVisible()
  await expect(page.getByText('Bez aktywów i transakcji')).toBeVisible()
})

test('mobile layout fits viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'IKE — demonstracja' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})

test('empty account list is an empty state, not a fictitious portfolio', async ({ page }) => {
  await page.route('**/api/accounts', (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: '[]',
  }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Jeszcze nie masz rachunków' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'IKE — demonstracja' })).toHaveCount(0)
})

test('reports backend error and allows retry', async ({ page }) => {
  await page.route('**/api/health/ready', (route) => route.fulfill({
    status: 503, contentType: 'application/json', body: '{"status":"unavailable"}',
  }))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Nie udało się połączyć')
  await page.unroute('**/api/health/ready')
  await page.getByRole('button', { name: 'Spróbuj ponownie' }).click()
  await expect(page.getByRole('status')).toHaveText('Aplikacja i baza danych są połączone')
})

