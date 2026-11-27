import { test, expect } from './fixtures'

const listing = '00000000-0000-4000-8000-000000000004'
const account = '00000000-0000-4000-8000-000000000001'
function snapshot(updated: boolean, failed = false) {
  return { scope: 'ALL', as_of: '2026-11-27', account_count: 1, position_count: 1,
    totals: { cost: '1000.00', value: updated ? '1100.00' : null, paid_income: '0.00', gain: updated ? '100.00' : null,
      gain_percent: updated ? '10.00' : null, known_value: updated ? '1100.00' : '0.00', complete: updated, allocation_value: [], allocation_cost: [] },
    positions: [{ account_id: account, account_name: 'Synthetic Yahoo', account_kind: 'IKE', label: 'IUSQ · XETR', asset_class: 'ETF', currency: 'EUR',
      native_cost: '200.00', native_value: updated ? '220.00' : null, cost_pln: '1000.00', value_pln: updated ? '1100.00' : null,
      gain_pln: updated ? '100.00' : null, paid_income: '0.00', reasons: updated ? [] : ['missing_price'], quantity: '2', listing_id: listing,
      observed_on: updated ? '2026-11-27' : null, price_source: updated ? 'YAHOO' : null, quoted_at: updated ? '2026-11-27T12:00:00Z' : null,
      fetched_at: updated ? '2026-11-27T12:16:00Z' : null, yahoo: { symbol: 'IUSQ.DE', failed, attempted_at: null, fetched_at: null, quoted_at: null } }],
    estimated_fx: true, missing_fx: [], fx_rates: [],
  }
}

test('Yahoo fetch on load and reload updates dashboard and displays both timestamps', async ({ page }) => {
  let updated = false
  let calls = 0
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: snapshot(updated) }))
  await page.route('**/api/market-prices/refresh', async (route) => {
    calls++; updated = true
    await route.fulfill({ json: { updated: 1, failed: 0, cooldown_seconds: 300 } })
  })
  await page.goto('/')
  const portfolio = page.locator('.portfolio-section')
  await expect(portfolio.locator('.portfolio-cards')).toContainText('1\u00a0100,00 PLN')
  const row = portfolio.getByRole('row').filter({ hasText: 'Synthetic Yahoo' })
  await expect(row).toContainText('Yahoo Finance')
  await expect(row).toContainText('Notowanie:')
  await expect(row).toContainText('Pobrano:')
  await page.reload()
  await expect(portfolio.getByRole('status', { name: 'Stan Yahoo' })).toContainText('sprawdzono')
  expect(calls).toBeGreaterThanOrEqual(2)
  await portfolio.getByRole('button', { name: 'Odśwież podsumowanie', exact: true }).click()
  await expect(portfolio.getByRole('status', { name: 'Stan Yahoo' })).toContainText('odświeżono 1')
})

test('Yahoo failure keeps last valuation visible and mapping can be disabled', async ({ page }) => {
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: snapshot(true, true) }))
  await page.route('**/api/market-prices/refresh', (route) => route.fulfill({ json: { updated: 0, failed: 1, cooldown_seconds: 300 } }))
  let disabled = false
  await page.route('**/api/listings/*/yahoo', (route) => { disabled = route.request().method() === 'DELETE'; return route.fulfill({ json: { symbol: null } }) })
  await page.goto('/')
  const portfolio = page.locator('.portfolio-section')
  await expect(portfolio.getByRole('status', { name: 'Stan Yahoo' })).toContainText('Zachowano poprzednie ceny')
  await expect(portfolio.locator('.portfolio-cards')).toContainText('1\u00a0100,00 PLN')
  await portfolio.getByText('Automatyczne kursy Yahoo Finance', { exact: true }).click()
  await portfolio.getByRole('button', { name: 'Wylacz Yahoo', exact: true }).click()
  await expect.poll(() => disabled).toBe(true)
  await expect(portfolio.getByRole('form', { name: 'Yahoo: IUSQ · XETR' }).getByRole('status')).toContainText('Wylaczono Yahoo')
})

test('explicit Yahoo mapping sends symbol and shows provider failure', async ({ page }) => {
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: snapshot(false) }))
  await page.route('**/api/market-prices/refresh', (route) => route.fulfill({ json: { updated: 0, failed: 1, cooldown_seconds: 300 } }))
  let symbol = ''
  await page.route('**/api/listings/*/yahoo', (route) => {
    symbol = route.request().postDataJSON().symbol
    return route.fulfill({ json: { symbol } })
  })
  await page.goto('/')
  const portfolio = page.locator('.portfolio-section')
  await portfolio.getByText('Automatyczne kursy Yahoo Finance', { exact: true }).click()
  const form = portfolio.getByRole('form', { name: 'Yahoo: IUSQ · XETR' })
  await form.getByLabel('Symbol Yahoo Finance').fill('iusq.de')
  await form.getByRole('button', { name: 'Zapisz symbol Yahoo' }).click()
  await expect.poll(() => symbol).toBe('IUSQ.DE')
  await expect(form.getByRole('status')).toContainText('pobranie nie powiodlo sie')
})
