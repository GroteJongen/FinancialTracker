// Synthetic CI accounts only. Never runs on application startup.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:5173/api'
const json = async (path, options) => {
  const response = await fetch(base + path, { ...options, headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(10000) })
  assert.ok(response.ok)
  return response.json()
}
const accounts = await json('/accounts')
const ids = ['TEST - trwalosc obligacji', 'TEST - trwalosc akcji'].map((name) => accounts.find((row) => row.name === name)?.id)
assert.ok(ids.every(Boolean))
const name = 'TEST - trwalosc grupy portfela'
if (process.argv[2] === 'create') {
  const options = { method: 'POST', body: JSON.stringify({ name, account_ids: ids }) }
  const group = await json('/portfolios', options)
  assert.equal((await json('/portfolios', options)).id, group.id)
}
const group = (await json('/portfolios')).find((row) => row.name === name)
assert.ok(group)
assert.deepEqual([...group.account_ids].sort(), [...ids].sort())
const snapshot = await json('/portfolio?portfolio_id=' + group.id)
assert.equal(snapshot.totals.cost, '2001.00')
assert.equal(snapshot.totals.value, '2200.00')
assert.equal(snapshot.totals.gain, '219.00')
assert.equal(snapshot.position_count, 2)
console.log('PASS: custom portfolio membership and mixed-asset totals persist without duplicating accounts')
