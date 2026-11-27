import { request } from '../shared/api'

type Refresh = { updated: number; failed: number; cooldown_seconds: number }
let pending: Promise<Refresh> | null = null

export function refreshMarket() {
  if (!pending) {
    pending = request<Refresh>('/api/market-prices/refresh', { method: 'POST' })
      .then((result) => {
        window.dispatchEvent(new Event('financialtracker:quotes-updated'))
        return result
      }).finally(() => { pending = null })
  }
  return pending
}

export function quoteTime(value: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    timeZone: 'Europe/Warsaw', dateStyle: 'short', timeStyle: 'medium',
  }).format(new Date(value))
}
