import { expect, test } from './fixtures'
import { iusq, iusqAccount, openIusq } from './instrument-fixture'

async function seed(page: import('@playwright/test').Page) {
  const account = await iusqAccount(page)
  const response = await page.request.post(`/api/accounts/${account}/purchases`, { data: { listing_id: iusq, request_id: crypto.randomUUID(), trade_date: '2026-01-08', quantity: '0.125', unit_price: '100.12345678', commission: '0.10', currency: 'EUR' } })
  expect(response.status()).toBe(201)
  await openIusq(page)
  return page.getByRole('region', { name: 'Historia zakupów instrumentu', exact: true })
}

test('existing fractional purchases can be corrected with audit and survive reload', async ({ page }) => {
  const history = await seed(page)
  const row = history.getByRole('row').filter({ hasText: '08.01.2026' })
  await expect(row).toContainText('0,125')
  await expect(row).toContainText('100,12345678')
  await expect(row).toContainText('12,62')
  await row.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
  await history.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,25')
  await history.getByLabel('Powód korekty instrumentu', { exact: true }).fill('Syntetyczna korekta ilości')
  await history.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
  await expect(history.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toContainText('Korekta instrumentu została zapisana')
  await expect(row).toContainText('0,25')
  await row.getByRole('button', { name: 'Zmiany instrumentu', exact: true }).click()
  await expect(history.getByRole('region', { name: 'Historia zmian zakupu' })).toContainText('Syntetyczna korekta ilości')
  await openIusq(page)
  await expect(row).toContainText('0,25')
})

test('invalid correction preserves fields and requires a reason', async ({ page }) => {
  const history = await seed(page)
  await history.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
  await history.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,123456789')
  await history.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
  await expect(history.getByRole('alert')).toBeVisible()
  await expect(history.getByLabel('Liczba jednostek instrumentu', { exact: true })).toHaveValue('0,123456789')
  await history.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('1')
  await history.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
  await expect(history.getByRole('alert')).toContainText('powód korekty')
})

test('correction fields appear only after choosing a history row and can be cancelled', async ({ page }) => {
  const history = await seed(page)
  await expect(history.getByRole('form')).toHaveCount(0)
  await history.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
  await expect(history.getByRole('form', { name: 'Korekta zakupu instrumentu' })).toBeVisible()
  await history.getByRole('button', { name: 'Anuluj korektę instrumentu', exact: true }).click()
  await expect(history.getByRole('form')).toHaveCount(0)
})

test('purchase history fits a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const history = await seed(page)
  await expect(history.getByRole('heading', { name: 'Historia zakupów instrumentu' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
