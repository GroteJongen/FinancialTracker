import { expect, test } from './fixtures'

for (const cached of [false, true]) {
  test(`opening page refreshes NBP and PLN totals, cached=${cached}`, async ({ page }) => {
    let ready = cached
    let calls = 0
    await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: {
      scope: 'ALL', as_of: '2026-11-27', account_count: 1, position_count: 1,
      estimated_fx: true, missing_fx: ready ? [] : [{ currency: 'EUR', requested_on: '2026-11-10' }], fx_rates: [], positions: [],
      totals: { cost: ready ? '4000.00' : null, value: ready ? '5500.00' : null, gain: ready ? '1500.00' : null, gain_percent: ready ? '37.50' : null, paid_income: '0.00', known_value: '0.00', complete: ready, allocation_value: [], allocation_cost: [] },
    } }))
    await page.route('**/api/portfolio/fx/refresh?*', async (route) => {
      calls++
      expect(new URL(route.request().url()).searchParams.get('only_missing')).toBe('false')
      ready = true
      await route.fulfill({ json: { updated: 1, failed: 0, remaining: 0 } })
    })
    await page.goto('/')
    const section = page.getByRole('region', { name: 'Mój portfel', exact: true })
    await expect(section.getByRole('status', { name: 'Kursy NBP' })).toContainText('odświeżono 1')
    const card = section.locator('.portfolio-cards > div').filter({ has: page.getByText('Wartość aktywów', { exact: true }) }).locator('dd')
    await expect(card).toHaveText('5\u00a0500,00 PLN')
    expect(calls).toBe(1)
  })
}

test('NBP outage preserves native value and gain without automatic retry loop', async ({ page }) => {
  let calls = 0
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: {
    scope: 'ALL', as_of: '2026-11-27', account_count: 1, position_count: 1, estimated_fx: true,
    missing_fx: [{ currency: 'EUR', requested_on: '2026-11-10' }], fx_rates: [],
    totals: { cost: null, value: null, gain: null, gain_percent: null, paid_income: '0.00', known_value: '0.00', complete: false, allocation_value: [], allocation_cost: [] },
    positions: [{ account_id: 'synthetic', account_name: 'TEST EUR', account_kind: 'STANDARD', label: 'TEST ETF', asset_class: 'ETF', currency: 'EUR', quantity: '10', native_cost: '1000.00', native_value: '1100.00', native_gain: '100.00', native_gain_percent: '10.00', cost_pln: null, value_pln: null, gain_pln: null, gain_percent: null, paid_income: '0.00', observed_on: '2026-11-20', reasons: ['missing_fx'], unit_price: '110.00' }],
  } }))
  await page.route('**/api/portfolio/fx/refresh?*', async (route) => {
    calls++
    await route.fulfill({ json: { updated: 0, failed: 1, remaining: 1 } })
  })
  await page.goto('/')
  const section = page.getByRole('region', { name: 'Mój portfel', exact: true })
  await expect(section.getByRole('status', { name: 'Kursy NBP' })).toContainText('nie powiodła się')
  const row = section.getByRole('row').filter({ hasText: 'TEST ETF' })
  await expect(row).toContainText('1\u00a0100,00 EUR')
  await expect(row).toContainText('100,00 EUR')
  await expect(row).toContainText('10,00%')
  await expect(row).toContainText('Wynik w EUR')
  await page.evaluate(() => window.dispatchEvent(new Event('financialtracker:updated')))
  await expect(row).toBeVisible()
  expect(calls).toBe(1)
})
