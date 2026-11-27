import { expect, test } from './fixtures'
import type { Page } from '@playwright/test'

test.use({ actionTimeout: 10000 })
const sectionOf = (page: Page) => page.getByRole('region', { name: 'Instrumenty giełdowe', exact: true })

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

for (const [currency, kind] of [['PLN', 'STANDARD'], ['EUR', 'IKE'], ['USD', 'IKZE']]) {
  test(`registers stock and shows ${currency} position on ${kind} with correction audit`, async ({ page }) => {
    const section = await prepareCompany(page, currency)
    await section.getByRole('button', { name: 'Zapisz instrument', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu instrumentu' })).toContainText('Instrument został zapisany')
    await section.getByRole('button', { name: 'Dodaj rachunek instrumentu', exact: true }).click()
    await section.getByLabel('Nazwa rachunku instrumentu', { exact: true }).fill('TEST rachunek instrumentu ' + currency + Date.now())
    await section.getByLabel('Typ rachunku instrumentu', { exact: true }).selectOption(kind)
    await section.getByRole('button', { name: 'Zapisz rachunek instrumentu', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu instrumentu' })).toContainText('Rachunek inwestycyjny został zapisany')
    await section.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('10')
    await section.getByLabel(`Cena zakupu instrumentu (${currency})`, { exact: true }).fill('100')
    await section.getByLabel(`Prowizja zakupu instrumentu (${currency})`, { exact: true }).fill('2')
    await section.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-10-05')
    await section.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
    const card = (label: string) => section.locator('.stock-position-cards > div').filter({ has: page.getByText(label, { exact: true }) }).locator('dd')
    await expect(card('Koszt instrumentu')).toHaveText('1\u00a0002,00 ' + currency)
    await expect(card('Wartość instrumentu')).toHaveText('—')
    await section.getByLabel(`Cena wyceny instrumentu (${currency})`, { exact: true }).fill('110')
    await section.getByLabel('Data wyceny instrumentu', { exact: true }).fill('2026-10-06')
    await section.getByRole('button', { name: 'Zapisz cenę instrumentu', exact: true }).click()
    await expect(card('Zysk / strata instrumentu')).toHaveText('98,00 ' + currency)
    await expect(card('Wynik instrumentu (%)')).toHaveText('9,78%')
    await section.getByRole('button', { name: 'Popraw instrumenty', exact: true }).click()
    await section.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('9')
    await section.getByLabel('Powód korekty instrumentu', { exact: true }).fill('Syntetyczna korekta liczby instrumentu')
    await section.getByRole('button', { name: 'Zapisz korektę instrumentu', exact: true }).click()
    await expect(card('Zysk / strata instrumentu')).toHaveText('88,00 ' + currency)
    await section.getByRole('button', { name: 'Zmiany instrumentu', exact: true }).click()
    await expect(section.getByRole('region', { name: 'Historia zmian zakupu', exact: true })).toContainText('Syntetyczna korekta liczby instrumentu')
    const listingId = await section.getByLabel('Wybierz instrument', { exact: true }).inputValue()
    const accountId = await section.getByLabel('Rachunek instrumentu', { exact: true }).inputValue()
    await page.reload()
  await page.locator('.operations-panel > summary').click()
    await section.getByLabel('Wybierz instrument', { exact: true }).selectOption(listingId)
    await section.getByLabel('Rachunek instrumentu', { exact: true }).selectOption(accountId)
    await expect(card('Zysk / strata instrumentu')).toHaveText('88,00 ' + currency)
    await expect(page.getByRole('region', { name: 'Zakupy IUSQ', exact: true }).getByRole('row').filter({ hasText: '05.10.2026' })).toHaveCount(0)
  })
}

test('catalogue and fractional purchase retry after lost response do not duplicate data', async ({ page }) => {
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
  await section.getByLabel('Liczba jednostek instrumentu', { exact: true }).fill('0,125')
  await section.getByLabel('Cena zakupu instrumentu (PLN)', { exact: true }).fill('100')
  await section.getByLabel('Prowizja zakupu instrumentu (PLN)', { exact: true }).fill('0,10')
  await section.getByLabel('Data zakupu instrumentu', { exact: true }).fill('2026-10-08')
  first = true
  await page.route('**/api/accounts/*/purchases', async (route) => {
    if (first && route.request().method() === 'POST') { first = false; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await section.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await section.getByRole('button', { name: 'Zapisz zakup instrumentu', exact: true }).click()
  await expect(section.getByRole('status', { name: 'Wynik zapisu instrumentu' })).toContainText('Zakup instrumentu został zapisany')
  const listingId = await section.getByLabel('Wybierz instrument', { exact: true }).inputValue()
  const accountId = await section.getByLabel('Rachunek instrumentu', { exact: true }).inputValue()
  await page.reload()
  await page.locator('.operations-panel > summary').click()
  await section.getByLabel('Wybierz instrument', { exact: true }).selectOption(listingId)
  await section.getByLabel('Rachunek instrumentu', { exact: true }).selectOption(accountId)
  await expect(section.getByRole('row').filter({ hasText: '08.10.2026' })).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})

test('empty stock catalogue has no fabricated companies', async ({ page }) => {
  await page.route('**/api/listings?kind=ALL', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.goto('/')
  await page.locator('.operations-panel > summary').click()
  const section = sectionOf(page)
  await expect(section.getByText('Katalog instrumentu jest pusty. Dodaj pierwszy instrument.')).toBeVisible()
  await expect(section.getByLabel('Wybierz instrument', { exact: true })).toHaveCount(0)
})
