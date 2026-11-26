import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function createAccount(page: Page, name: string, kind = 'STANDARD') {
  await page.goto('/')
  const section = page.getByRole('region', { name: 'Obligacje skarbowe', exact: true })
  await section.getByRole('button', { name: 'Dodaj rachunek obligacji', exact: true }).click()
  await section.getByLabel('Nazwa rachunku', { exact: true }).fill(name)
  await section.getByLabel('Typ rachunku', { exact: true }).selectOption(kind)
  await section.getByRole('button', { name: 'Zapisz rachunek obligacji', exact: true }).click()
  await expect(section.getByLabel('Rachunek obligacji', { exact: true })).toHaveValue(/.+/)
  await expect(section.getByText('Rachunek: ' + name + '. Wpisz dane z potwierdzenia zakupu.')).toBeVisible()
  return section
}

for (const [type, series, kind] of [['TOS', 'TOS1129', 'STANDARD'], ['COI', 'COI1130', 'IKE_BONDS'], ['EDO', 'EDO1136', 'IKZE']]) {
  test(`adds ${type} on ${kind}, corrects with audit and preserves data`, async ({ page }) => {
    const name = `TEST obligacje ${type} ${Date.now()}`
    const section = await createAccount(page, name, kind)
    await section.getByLabel('Rodzaj obligacji', { exact: true }).selectOption(type)
    await section.getByLabel('Seria obligacji', { exact: true }).fill(series)
    await section.getByLabel('Data zakupu obligacji', { exact: true }).fill('2026-11-10')
    await section.getByLabel('Liczba obligacji', { exact: true }).fill('10')
    await section.getByLabel('Cena jednej obligacji (PLN)', { exact: true }).fill('99,90')
    await section.getByLabel('Oprocentowanie (%) — opcjonalnie', { exact: true }).fill('4,4')
    if (type !== 'TOS') await section.getByLabel('Marża ponad inflację (%) — opcjonalnie').fill('1,5')
    await section.getByRole('button', { name: 'Zapisz zakup obligacji', exact: true }).click()
    await expect(section.getByRole('status', { name: 'Wynik zapisu obligacji' })).toContainText('Zakup obligacji został zapisany.')
    let row = section.getByRole('row').filter({ hasText: series })
    await expect(row).toContainText('999,00')
    await row.getByRole('button', { name: 'Popraw obligacje', exact: true }).click()
    await section.getByLabel('Liczba obligacji', { exact: true }).fill('12')
    await section.getByLabel('Powód korekty obligacji', { exact: true }).fill('Korekta liczby sztuk z potwierdzenia')
    await section.getByRole('button', { name: 'Zapisz korektę obligacji', exact: true }).click()
    await expect(row).toContainText('1\u00a0198,80')
    await row.getByRole('button', { name: 'Zmiany obligacji', exact: true }).click()
    const history = section.getByRole('region', { name: 'Historia zmian obligacji' })
    await expect(history).toContainText('Korekta liczby sztuk z potwierdzenia')
    await expect(history).toContainText('10 → 12')
    const accountId = await section.getByLabel('Rachunek obligacji', { exact: true }).inputValue()
    await page.reload()
    await section.getByLabel('Rachunek obligacji', { exact: true }).selectOption(accountId)
    row = section.getByRole('row').filter({ hasText: series })
    await expect(row).toContainText('1\u00a0198,80')
    await expect(section).toContainText('Koszt zakupu nie jest bieżącą wyceną')
  })
}

test('bond retry after lost response does not duplicate purchase; invalid quantity keeps form', async ({ page }) => {
  const section = await createAccount(page, 'TEST ponowienie obligacji ' + Date.now())
  await section.getByLabel('Seria obligacji', { exact: true }).fill('TOS1129')
  await section.getByLabel('Data zakupu obligacji', { exact: true }).fill('2026-11-10')
  await section.getByLabel('Liczba obligacji', { exact: true }).fill('0,5')
  await section.getByRole('button', { name: 'Zapisz zakup obligacji', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('całkowitą liczbę')
  await expect(section.getByLabel('Liczba obligacji', { exact: true })).toHaveValue('0,5')
  await section.getByLabel('Liczba obligacji', { exact: true }).fill('2')
  let first = true
  await page.route('**/api/accounts/*/bonds', async (route) => {
    if (route.request().method() === 'POST' && first) {
      first = false
      await route.fetch()
      await route.abort('failed')
    } else await route.continue()
  })
  await section.getByRole('button', { name: 'Zapisz zakup obligacji', exact: true }).click()
  await expect(section.getByRole('alert')).toContainText('Dane formularza zostaly zachowane')
  await section.getByRole('button', { name: 'Zapisz zakup obligacji', exact: true }).click()
  await expect(section.getByRole('status', { name: 'Wynik zapisu obligacji' })).toContainText('Zakup obligacji został zapisany.')
  await expect(section.getByRole('row').filter({ hasText: 'TOS1129' })).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
