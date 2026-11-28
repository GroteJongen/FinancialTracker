import { test as base, expect } from '@playwright/test'

// UI acceptance tests never fetch real market prices into their synthetic ledger.
export const test = base.extend<{ marketNetwork: void }>({
  marketNetwork: [async ({ page }, use) => {
    await page.route('**/api/market-prices/refresh', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ updated: 0, failed: 0, cooldown_seconds: 300 }),
    }))
    await page.route('**/api/portfolio/fx/refresh?*', (route) => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify({ updated: 0, failed: 0, remaining: 0 }),
    }))
    await page.route('**/api/bonds/refresh?*', (route) => route.fulfill({ json: { updated: 0, failed: 0, remaining: 0 } }))
    await use()
  }, { auto: true }],
})
export { expect }
