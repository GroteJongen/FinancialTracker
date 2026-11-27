import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { request } from '../shared/api'
import { refreshMarket } from './market'

export default function YahooMapping({ listingId, label, current }: {
  listingId: string; label: string; current: string | null
}) {
  const [symbol, setSymbol] = useState(current ?? '')
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const [message, setMessage] = useState('')
  async function save(event: FormEvent | null, disable = false) {
    event?.preventDefault()
    if (lock.current) return
    lock.current = true; setBusy(true); setMessage('')
    try {
      await request(`/api/listings/${listingId}/yahoo`, {
        method: disable ? 'DELETE' : 'PUT',
        ...(disable ? {} : { body: JSON.stringify({ symbol: symbol.trim().toUpperCase() }) }),
      })
      window.dispatchEvent(new Event('financialtracker:quotes-updated'))
      if (disable) { setSymbol(''); setMessage('Wylaczono Yahoo. Wycena korzysta z cen recznych.') }
      else {
        const result = await refreshMarket()
        setMessage(result.failed ? 'Zapisano symbol, ale pobranie nie powiodlo sie. Sprawdz symbol, gielde i walute; Yahoo moze tez ograniczac dostep.' : 'Zapisano symbol. Kursy sa pobierane najwyzej raz na 5 minut.')
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Nie udalo sie zapisac symbolu.') }
    finally { lock.current = false; setBusy(false) }
  }
  return <form className="yahoo-mapping" aria-label={'Yahoo: ' + label} onSubmit={(event) => { void save(event) }}>
    <fieldset disabled={busy}><legend>{label}</legend>
      <label htmlFor={'yahoo-' + listingId}>Symbol Yahoo Finance
        <input id={'yahoo-' + listingId} value={symbol} maxLength={30} placeholder="np. IUSQ.DE, AAPL, PKO.WA"
          onChange={(event) => setSymbol(event.target.value)} required /></label>
      <div className="form-actions"><button type="submit" className="secondary-button">Zapisz symbol Yahoo</button>
        {current && <button type="button" className="text-button" onClick={() => { void save(null, true) }}>Wylacz Yahoo</button>}</div>
    </fieldset>{message && <p role="status">{message}</p>}
  </form>
}
