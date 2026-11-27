import { expect, test } from './fixtures'
import { iusq, iusqAccount, openIusq } from './instrument-fixture'

test('instrument operations show only purchase history without position or creation forms', async ({ page }) => {
  const account = await iusqAccount(page)
  expect((await page.request.post(`/api/accounts/${account}/purchases`, { data: { listing_id: iusq, request_id: crypto.randomUUID(), quantity: '2', unit_price: '100', commission: '0', trade_date: '2026-11-10', currency: 'EUR' } })).status()).toBe(201)
  expect((await page.request.post(`/api/accounts/${account}/prices`, { data: { listing_id: iusq, request_id: crypto.randomUUID(), price: '110', observed_on: '2026-11-20', currency: 'EUR' } })).status()).toBe(201)
  const valuationRequests: string[] = []
  page.on('request', (request) => { if (new URL(request.url()).pathname.endsWith('/valuation')) valuationRequests.push(request.url()) })
  await openIusq(page)
  const section = page.getByRole('region', { name: 'Instrumenty', exact: true })
  const history = section.getByRole('region', { name: 'Historia zakupów instrumentu', exact: true })
  await expect(history.getByRole('row').filter({ hasText: '10.11.2026' })).toContainText('100,00')
  await expect(section.getByRole('heading', { name: /^Pozycja:/ })).toHaveCount(0)
  await expect(section.locator('.instrument-position-cards')).toHaveCount(0)
  await expect(section.getByText(/^Historia cen ręcznych/)).toHaveCount(0)
  await expect(section.getByRole('form', { name: 'Cena wyceny instrumentu', exact: true })).toHaveCount(0)
  await expect(section.getByRole('form', { name: 'Nowy zakup instrumentu', exact: true })).toHaveCount(0)
  await expect(section.getByRole('button', { name: 'Zapisz cenę instrumentu', exact: true })).toHaveCount(0)
  await expect(section.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true })).toHaveCount(0)
  expect(valuationRequests).toHaveLength(0)
  const summary = await (await page.request.get(`/api/accounts/${account}/valuation?listing_id=${iusq}`)).json()
  expect(summary.display.market_value).toBe('220.00')
})
