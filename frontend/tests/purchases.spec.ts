import { expect, test } from './fixtures'
import { openIusq } from './instrument-fixture'

test('adds fractional purchases, corrects with audit, and survives reload', async ({ page }) => {
  await openIusq(page)
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,125')
  await page.getByLabel('Cena zakupu instrumentu (EUR)', { exact: true }).fill('100,12345678')
  await page.getByLabel('Prowizja zakupu instrumentu (EUR)', { exact: true }).fill('0,10')
  await page.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-01-08')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(page.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toHaveText('Zakup instrumentu został zapisany.')
  let row = page.getByRole('row').filter({ hasText: '08.01.2026' })
  await expect(row).toContainText('0,125')
  await expect(row).toContainText('100,12345678')
  await row.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,25')
  await page.getByLabel('Powód korekty instrumentu', { exact: true }).fill('Przepisano ilość z potwierdzenia')
  await page.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
  await expect(page.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toContainText('Korekta instrumentu została zapisana')
  await expect(row).toContainText('0,25')
  await row.getByRole('button', { name: 'Zmiany instrumentu', exact: true }).click()
  const history = page.getByRole('region', { name: 'Historia zmian zakupu' })
  await expect(history).toContainText('Przepisano ilość z potwierdzenia')
  await expect(history).toContainText('0,125')
  await expect(history).toContainText('0,25')
  await openIusq(page)
  row = page.getByRole('row').filter({ hasText: '08.01.2026' })
  await expect(row).toContainText('0,25')
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('2')
  await page.getByLabel('Cena zakupu instrumentu (EUR)', { exact: true }).fill('110')
  await page.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-01-09')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '09.01.2026' })).toContainText('110,00')
})

test('rejects excess precision and missing correction reason without losing input', async ({ page }) => {
  await openIusq(page)
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,123456789')
  await page.getByLabel('Cena zakupu instrumentu (EUR)', { exact: true }).fill('100')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('do 8 miejsc po przecinku')
  await expect(page.getByLabel('Liczba jednostek instrumentu', { exact: true })).toHaveValue('0,123456789')
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('1')
  await page.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-01-06')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  const row = page.getByRole('row').filter({ hasText: '06.01.2026' })
  await row.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
  await page.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('powód korekty')
})

test('lost create response can be retried without a duplicate purchase', async ({ page }) => {
  let first = true
  await page.route('**/api/accounts/*/purchases', async (route) => {
    if (route.request().method() === 'POST' && first) {
      first = false
      await route.fetch()
      await route.abort('failed')
    } else {
      await route.continue()
    }
  })
  await openIusq(page)
  await page.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,333')
  await page.getByLabel('Cena zakupu instrumentu (EUR)', { exact: true }).fill('98')
  await page.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-01-07')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await page.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(page.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toContainText('Zakup instrumentu został zapisany')
  await openIusq(page)
  await expect(page.getByRole('row').filter({ hasText: '07.01.2026' })).toHaveCount(1)
})

test('purchase form and table fit a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await openIusq(page)
  await expect(page.getByLabel('Liczba jednostek instrumentu', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
