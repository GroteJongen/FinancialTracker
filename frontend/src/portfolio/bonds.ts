import { request } from '../shared/api'

type Result = { updated: number; failed: number; remaining: number }
const pending = new Map<string, Promise<Result>>()
export function refreshBondData(query: string): Promise<Result> {
  const active = pending.get(query)
  if (active) return active
  const task = (async () => {
    let updated = 0
    let last: Result = { updated: 0, failed: 0, remaining: 0 }
    for (let batch = 0; batch < 10; batch++) {
      last = await request<Result>('/api/bonds/refresh?' + query, { method: 'POST' })
      updated += last.updated
      if (!last.remaining || last.failed || !last.updated) break
    }
    return { ...last, updated }
  })().finally(() => { pending.delete(query) })
  pending.set(query, task)
  return task
}
