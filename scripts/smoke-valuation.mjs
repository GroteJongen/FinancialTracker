// Synthetic CI account only; execute after smoke-purchases.mjs.
import assert from 'node:assert/strict'
const root = 'http://127.0.0.1:8000/api/accounts/00000000-0000-4000-8000-000000000002'
async function json(path, options) {
  const response = await fetch(root + path, {
    ...options, signal: AbortSignal.timeout(10000),
    headers: { 'Content-Type': 'application/json' },
  })
  assert.ok(response.ok, 'Valuation API failed: ' + response.status)
  return response.json()
}
if (process.argv[2] === 'create') {
  const data = {
    listing_id: '00000000-0000-4000-8000-000000000004',
    request_id: '00000000-0000-4000-8000-000000000030',
    price: '110', observed_on: '2026-01-20', currency: 'EUR',
  }
  const first = await json('/prices', { method: 'POST', body: JSON.stringify(data) })
  const again = await json('/prices', { method: 'POST', body: JSON.stringify(data) })
  assert.equal(first.id, again.id)
}
const summary = await json('/valuation')
assert.equal(summary.status, 'priced')
assert.equal(summary.history.length, 1)
assert.equal(summary.price.source, 'MANUAL')
assert.equal(summary.display.cost, '25.13')
assert.equal(summary.display.market_value, '27.50')
assert.equal(summary.display.gain, '2.37')
console.log('PASS: private manual price and valuation persist')
