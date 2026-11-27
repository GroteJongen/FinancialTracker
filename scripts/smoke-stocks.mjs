// Explicit synthetic CI data only.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:5173/api'
async function json(path, options) {
  const response = await fetch(base + path, { ...options, signal: AbortSignal.timeout(10000), headers: { 'Content-Type': 'application/json' } })
  assert.ok(response.ok, 'Stock API failed: ' + response.status)
  return response.json()
}
let stocks = await json('/listings?kind=STOCK')
let accounts = await json('/accounts')
let listing = stocks.find((item) => item.symbol === 'SYN.TEST')
let account = accounts.find((item) => item.name === 'TEST - trwalosc akcji')
if (process.argv[2] === 'create') {
  listing = await json('/stocks', { method: 'POST', body: JSON.stringify({ name: 'Spolka syntetyczna CI', symbol: 'SYN.TEST', mic: 'XWAR', currency: 'PLN' }) })
  account = await json('/investment-accounts', { method: 'POST', body: JSON.stringify({ name: 'TEST - trwalosc akcji', kind: 'STANDARD', currency: 'PLN' }) })
  const body = JSON.stringify({ listing_id: listing.id, request_id: '00000000-0000-4000-8000-000000000051', trade_date: '2026-10-05', quantity: '10', unit_price: '100', commission: '2', currency: 'PLN' })
  const first = await json(`/accounts/${account.id}/purchases`, { method: 'POST', body })
  assert.equal((await json(`/accounts/${account.id}/purchases`, { method: 'POST', body })).id, first.id)
  await json(`/accounts/${account.id}/prices`, { method: 'POST', body: JSON.stringify({ listing_id: listing.id, request_id: '00000000-0000-4000-8000-000000000052', observed_on: '2026-10-06', price: '110', currency: 'PLN' }) })
}
assert.ok(account && listing)
const summary = await json(`/accounts/${account.id}/valuation?listing_id=${listing.id}`)
assert.equal(summary.display.gain, '98.00')
assert.equal(summary.display.gain_percent, '9.78')
assert.equal(summary.currency, 'PLN')
const purchases = await json(`/accounts/${account.id}/purchases`)
assert.equal(purchases.length, 1)
const audit = await json(`/accounts/${account.id}/purchases/${purchases[0].id}/audit`)
assert.equal(audit.length, 1)
assert.equal((await json('/listings')).length, 1)
console.log('PASS: stock catalogue, purchase, manual price, result and audit persist')
