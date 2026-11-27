// Read-only check of an explicitly synthetic cache inserted by isolated CI.
import assert from 'node:assert/strict'
const base = 'http://127.0.0.1:5173/api'
const get = async (path) => {
  const response = await fetch(base + path, { signal: AbortSignal.timeout(10000) })
  assert.ok(response.ok)
  return response.json()
}
const listing = (await get('/listings?kind=STOCK')).find((item) => item.symbol === 'SYN.TEST')
const account = (await get('/accounts')).find((item) => item.name === 'TEST - trwalosc akcji')
const result = await get(`/accounts/${account.id}/valuation?listing_id=${listing.id}`)
assert.equal(result.price.source, 'YAHOO')
assert.equal(result.price.provider_symbol, 'SYN.TEST.WA')
assert.equal(result.display.gain, '98.00')
assert.ok(result.price.quoted_at && result.price.recorded_at)
assert.equal(result.history[0].source, 'MANUAL')
console.log('PASS: synthetic Yahoo mapping, quote, timestamps and manual history persist')
