// Run against local synthetic data only. No filesystem or database mutation.
const unavailable = process.argv[2] === 'unavailable'
const base = 'http://127.0.0.1:8000'
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
let lastError
for (let attempt = 0; attempt < 40; attempt++) {
  try {
    const live = await fetch(`${base}/api/health/live`, { signal: AbortSignal.timeout(5000) })
    if (live.status !== 200) throw new Error('Backend is not alive')
    const ready = await fetch(`${base}/api/health/ready`, { signal: AbortSignal.timeout(10000) })
    if (unavailable) {
      if (ready.status !== 503) throw new Error('Readiness must fail during database outage')
      const data = await ready.json()
      if (JSON.stringify(data) !== '{"status":"unavailable"}') throw new Error('Unexpected error')
    } else {
      if (ready.status !== 200) throw new Error('Database is not ready')
      const response = await fetch('http://127.0.0.1:5173/api/accounts', {
        signal: AbortSignal.timeout(5000),
      })
      const accounts = await response.json()
      const demo = accounts.filter((item) => item.id === '00000000-0000-4000-8000-000000000002')
      if (response.status !== 200 || demo.length !== 1 || demo[0].kind !== 'IKE') {
        throw new Error('Seed or persistence check failed')
      }
      const page = await fetch('http://127.0.0.1:5173', { signal: AbortSignal.timeout(5000) })
      if (page.status !== 200 || !(await page.text()).includes('FinancialTracker')) {
        throw new Error('Frontend is unavailable')
      }
    }
    console.log(unavailable ? 'PASS: database outage is sanitized' : 'PASS: full stack and persisted account')
    process.exit(0)
  } catch (error) {
    lastError = error
    await sleep(1000)
  }
}
console.error(lastError)
process.exit(1)
