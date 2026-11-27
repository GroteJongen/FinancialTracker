// Read/write synthetic CI data only; uses pre-existing synthetic smoke accounts.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:5173/api'
async function json(path, options) {
  const response = await fetch(base + path, { ...options, signal: AbortSignal.timeout(10000), headers: { 'Content-Type': 'application/json' } })
  assert.ok(response.ok, 'Portfolio API failed: ' + response.status)
  return response.json()
}
const accounts = await json('/accounts')
const account = accounts.find((item) => item.name === 'TEST - trwalosc obligacji')
assert.ok(account)
const purchases = await json(`/accounts/${account.id}/bonds`)
if (process.argv[2] === 'create') {
  const body = JSON.stringify({ request_id: '00000000-0000-4000-8000-000000000061', purchase_revision: purchases[0].revision, value: '1100', paid_interest: '20', observed_on: '2026-11-20' })
  const first = await json(`/accounts/${account.id}/bonds/${purchases[0].id}/valuations`, { method: 'POST', body })
  assert.equal((await json(`/accounts/${account.id}/bonds/${purchases[0].id}/valuations`, { method: 'POST', body })).id, first.id)
}
const result = await json('/portfolio?scope=STANDARD')
assert.equal(result.totals.cost, '2001.00')
assert.equal(result.totals.value, '2200.00')
assert.equal(result.totals.paid_income, '20.00')
assert.equal(result.totals.gain, '219.00')
assert.equal(result.totals.complete, true)
assert.equal(result.totals.allocation_value.length, 2)
assert.equal(result.totals.allocation_value[0].percent, '50.00')
console.log('PASS: portfolio scope, allocation, bond valuation and paid interest persist')
