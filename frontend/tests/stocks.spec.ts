import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

test.use({ actionTimeout: 10000 })
const sectionOf = (page: Page) => page.getByRole('region', { name: 'Akcje', exact: true })

async function prepareCompany(page: Page, currency: string) {
  await page.goto('/')
  const section = sectionOf(page)
  await section.getByRole('button', { name: 'Dodaj spółkę', exact: true }).click()
  const marker = Date.now().toString()
  await section.getByLabel('Nazwa spółki', { exact: true }).fill('TEST akcje ' + currency + ' ' + marker)
  await section.getByLabel('Ticker akcji', { exact: true }).fill('SYN' + currency + marker)
  await section.getByLabel('Giełda akcji (MIC)', { exact: true }).fill('XWAR')
  await section.getByLabel('Waluta notowania akcji', { exact: true }).selectOption(currency)
  return section
}

for (const [currency, kind] of [['PLN', 'STANDARD'], ['EUR', 'IKE'], ['USD', 'IKZE']]) {
  test(`registers stock and shows ${currency} position on ${kind} with correction audit`, async ({ page }) => {
    const section = await prepareCompany(page, currency)
    await section.getByRole('button', { name: 'Zapisz spółkę', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu akcji' })).toContainText('Spółka została zapisana')
    await section.getByRole('button', { name: 'Dodaj rachunek akcji', exact: true }).click()
    await section.getByLabel('Nazwa rachunku akcji', { exact: true }).fill('TEST rachunek akcji ' + currency + Date.now())
    await section.getByLabel('Typ rachunku akcji', { exact: true }).selectOption(kind)
    await section.getByRole('button', { name: 'Zapisz rachunek akcji', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Zapis katalogu akcji' })).toContainText('Rachunek inwestycyjny został zapisany')
    await section.getByLabel('Liczba akcji', { exact: true }).fill('10')
    await section.getByLabel(`Cena zakupu akcji (${currency})`, { exact: true }).fill('100')
    await section.getByLabel(`Prowizja zakupu akcji (${currency})`, { exact: true }).fill('2')
    await section.getByLabel('Data zakupu akcji', { exact: true }).fill('2026-10-05')
    await section.getByRole('button', { name: 'Zapisz zakup akcji', exact: true }).click()
    const card = (label: string) => section.locator('.stock-position-cards > div').filter({ hasText: label }).locator('dd')
    await expect(card('Koszt akcji')).toHaveText('1\u00a0002,00 ' + currency)
    await expect(card('Wartość akcji')).toHaveText('—')
    await section.getByLabel(`Cena wyceny akcji (${currency})`, { exact: true }).fill('110')
    await section.getByLabel('Data wyceny akcji', { exact: true }).fill('2026-10-06')
    await section.getByRole('button', { name: 'Zapisz cenę akcji', exact: true }).click()
    await expect(card('Zysk / strata akcji')).toHaveText('98,00 ' + currency)
    await expect(card('Wynik akcji (%)')).toHaveText('9,78%')
    await section.getByRole('button', { name: 'Popraw akcje', exact: true }).click()
    await section.getByLabel('Liczba akcji', { exact: true }).fill('9')
    await section.getByLabel('Powód korekty akcji', { exact: true }).fill('Syntetyczna korekta liczby akcji')
    await section.getByRole('button', { name: 'Zapisz korektę akcji', exact: true }).click()
    await expect(card('Zysk / strata akcji')).toHaveText('88,00 ' + currency)
    await section.getByRole('button', { name: 'Zmiany akcji', exact: true }).click()
    await expect(section.getByRole('region', { name: 'Historia zmian zakupu', exact: true })).toContainText('Syntetyczna korekta liczby akcji')
    const listingId = await section.getByLabel('Podgląd akcji', { exact: true }).inputValue()
    const accountId = await section.getByLabel('Rachunek akcji', { exact: true }).inputValue()
    await page.reload()
    await section.getByLabel('Podgląd akcji', { exact: true }).selectOption(listingId)
    await section.getByLabel('Rachunek akcji', { exact: true }).selectOption(accountId)
    await expect(card('Zysk / strata akcji')).toHaveText('88,00 ' + currency)
    await expect(page.getByRole('region', { name: 'Zakupy IUSQ', exact: true }).getByRole('row').filter({ hasText: '05.10.2026' })).toHaveCount(0)
  })
}

test('catalogue and fractional purchase retry after lost response do not duplicate data', async ({ page }) => {
  const section = await prepareCompany(page, 'PLN')
  let first = true
  await page.route('**/api/stocks', async (route) => {
    if (first) { first = false; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await section.getByRole('button', { name: 'Zapisz spółkę', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await section.getByRole('button', { name: 'Zapisz spółkę', exact: true }).click()
  await expect(section.getByRole('status', { name: 'Zapis katalogu akcji' })).toContainText('Spółka została zapisana')
  await section.getByLabel('Liczba akcji', { exact: true }).fill('0,125')
  await section.getByLabel('Cena zakupu akcji (PLN)', { exact: true }).fill('100')
  await section.getByLabel('Prowizja zakupu akcji (PLN)', { exact: true }).fill('0,10')
  await section.getByLabel('Data zakupu akcji', { exact: true }).fill('2026-10-08')
  first = true
  await page.route('**/api/accounts/*/purchases', async (route) => {
    if (first && route.request().method() === 'POST') { first = false; await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await section.getByRole('button', { name: 'Zapisz zakup akcji', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await section.getByRole('button', { name: 'Zapisz zakup akcji', exact: true }).click()
  await expect(section.getByRole('status', { name: 'Wynik zapisu akcji' })).toContainText('Zakup akcji został zapisany')
  const listingId = await section.getByLabel('Podgląd akcji', { exact: true }).inputValue()
  const accountId = await section.getByLabel('Rachunek akcji', { exact: true }).inputValue()
  await page.reload()
  await section.getByLabel('Podgląd akcji', { exact: true }).selectOption(listingId)
  await section.getByLabel('Rachunek akcji', { exact: true }).selectOption(accountId)
  await expect(section.getByRole('row').filter({ hasText: '08.10.2026' })).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})

test('empty stock catalogue has no fabricated companies', async ({ page }) => {
  await page.route('**/api/listings?kind=STOCK', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.goto('/')
  const section = sectionOf(page)
  await expect(section.getByText('Katalog akcji jest pusty. Dodaj pierwszą spółkę.')).toBeVisible()
  await expect(section.getByLabel('Podgląd akcji', { exact: true })).toHaveCount(0)
})
