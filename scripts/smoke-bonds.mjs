// Synthetic CI data only. Never run against a user's portfolio.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:5173/api'
async function json(path, options) {
  const response = await fetch(base + path, {
    ...options, signal: AbortSignal.timeout(10000), headers: { 'Content-Type': 'application/json' },
  })
  assert.ok(response.ok, 'Bond API failed: ' + response.status)
  return response.json()
}
let accounts = await json('/accounts')
let account = accounts.find((item) => item.name === 'TEST - trwalosc obligacji')
if (process.argv[2] === 'create') {
  account = await json('/bond-accounts', { method: 'POST', body: JSON.stringify({
    name: 'TEST - trwalosc obligacji', kind: 'STANDARD',
  }) })
  const body = JSON.stringify({
    request_id: '00000000-0000-4000-8000-000000000041', series: 'TOS1129',
    trade_date: '2026-11-10', quantity: 10, unit_price: '99.90', annual_rate: '4.4',
  })
  const first = await json(`/accounts/${account.id}/bonds`, { method: 'POST', body })
  const again = await json(`/accounts/${account.id}/bonds`, { method: 'POST', body })
  assert.equal(first.id, again.id)
}
assert.ok(account)
const purchases = await json(`/accounts/${account.id}/bonds`)
assert.equal(purchases.length, 1)
assert.equal(purchases[0].cost, '999.00')
assert.equal(purchases[0].terms_status, 'MANUAL_UNVERIFIED')
const history = await json(`/accounts/${account.id}/bonds/${purchases[0].id}/audit`)
assert.equal(history.length, 1)
assert.equal(history[0].after.series, 'TOS1129')
console.log('PASS: bond account, purchase, issue snapshot and audit persist')
