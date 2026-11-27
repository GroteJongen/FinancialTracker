import { useEffect, useState } from 'react'
import { formatDate, formatDecimal, request } from './api'
import type { Audit } from './api'

const fields = (currency: string) => [
  ['trade_date', 'Data zakupu'], ['quantity', 'Liczba jednostek'],
  ['unit_price', 'Cena jednostki (' + currency + ')'], ['commission', 'Prowizja (' + currency + ')'],
]

function value(key: string, text: string) {
  return key === 'trade_date' ? formatDate(text) : formatDecimal(text)
}

export default function AuditHistory({ accountId, purchaseId, currency = 'EUR' }: {
  accountId: string; purchaseId: string; currency?: string
}) {
  const [events, setEvents] = useState<Audit[] | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void request<Audit[]>(`/api/accounts/${accountId}/purchases/${purchaseId}/audit`, {
      signal: controller.signal,
    }).then((result) => { if (active) { setEvents(result); setError('') } })
      .catch(() => { if (active) setError('Nie udało się pobrać historii zmian.') })
    return () => { active = false; controller.abort() }
  }, [accountId, purchaseId, retry])

  return <section className="audit-history" aria-label="Historia zmian zakupu">
    <h3>Historia zmian zakupu</h3>
    {error ? <div role="alert"><p>{error}</p>
      <button type="button" onClick={() => setRetry((count) => count + 1)}>Ponów odczyt</button>
    </div> : events === null ? <p role="status">Pobieranie historii zmian…</p>
      : <ol>{events.map((event) => <li key={event.id}>
        <div className="audit-heading"><strong>{event.kind === 'CREATE' ? 'Dodano zakup' : 'Korekta zakupu'}</strong>
          <span>Wersja {event.revision} · {new Intl.DateTimeFormat('pl-PL', {
            timeZone: 'Europe/Warsaw', dateStyle: 'short', timeStyle: 'medium',
          }).format(new Date(event.created_at))}</span></div>
        {event.reason && <p className="audit-reason">Powód: {event.reason}</p>}
        <dl>{fields(currency).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>
          {event.before && <><span>{value(key, event.before[key])}</span><span aria-label="zmieniono na"> → </span></>}
          <strong>{value(key, event.after[key])}</strong>
        </dd></div>)}</dl>
      </li>)}</ol>}
  </section>
}
