import { expect, test } from './fixtures'
import { formatDecimal } from '../src/shared/api'

test('bond purchase immediately has accrued value, no FX required, and survives reload', async ({ page }) => {
  const accountResponse = await page.request.post('/api/bond-accounts', { data: { name: 'TEST naliczanie ' + Date.now(), kind: 'STANDARD' } })
  expect(accountResponse.ok()).toBeTruthy()
  const account = await accountResponse.json()
  const response = await page.request.post(`/api/accounts/${account.id}/bonds`, { data: {
    request_id: crypto.randomUUID(), series: 'TOS1129', trade_date: '2026-11-10', quantity: 10,
    unit_price: '99.90', annual_rate: '4.4', interest_mode: 'CAPITALIZE',
  } })
  expect(response.status()).toBe(201)
  const group = await (await page.request.post('/api/portfolios', { data: { name: 'TEST portfel odsetki ' + Date.now(), account_ids: [account.id] } })).json()
  const snapshot = await (await page.request.get('/api/portfolio?portfolio_id=' + group.id)).json()
  const holding = snapshot.positions.find((item: { account_id: string }) => item.account_id === account.id)
  expect(holding.bond_calculation).toBe('ACCRUED')
  expect(holding.value_pln).not.toBeNull()
  expect(holding.reasons).toEqual([])
  expect(snapshot.missing_fx).toEqual([])
  let fxCalls = 0
  await page.route('**/api/portfolio/fx/refresh?*', (route) => {
    if (new URL(route.request().url()).searchParams.get('portfolio_id') === group.id) fxCalls++
    return route.fulfill({ json: { updated: 0, failed: 0, remaining: 0 } })
  })
  await page.goto('/')
  const region = page.getByRole('region', { name: 'Mój portfel', exact: true })
  await region.getByLabel('Portfel', { exact: true }).selectOption(group.id)
  const row = region.getByRole('row').filter({ hasText: account.name })
  await expect(row).toContainText('Naliczone brutto')
  await expect(row).toContainText('kapitalizacja co roku')
  await expect(row).toContainText(formatDecimal(holding.value_pln, 2) + ' PLN')
  await expect(row).toContainText(formatDecimal(holding.gain_pln, 2) + ' PLN')
  expect(fxCalls).toBe(0)
  await page.reload()
  await region.getByLabel('Portfel', { exact: true }).selectOption(group.id)
  await expect(row).toContainText(formatDecimal(holding.value_pln, 2) + ' PLN')
})

test('opening dashboard fetches missing bond data once, failure stays incomplete with retry', async ({ page }) => {
  await page.request.post('/api/bond-accounts', { data: { name: 'TEST braki odsetek ' + Date.now(), kind: 'STANDARD' } })
  let calls = 0
  await page.route('**/api/bonds/refresh?*', (route) => {
    calls++
    return route.fulfill({ json: { updated: 0, failed: 1, remaining: 1 } })
  })
  await page.route('**/api/portfolio?scope=*', (route) => route.fulfill({ json: {
    scope: 'ALL', as_of: '2026-11-28', account_count: 1, position_count: 1,
    totals: { cost: '1000.00', value: null, gain: null, gain_percent: null, paid_income: '0.00', known_value: '0.00', complete: false, allocation_value: [], allocation_cost: [] },
    bond_requirements: ['CPI:2025-09'], missing_fx: [], fx_rates: [], estimated_fx: false,
    positions: [{ account_id: 'synthetic', account_name: 'Test CPI', account_kind: 'STANDARD', label: 'COI1128', asset_class: 'BOND', currency: 'PLN', quantity: '10', native_cost: '1000.00', cost_pln: '1000.00', native_value: null, value_pln: null, gain_pln: null, paid_income: null, reasons: ['missing_bond_valuation'], observed_on: null, bond_missing_data: 'missing_bond_inflation', bond_nominal_value: '1000.00' }],
  } }))
  await page.goto('/')
  const region = page.getByRole('region', { name: 'Mój portfel', exact: true })
  const status = region.getByRole('status', { name: 'Dane obligacji' })
  await expect(status).toContainText('Nie udało się uzupełnić wszystkich danych')
  await expect(region.getByRole('status', { name: 'Kompletność portfela' })).toContainText('nie jest to brak kursu NBP')
  await expect(region.getByText('Wartość aktywów', { exact: true }).locator('..').locator('dd')).toHaveText('—')
  expect(calls).toBe(1)
  await region.getByRole('button', { name: 'Odśwież dane obligacji', exact: true }).click()
  await expect(status).toContainText('Nie udało się uzupełnić wszystkich danych')
  expect(calls).toBe(2)
})
