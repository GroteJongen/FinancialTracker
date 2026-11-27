import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from '../shared/api'
import type { Listing, Purchase } from '../shared/api'
import AuditHistory from '../shared/AuditHistory'

type Correction = { trade_date: string; quantity: string; unit_price: string; commission: string; reason: string }

export default function PurchaseHistory({ accountId, listing, onBusy, disabled }: {
  accountId: string; listing: Listing; onBusy: (value: boolean) => void; disabled: boolean
}) {
  const [refresh, setRefresh] = useState(0)
  const [loaded, setLoaded] = useState<{ version: number; purchases: Purchase[] } | null>(null)
  const [loadError, setLoadError] = useState('')
  const [editing, setEditing] = useState<Purchase | null>(null)
  const [form, setForm] = useState<Correction>({ trade_date: '', quantity: '', unit_price: '', commission: '', reason: '' })
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const [auditId, setAuditId] = useState<string | null>(null)
  const current = loaded?.version === refresh ? loaded : null
  const blocked = saving || disabled || !current

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    void request<Purchase[]>(`/api/accounts/${accountId}/purchases`, { signal: controller.signal })
      .then((purchases) => { if (active) { setLoaded({ version: refresh, purchases: purchases.filter((item) => item.listing_id === listing.id) }); setLoadError('') } })
      .catch(() => { if (active) setLoadError('Nie udało się pobrać historii zakupów instrumentu.') })
    return () => { active = false; controller.abort() }
  }, [accountId, listing.id, refresh])

  function edit(item: Purchase) {
    setEditing(item)
    setForm({ trade_date: item.trade_date, quantity: item.quantity, unit_price: item.unit_price, commission: item.commission, reason: '' })
    setMessage(null)
  }
  function field(key: keyof Correction, value: string) { setForm((previous) => ({ ...previous, [key]: value })) }
  async function save(event: FormEvent) {
    event.preventDefault()
    if (savingRef.current || disabled || !current || !editing) return
    savingRef.current = true; setSaving(true); onBusy(true); setMessage(null)
    try {
      await request(`/api/accounts/${accountId}/purchases/${editing.id}`, { method: 'PUT', body: JSON.stringify({
        listing_id: listing.id, currency: listing.currency, trade_date: form.trade_date,
        quantity: form.quantity.trim().replace(',', '.'), unit_price: form.unit_price.trim().replace(',', '.'),
        commission: form.commission.trim().replace(',', '.'), reason: form.reason.trim(), expected_revision: editing.revision,
      }) })
      setEditing(null); setMessage({ text: 'Korekta instrumentu została zapisana.', error: false }); setRefresh((value) => value + 1)
    } catch (failure) {
      setMessage({ text: failure instanceof Error ? failure.message : 'Nie udało się zapisać korekty.', error: true })
      if (failure instanceof ApiError && failure.status === 409) setRefresh((value) => value + 1)
    } finally { savingRef.current = false; setSaving(false); onBusy(false) }
  }

  return <section className="purchase-panel" aria-label="Historia zakupów instrumentu" aria-busy={!current}>
    <div className="history-heading"><h3>Historia zakupów instrumentu</h3></div>
    {!current && !loadError && <p role="status">Pobieranie historii zakupów instrumentu…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt historii</button></div>}
    {current?.purchases.length === 0 && <p className="empty-purchases">Brak zakupów tego instrumentu na wybranym rachunku.</p>}
    <div className="purchase-table-scroll"><table className="purchase-table"><caption className="sr-only">Zakupy instrumentu {listing.symbol}</caption>
      <thead><tr><th>Data</th><th>Liczba jednostek</th><th>Cena ({listing.currency})</th><th>Prowizja ({listing.currency})</th><th>Działania</th></tr></thead>
      <tbody>{current?.purchases.map((item) => <tr key={item.id}><td>{formatDate(item.trade_date)}</td><td>{formatDecimal(item.quantity)}</td>
        <td>{formatDecimal(item.unit_price, 2)}</td><td>{formatDecimal(item.commission, 2)}</td><td className="row-actions">
          <button className="text-button" type="button" disabled={blocked} onClick={() => edit(item)}>Popraw instrument</button>
          <button className="text-button" type="button" disabled={blocked} aria-expanded={auditId === item.id} onClick={() => setAuditId((previous) => previous === item.id ? null : item.id)}>Zmiany instrumentu</button>
        </td></tr>)}</tbody></table></div>
    {editing && <form aria-label="Korekta zakupu instrumentu" noValidate onSubmit={(event) => { void save(event) }}>
      <h4>Popraw zakup instrumentu</h4>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <label htmlFor="history-trade-date">Data zakupu instrumentu<input id="history-trade-date" type="date" required max={todayWarsaw()} value={form.trade_date} onChange={(event) => field('trade_date', event.target.value)} /></label>
        <label htmlFor="history-quantity">Liczba jednostek instrumentu<input id="history-quantity" inputMode="decimal" required value={form.quantity} onChange={(event) => field('quantity', event.target.value)} /></label>
        <label htmlFor="history-unit-price">Cena zakupu instrumentu ({listing.currency})<input id="history-unit-price" inputMode="decimal" required value={form.unit_price} onChange={(event) => field('unit_price', event.target.value)} /></label>
        <label htmlFor="history-commission">Prowizja zakupu instrumentu ({listing.currency})<input id="history-commission" inputMode="decimal" required value={form.commission} onChange={(event) => field('commission', event.target.value)} /></label>
        <label className="reason-field" htmlFor="history-reason">Powód korekty instrumentu<textarea id="history-reason" required maxLength={500} value={form.reason} onChange={(event) => field('reason', event.target.value)} /></label>
      </div><div className="form-actions"><button className="primary-button" type="submit">Zapisz korektę instrumentu</button>
        <button className="secondary-button" type="button" onClick={() => { setEditing(null); setMessage(null) }}>Anuluj korektę instrumentu</button>
      </div></fieldset>
    </form>}
    {message && <p role={message.error ? 'alert' : 'status'} aria-label="Wynik zapisu instrumentu" className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}>{message.text}</p>}
    {auditId && <AuditHistory key={auditId + ':' + current?.purchases.find((item) => item.id === auditId)?.revision} accountId={accountId} purchaseId={auditId} currency={listing.currency} />}
  </section>
}
