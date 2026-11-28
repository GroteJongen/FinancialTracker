import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from '../shared/api'
import type { Listing, Purchase } from '../shared/api'
import AuditHistory from '../shared/AuditHistory'

const searchable = (value: string) => value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pl-PL').replace(/\s/g, '').replace(/,/g, '.')

type Correction = { trade_date: string; quantity: string; unit_price: string; commission: string; reason: string }

export default function PurchaseHistory({ accountId, accountName, listing, onBusy, disabled }: {
  accountId: string; accountName: string; listing: Listing; onBusy: (value: boolean) => void; disabled: boolean
}) {
  const [refresh, setRefresh] = useState(0)
  const [query, setQuery] = useState('')
  const [order, setOrder] = useState<'desc' | 'asc'>('desc')
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

  const needle = searchable(query)
  const purchases = (current?.purchases ?? []).filter((item) => !needle || [
    listing.name, listing.symbol, listing.isin ?? '', accountName, item.trade_date, formatDate(item.trade_date),
    formatDecimal(item.quantity), formatDecimal(item.unit_price, 2), formatDecimal(item.commission, 2), formatDecimal(item.cost, 2),
  ].some((value) => searchable(value).includes(needle))).sort((left, right) => {
    const comparison = left.trade_date.localeCompare(right.trade_date) || left.created_at.localeCompare(right.created_at) || left.id.localeCompare(right.id)
    return order === 'asc' ? comparison : -comparison
  })

  return <div aria-busy={!current}>
    <div className="history-tools">
      <label className="history-search" htmlFor="history-search">Wyszukaj w historii
        <input id="history-search" type="search" placeholder="Data, liczba jednostek lub cena" value={query} disabled={saving || disabled} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <div className="history-sort"><label htmlFor="history-order">Sortuj według daty zakupu</label>
        <select id="history-order" value={order} disabled={saving || disabled} onChange={(event) => setOrder(event.target.value as 'desc' | 'asc')}>
          <option value="desc">Najnowsze pierwsze</option><option value="asc">Najstarsze pierwsze</option>
        </select>
      </div>
      {query && <button type="button" className="secondary-button" disabled={saving || disabled} onClick={() => setQuery('')}>Wyczyść wyszukiwanie</button>}
    </div>
    {current && <p className="form-hint" role="status" aria-label="Liczba zakupów" aria-live="polite">Znaleziono: {purchases.length} z {current.purchases.length} zakupów.</p>}
    {!current && !loadError && <p role="status">Pobieranie historii zakupów instrumentu…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt historii</button></div>}
    {current?.purchases.length === 0 && <p className="empty-purchases">Brak zakupów tego instrumentu na wybranym rachunku.</p>}
    {current && current.purchases.length > 0 && purchases.length === 0 && <p className="empty-purchases">Brak zakupów pasujących do wyszukiwania.</p>}
    <div className="purchase-table-scroll"><table className="purchase-table"><caption className="sr-only">Zakupy instrumentu {listing.symbol}</caption>
      <thead><tr><th>Data</th><th>Liczba jednostek</th><th>Cena ({listing.currency})</th><th>Prowizja ({listing.currency})</th><th>Koszt zakupu ({listing.currency})</th><th>Działania</th></tr></thead>
      <tbody>{purchases.map((item) => <tr key={item.id}><td>{formatDate(item.trade_date)}</td><td>{formatDecimal(item.quantity)}</td>
        <td>{formatDecimal(item.unit_price, 2)}</td><td>{formatDecimal(item.commission, 2)}</td><td>{formatDecimal(item.cost, 2)}</td><td className="row-actions">
          <button className="text-button" type="button" disabled={blocked} onClick={() => edit(item)}>Popraw instrument</button>
          <button className="text-button" type="button" disabled={blocked} aria-expanded={auditId === item.id} onClick={() => setAuditId((previous) => previous === item.id ? null : item.id)}>Zmiany instrumentu</button>
        </td></tr>)}</tbody></table></div>
    <p className="form-hint">Koszt zakupu obejmuje liczbę jednostek × cenę jednostki oraz prowizję.</p>
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
  </div>
}
