import { expect, test } from './fixtures'

async function selectAccount(page: import('@playwright/test').Page, name: string) {
  await page.goto('/')
  await page.getByLabel('Rachunek', { exact: true }).selectOption({ label: name })
  await expect(page.getByLabel('Cena wyceny (EUR)', { exact: true })).toBeEnabled()
}

async function buy(page: import('@playwright/test').Page, date: string, quantity = '10') {
  await page.getByLabel('Data zakupu', { exact: true }).fill(date)
  await page.getByLabel('Liczba jednostek', { exact: true }).fill(quantity)
  await page.getByLabel('Cena jednostki (EUR)', { exact: true }).fill('100')
  await page.getByLabel('Prowizja (EUR)', { exact: true }).fill('2')
  await page.getByRole('button', { name: 'Zapisz zakup', exact: true }).click()
  await expect(page.getByRole('status', { name: 'Wynik zapisu' })).toContainText('Zakup został zapisany')
  await expect(page.getByLabel('Cena wyceny (EUR)', { exact: true })).toBeEnabled()
}

async function price(page: import('@playwright/test').Page, value: string, date: string) {
  await page.getByLabel('Cena wyceny (EUR)', { exact: true }).fill(value)
  await page.getByLabel('Data wyceny', { exact: true }).fill(date)
  await page.getByRole('button', { name: 'Zapisz cenę', exact: true }).click()
}

function card(page: import('@playwright/test').Page, label: string) {
  return page.locator('.valuation-cards > div').filter({ has: page.getByText(label, { exact: true }) }).locator('dd')
}

test('manual quote values the position, survives reload, and recalculates a correction', async ({ page }) => {
  await selectAccount(page, 'TEST — wycena')
  await buy(page, '2026-01-10')
  await expect(page.getByText('Brak wyceny — wpisz cenę jednostki.')).toBeVisible()
  await expect(card(page, 'Wartość pozycji')).toHaveText('—')
  await price(page, '110,00', '2026-01-20')
  await expect(card(page, 'Koszt zakupów')).toHaveText('1 002,00 EUR')
  await expect(card(page, 'Wartość pozycji')).toHaveText('1 100,00 EUR')
  await expect(card(page, 'Zysk / strata')).toHaveText('98,00 EUR')
  await expect(card(page, 'Wynik procentowy')).toHaveText('9,78%')
  await page.reload()
  await page.getByLabel('Rachunek', { exact: true }).selectOption({ label: 'TEST — wycena' })
  await expect(card(page, 'Zysk / strata')).toHaveText('98,00 EUR')
  const row = page.getByRole('row').filter({ hasText: '10.01.2026' })
  await row.getByRole('button', { name: 'Popraw', exact: true }).click()
  await page.getByLabel('Liczba jednostek', { exact: true }).fill('9')
  await page.getByLabel('Powód korekty', { exact: true }).fill('Poprawiona liczba jednostek')
  await page.getByRole('button', { name: 'Zapisz korektę', exact: true }).click()
  await expect(card(page, 'Zysk / strata')).toHaveText('88,00 EUR')
  await page.getByText('Historia cen ręcznych', { exact: false }).click()
  await expect(page.getByRole('table', { name: 'Historia cen wyceny' })).toContainText('110,00')
})

test('rejects an old date and hides gain after a later purchase', async ({ page }) => {
  await selectAccount(page, 'TEST — daty')
  await buy(page, '2026-01-10')
  await price(page, '110', '2026-01-09')
  await expect(page.getByRole('alert')).toContainText('Data wyceny musi być pomiędzy')
  await price(page, '110', '2026-01-20')
  await expect(card(page, 'Zysk / strata')).toHaveText('98,00 EUR')
  await buy(page, '2026-01-21')
  await expect(page.getByText('Cena wymaga aktualizacji:', { exact: false })).toBeVisible()
  await expect(card(page, 'Zysk / strata')).toHaveText('—')
  await expect(card(page, 'Wartość pozycji')).toHaveText('—')
  await price(page, '120', '2026-01-21')
  await expect(card(page, 'Zysk / strata')).toHaveText('396,00 EUR')
})

test('lost price response retries without adding a second history entry', async ({ page }) => {
  await selectAccount(page, 'TEST — ponowienie')
  await buy(page, '2026-01-10', '0,125')
  let first = true
  await page.route('**/api/accounts/*/prices', async (route) => {
    if (first) {
      first = false
      await route.fetch()
      await route.abort('failed')
    } else {
      await route.continue()
    }
  })
  await price(page, '104', '2026-01-20')
  await expect(page.getByRole('alert')).toContainText('Dane formularza zostały zachowane')
  await page.getByRole('button', { name: 'Zapisz cenę', exact: true }).click()
  await expect(page.getByText('Historia cen ręcznych (1)', { exact: true })).toBeVisible()
  await expect(card(page, 'Zysk / strata')).toHaveText('-1,50 EUR')
})

test('valuation cards and form fit mobile width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Wycena IUSQ', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
