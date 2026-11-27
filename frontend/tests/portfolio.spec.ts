import { expect, test } from './fixtures'
import type { Page } from '@playwright/test'

test.use({ actionTimeout: 10000 })
const portfolio = (page: Page) => page.getByRole('region', { name: 'Mój portfel', exact: true })
const card = (page: Page, label: string) => portfolio(page).locator('.portfolio-cards > div').filter({ has: page.getByText(label, { exact: true }) }).locator('dd')
const sectors = [
  { asset_class: 'BOND', amount: '110000.00', percent: '59.46', start: '0.00', end: '59.46' },
  { asset_class: 'ETF', amount: '50000.00', percent: '27.03', start: '59.46', end: '86.49' },
  { asset_class: 'STOCK', amount: '25000.00', percent: '13.51', start: '86.49', end: '100.00' },
]
const costs = [
  { asset_class: 'BOND', amount: '100000.00', percent: '57.14', start: '0.00', end: '57.14' },
  { asset_class: 'ETF', amount: '50000.00', percent: '28.57', start: '57.14', end: '85.71' },
  { asset_class: 'STOCK', amount: '25000.00', percent: '14.29', start: '85.71', end: '100.00' },
]

function snapshot(scope = 'ALL', incomplete = false) {
  const values: Record<string, [string, string, string]> = { ALL: ['175000.00', '185000.00', '10000.00'], STANDARD: ['100000.00', '110000.00', '10000.00'], IKE: ['50000.00', '50000.00', '0.00'], IKZE: ['25000.00', '25000.00', '0.00'], RETIREMENT: ['75000.00', '75000.00', '0.00'] }
  const [cost, value, gain] = values[scope]
  return { scope, as_of: '2026-11-27', account_count: 3, position_count: 3,
    totals: { cost, value: incomplete ? null : value, gain: incomplete ? null : gain, gain_percent: incomplete ? null : '5.71', paid_income: '0.00', known_value: '135000.00', complete: !incomplete, allocation_value: incomplete ? [] : sectors, allocation_cost: costs },
    positions: [], missing_fx: [], fx_rates: [], estimated_fx: false,
  }
}

test('dashboard example, filters and real pie rendering on mobile', async ({ page }) => {
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot(new URL(route.request().url()).searchParams.get('scope') ?? 'ALL')) }))
  await page.goto('/')
  await expect(card(page, 'Koszt zakupów')).toHaveText('175\u00a0000,00 PLN')
  await expect(card(page, 'Wartość aktywów')).toHaveText('185\u00a0000,00 PLN')
  await expect(card(page, 'Łączny zysk / strata')).toHaveText('10\u00a0000,00 PLN')
  const pie = portfolio(page).getByRole('img', { name: /Udziały portfela/ })
  await expect(pie).toBeVisible()
  await expect(pie).toHaveAttribute('aria-label', /59,46%/)
  expect(await pie.evaluate((element) => getComputedStyle(element).backgroundImage)).toContain('conic-gradient')
  for (const [label, value] of [['IKE', '50\u00a0000,00 PLN'], ['IKZE', '25\u00a0000,00 PLN'], ['IKE + IKZE', '75\u00a0000,00 PLN'], ['Zwykłe', '110\u00a0000,00 PLN'], ['Wszystkie', '185\u00a0000,00 PLN']]) {
    await portfolio(page).getByRole('group', { name: 'Filtr portfela' }).getByRole('button', { name: label, exact: true }).click()
    await expect(card(page, 'Wartość aktywów')).toHaveText(value)
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(pie).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})

test('incomplete value stays unknown while cost allocation remains available', async ({ page }) => {
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot('ALL', true)) }))
  await page.goto('/')
  await expect(card(page, 'Wartość aktywów')).toHaveText('—')
  await expect(card(page, 'Łączny zysk / strata')).toHaveText('—')
  await expect(portfolio(page).getByRole('status', { name: 'Kompletność portfela' })).toContainText('niepełne')
  await expect(portfolio(page).getByRole('img')).toHaveCount(0)
  await portfolio(page).getByRole('button', { name: 'Według kosztu', exact: true }).click()
  await expect(portfolio(page).getByRole('img')).toHaveAttribute('aria-label', /57,14%/)
})

