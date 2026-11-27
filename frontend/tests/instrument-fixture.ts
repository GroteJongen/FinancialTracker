import type { Page } from '@playwright/test'

export const iusq = '00000000-0000-4000-8000-000000000004'
const accounts = new WeakMap<Page, string>()

export async function iusqAccount(page: Page, name = 'TEST wspólny ETF') {
  let account = accounts.get(page)
  if (!account) {
    const response = await page.request.post('/api/investment-accounts', { data: { name: name + ' ' + crypto.randomUUID(), kind: 'STANDARD', currency: 'EUR' } })
    if (!response.ok()) throw new Error('Synthetic account creation failed')
    account = (await response.json() as { id: string }).id
    accounts.set(page, account)
  }
  return account
}

export async function openIusq(page: Page, name?: string) {
  const account = await iusqAccount(page, name)
  await page.goto('/')
  await page.locator('.operations-panel > summary').click()
  await page.getByLabel('Wybierz instrument', { exact: true }).selectOption(iusq)
  await page.getByLabel('Rachunek instrumentu', { exact: true }).selectOption(account)
}
