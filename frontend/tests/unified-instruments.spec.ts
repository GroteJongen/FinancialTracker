import { expect, test } from './fixtures'
import { iusq, iusqAccount, openIusq } from './instrument-fixture'

test('existing IUSQ purchases and prices remain accessible in the single instrument view', async ({ page }) => {
  const account = await iusqAccount(page)
  const purchase = await page.request.post(`/api/accounts/${account}/purchases`, { data: { listing_id: iusq, request_id: crypto.randomUUID(), quantity: '2', unit_price: '100', commission: '0', trade_date: '2026-11-10', currency: 'EUR' } })
  expect(purchase.status()).toBe(201)
  await page.request.post(`/api/accounts/${account}/prices`, { data: { listing_id: iusq, request_id: crypto.randomUUID(), price: '110', observed_on: '2026-11-20', currency: 'EUR' } })
  await openIusq(page)
  await expect(page.locator('.etf-operations')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Operacje ETF (EUR)', exact: true })).toHaveCount(0)
  const section = page.getByRole('region', { name: 'Instrumenty', exact: true })
  await expect(section.getByRole('heading', { name: 'Pozycja: IUSQ · XETR' })).toBeVisible()
  await expect(section.locator('.instrument-position-cards')).toContainText('220,00 EUR')
  await expect(section.getByRole('row').filter({ hasText: '10.11.2026' })).toContainText('100,00')
  await section.getByText('Historia cen ręcznych (1)', { exact: true }).click()
  await expect(section.getByRole('table', { name: 'Historia cen wyceny' })).toContainText('110,00')
  await expect(section.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true })).toHaveCount(1)
  await expect(section.getByRole('button', { name: 'Zapisz cenę instrumentu', exact: true })).toHaveCount(1)
})