test('actual stock price update refreshes portfolio without a page reload', async ({ page }) => {
  const tag = Date.now().toString()
  const account = await (await page.request.post('/api/investment-accounts', { data: { name: 'TEST live portfel ' + tag, kind: 'IKZE', currency: 'PLN' } })).json()
  const listing = await (await page.request.post('/api/stocks', { data: { name: 'TEST live spółka ' + tag, symbol: 'P' + tag, mic: 'XWAR', currency: 'PLN' } })).json()
  await page.request.post(`/api/accounts/${account.id}/purchases`, { data: { request_id: crypto.randomUUID(), listing_id: listing.id, currency: 'PLN', trade_date: '2026-11-01', quantity: '10', unit_price: '100', commission: '0' } })
  await page.request.post(`/api/accounts/${account.id}/prices`, { data: { request_id: crypto.randomUUID(), listing_id: listing.id, currency: 'PLN', observed_on: '2026-11-20', price: '110' } })
  await page.goto('/')
  const row = portfolio(page).getByRole('row').filter({ hasText: account.name })
  await expect(row).toContainText('1\u00a0100,00 PLN')
  const stocks = page.getByRole('region', { name: 'Akcje', exact: true })
  await stocks.getByLabel('Podgląd akcji', { exact: true }).selectOption(listing.id)
  await stocks.getByLabel('Rachunek akcji', { exact: true }).selectOption(account.id)
  await stocks.getByLabel('Cena wyceny akcji (PLN)', { exact: true }).fill('120')
  await stocks.getByLabel('Data wyceny akcji', { exact: true }).fill('2026-11-21')
  await stocks.getByRole('button', { name: 'Zapisz cenę akcji', exact: true }).click()
  await expect(row).toContainText('1\u00a0200,00 PLN')
  await expect(row).toContainText('200,00 PLN')
})

test('actual bond valuation and paid interest are shown without duplicate payouts', async ({ page }) => {
  const account = await (await page.request.post('/api/bond-accounts', { data: { name: 'TEST odsetki portfel ' + Date.now(), kind: 'STANDARD' } })).json()
  await page.request.post(`/api/accounts/${account.id}/bonds`, { data: { request_id: crypto.randomUUID(), series: 'TOS1129', trade_date: '2026-11-10', quantity: 1000, unit_price: '100' } })
  await page.goto('/')
  const row = portfolio(page).getByRole('row').filter({ hasText: account.name })
  await expect(row).toContainText('Uzupełnij wycenę obligacji')
  await row.getByRole('button', { name: 'Wycena obligacji', exact: true }).click()
  const form = portfolio(page).getByRole('form', { name: 'Wycena partii obligacji' })
  await form.getByLabel('Bieżąca wartość obligacji (PLN)', { exact: true }).fill('100000')
  await form.getByLabel('Łączne wypłacone odsetki brutto (PLN)', { exact: true }).fill('10000')
  await form.getByRole('button', { name: 'Zapisz wycenę obligacji', exact: true }).click()
  await expect(row).toContainText('10\u00a0000,00 PLN')
  await expect(row).toContainText('100\u00a0000,00 PLN')
  await expect(form).toHaveCount(0)
  await page.reload()
  await expect(row).toContainText('10\u00a0000,00 PLN')
})

test('NBP failure is reported without inventing exchange rates', async ({ page }) => {
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot('ALL', true)) }))
  await page.route('**/api/portfolio/fx/refresh?scope=*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"updated":0,"failed":1,"remaining":1}' }))
  await page.goto('/')
  await portfolio(page).getByRole('button', { name: 'Pobierz kursy NBP', exact: true }).click()
  await expect(portfolio(page).getByRole('status', { name: 'Informacja portfela' })).toContainText('nie powiodła się')
  await expect(card(page, 'Wartość aktywów')).toHaveText('—')
})
