import { expect, test } from './fixtures'
import type { Page } from '@playwright/test'

test.use({ actionTimeout: 10000 })
const sectionOf = (page: Page) => page.getByRole('region', { name: 'Instrumenty', exact: true })

async function prepareCompany(page: Page, currency: string) {
  await page.goto('/')
  await page.locator('.operations-panel > summary').click()
  const section = sectionOf(page)
  await section.getByRole('button', { name: 'Dodaj instrument', exact: true }).click()
  const marker = Date.now().toString()
  await section.getByLabel('Nazwa instrumentu', { exact: true }).fill('TEST instrumenty ' + currency + ' ' + marker)
  await section.getByLabel('Ticker instrumentu', { exact: true }).fill('SYN' + currency + marker)
  await section.getByLabel('Giełda instrumentu (MIC)', { exact: true }).fill('XWAR')
  await section.getByLabel('Waluta notowania instrumentu', { exact: true }).selectOption(currency)
  return section
}

async function openHistory(page: Page, listing: string, account: string) {
  await page.goto('/')
  await page.locator('.operations-panel > summary').click()
  const section = sectionOf(page)
  await section.getByLabel('Wybierz instrument', { exact: true }).selectOption(listing)
  await section.getByLabel('Rachunek instrumentu', { exact: true }).selectOption(account)
  return section.getByRole('region', { name: 'Historia zakupów instrumentu', exact: true })
}

for (const [currency, kind] of [['PLN', 'STANDARD'], ['EUR', 'IKE'], ['USD', 'IKZE']]) {
  test(`registers stock and preserves ${currency} history on ${kind} with correction audit`, async ({ page }) => {
    const section = await prepareCompany(page, currency)
    await section.getByRole('button', { name: 'Zapisz instrument', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu instrumentu' })).toContainText('Instrument został zapisany')
    await section.getByRole('button', { name: 'Dodaj rachunek instrumentu', exact: true }).click()
    await section.getByLabel('Nazwa rachunku instrumentu', { exact: true }).fill('TEST historia ' + currency + crypto.randomUUID())
    await section.getByLabel('Typ rachunku instrumentu', { exact: true }).selectOption(kind)
    await section.getByLabel('Waluta bazowa rachunku instrumentu', { exact: true }).selectOption(currency)
    await section.getByRole('button', { name: 'Zapisz rachunek instrumentu', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu instrumentu' })).toContainText('Rachunek inwestycyjny został zapisany')
    const listing = await section.getByLabel('Wybierz instrument', { exact: true }).inputValue()
    const account = await section.getByLabel('Rachunek instrumentu', { exact: true }).inputValue()
    expect((await page.request.post('/api/accounts/' + account + '/purchases', { data: { request_id: crypto.randomUUID(), listing_id: listing, currency, trade_date: '2026-10-05', quantity: '10', unit_price: '100', commission: '2' } })).status()).toBe(201)
    const history = await openHistory(page, listing, account)
    const row = history.getByRole('row').filter({ hasText: '05.10.2026' })
    await expect(row).toContainText('100,00')
    await row.getByRole('button', { name: 'Popraw instrument', exact: true }).click()
    await history.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('9')
    await history.getByLabel('Powód korekty instrumentu', { exact: true }).fill('Syntetyczna korekta ilości')
    await history.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
    await expect(history.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toContainText('Korekta instrumentu została zapisana')
    await expect(row.getByRole('cell').nth(1)).toHaveText('9')
    await row.getByRole('button', { name: 'Zmiany instrumentu', exact: true }).click()
    await expect(history.getByRole('region', { name: 'Historia zmian zakupu', exact: true })).toContainText('Syntetyczna korekta ilości')
    await openHistory(page, listing, account)
    await expect(row.getByRole('cell').nth(1)).toHaveText('9')
  })
}

test('catalogue retry after lost response does not duplicate data', async ({ page }) => {
  const section = await prepareCompany(page, 'PLN')
  let first = true
  await page.route('**/api/securities', async (route) => {
    if (first) { first = false; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await section.getByRole('button', { name: 'Zapisz instrument', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await section.getByRole('button', { name: 'Zapisz instrument', exact: true }).click()
  await expect(section.getByRole('status', { name: 'Zapis katalogu instrumentu' })).toContainText('Instrument został zapisany')
  await expect(section.getByRole('region', { name: 'Historia zakupów instrumentu', exact: true })).toContainText('Brak zakupów')
  const listing = await section.getByLabel('Wybierz instrument', { exact: true }).inputValue()
  const listings = await (await page.request.get('/api/listings?kind=ALL')).json() as { id: string }[]
  expect(listings.filter((item) => item.id === listing)).toHaveLength(1)
})

test('empty stock catalogue has no fabricated companies', async ({ page }) => {
  await page.route('**/api/listings?kind=ALL', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.goto('/')
  await page.locator('.operations-panel > summary').click()
  const section = sectionOf(page)
  await expect(section.getByText('Katalog instrumentu jest pusty. Dodaj pierwszy instrument.')).toBeVisible()
  await expect(section.getByLabel('Wybierz instrument', { exact: true })).toHaveCount(0)
})
