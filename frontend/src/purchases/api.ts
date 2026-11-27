export type Account = { id: string; name: string; kind: string; currency: string }
export type Listing = {
  id: string; name: string; symbol: string; isin: string | null; mic: string; currency: string
  kind: string; account_ids?: string[]
}
export type Purchase = {
  id: string; account_id: string; listing_id: string; symbol: string; isin: string | null
  trade_date: string; quantity: string; unit_price: string; commission: string; currency: string
  revision: number; created_at: string; updated_at: string
}
export type Audit = {
  id: string; revision: number; kind: string; reason: string | null
  before: Record<string, string> | null; after: Record<string, string>; created_at: string
}

const labels: Record<string, string> = {
  trade_date: 'Data zakupu', quantity: 'Liczba jednostek', unit_price: 'Cena jednostki',
  commission: 'Prowizja', currency: 'Waluta', reason: 'Powód korekty',
  account_id: 'Rachunek instrumentu', listing_id: 'Instrument', expected_revision: 'Wersja zakupu',
  price: 'Cena wyceny', observed_on: 'Data wyceny',
  series: 'Seria obligacji', annual_rate: 'Oprocentowanie', margin: 'Marża',
  source_url: 'Dokument emisji', name: 'Nazwa rachunku', kind: 'Typ rachunku',
  symbol: 'Ticker', mic: 'Giełda (MIC)', isin: 'ISIN',
  value: 'Wartość obligacji', paid_interest: 'Wypłacone odsetki', purchase_revision: 'Wersja zakupu',
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(12000)
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new ApiError('Nie udało się połączyć. Dane formularza zostały zachowane. Możesz ponowić zapis.', 0)
  }
  let body
  try {
    body = await response.json()
  } catch {
    throw new ApiError('Nie udało się odczytać odpowiedzi. Dane formularza zostały zachowane. Możesz ponowić zapis.', 0)
  }
  if (!response.ok) {
    const message = typeof body.detail === 'string' ? body.detail : 'Nie udało się wykonać operacji.'
    const fields = Array.isArray(body.errors) ? body.errors.map((error: { field: string; message: string }) =>
      ((path === '/api/stocks' || path === '/api/securities') && error.field === 'name' ? 'Nazwa instrumentu' : labels[error.field] ?? 'Pole formularza') + ': ' + error.message,
    ).join(' ') : ''
    throw new ApiError([message, fields].filter(Boolean).join(' '), response.status)
  }
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase() ?? 'GET')) {
    window.dispatchEvent(new Event('financialtracker:updated'))
  }
  return body as T
}

export function formatDecimal(value: string, minDecimals = 0): string {
  const [whole, fraction = ''] = value.split('.')
  const digits = fraction.replace(/0+$/, '').padEnd(minDecimals, '0')
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0') + (digits ? ',' + digits : '')
}

export function formatDate(value: string): string {
  return value.split('-').reverse().join('.')
}

export function todayWarsaw(): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'Europe/Warsaw', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const get = (name: string) => parts.find((part) => part.type === name)!.value
  return get('year') + '-' + get('month') + '-' + get('day')
}
