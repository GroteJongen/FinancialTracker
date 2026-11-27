import { request } from '../shared/api'

type Result = { updated: number; failed: number; remaining: number }
const pending = new Map<string, Promise<Result>>()

export function refreshFxRates(query: string, onlyMissing = false): Promise<Result> {
  const active = pending.get(query)
  if (active) return active
  const task = (async () => {
    let updated = 0
    let last: Result = { updated: 0, failed: 0, remaining: 0 }
    for (let batch = 0; batch < 20; batch++) {
      last = await request<Result>('/api/portfolio/fx/refresh?' + query + '&only_missing=' + (onlyMissing || batch > 0), { method: 'POST' })
      updated += last.updated
      // Failed or unavailable dates must not create an automatic retry loop.
      if (!last.remaining || last.failed || !last.updated) break
    }
    return { ...last, updated }
  })().finally(() => { pending.delete(query) })
  pending.set(query, task)
  return task
}
