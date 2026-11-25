// Mutates only the synthetic CI account; not a normal application startup task.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:8000/api/accounts/00000000-0000-4000-8000-000000000002/purchases'
async function json(path, options) {
  const response = await fetch(path, {
    ...options, signal: AbortSignal.timeout(10000),
    headers: { 'Content-Type': 'application/json' },
  })
  assert.ok(response.ok, 'Purchase API failed: ' + response.status)
  return response.json()
}
const body = {
  listing_id: '00000000-0000-4000-8000-000000000004',
  request_id: '00000000-0000-4000-8000-000000000005',
  trade_date: '2026-01-04', quantity: '0.125', unit_price: '100.12345678',
  commission: '0.10', currency: 'EUR',
}
if (process.argv[2] === 'create') {
  const created = await json(base, { method: 'POST', body: JSON.stringify(body) })
  const retried = await json(base, { method: 'POST', body: JSON.stringify(body) })
  assert.equal(created.id, retried.id)
  const { request_id: ignored, ...fields } = body
  const corrected = await json(base + '/' + created.id, {
    method: 'PUT',
    body: JSON.stringify({ ...fields, quantity: '0.25', expected_revision: 1, reason: 'Test migracji i trwałości' }),
  })
  assert.equal(corrected.revision, 2)
}
const rows = await json(base)
const purchase = rows.find(item => item.trade_date === body.trade_date)
assert.ok(purchase)
assert.equal(purchase.quantity, '0.25000000')
assert.equal(purchase.unit_price, '100.12345678')
assert.equal(purchase.revision, 2)
const events = await json(base + '/' + purchase.id + '/audit')
assert.equal(events.length, 2)
assert.equal(events[0].after.quantity, '0.12500000')
assert.equal(events[1].before.quantity, '0.12500000')
assert.equal(events[1].after.quantity, '0.25000000')
console.log('PASS: purchase, correction and audit persisted')
