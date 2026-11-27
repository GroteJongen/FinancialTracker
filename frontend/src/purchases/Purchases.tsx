import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from './api'
import type { Account, Listing, Purchase } from './api'
import AuditHistory from './AuditHistory'
import Valuation from '../valuation/Valuation'

type Form = {
  listing_id: string; trade_date: string; quantity: string
  unit_price: string; commission: string; reason: string
}
const emptyForm = (): Form => ({
  listing_id: '', trade_date: todayWarsaw(), quantity: '', unit_price: '', commission: '0', reason: '',
})
const decimals: [keyof Form, string][] = [
  ['quantity', 'Liczba jednostek'], ['unit_price', 'Cena jednostki'], ['commission', 'Prowizja'],
]
const normalize = (value: string) => value.trim().replace(',', '.')
const canonicalDecimal = (value: string) => {
  const [whole, fraction = ''] = value.split('.')
  const integer = whole.replace(/^0+(?=[0-9])/, '')
  const digits = fraction.replace(/0+$/, '')
  return integer + (digits ? '.' + digits : '')
}

function sortPurchases(items: Purchase[]) {
  return [...items].sort((a, b) =>
    b.trade_date.localeCompare(a.trade_date) || b.created_at.localeCompare(a.created_at) || a.id.localeCompare(b.id),
  )
}

export default function Purchases({ accounts }: { accounts: Account[] }) {
  const [accountId, setAccountId] = useState(accounts[0].id)
  const [busy, setBusy] = useState(false)
  const account = accounts.find((item) => item.id === accountId) ?? accounts[0]
  return <section className="purchases-section" aria-labelledby="purchases-title">
    <div className="section-heading"><h2 id="purchases-title">Zakupy IUSQ</h2>
      <span>XETRA · EUR · ACC</span></div>
    <div className="purchase-account-picker">
      <label htmlFor="purchase-account">Rachunek</label>
      <select id="purchase-account" value={account.id} disabled={busy}
        onChange={(event) => setAccountId(event.target.value)}>
        {accounts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
    </div>
    <AccountPurchases key={account.id} account={account} onBusyChange={setBusy} />
  </section>
}

function AccountPurchases({ account, onBusyChange }: {
  account: Account; onBusyChange: (busy: boolean) => void
}) {
  const [listings, setListings] = useState<Listing[]>([])
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [retry, setRetry] = useState(0)
  const [form, setForm] = useState<Form>(emptyForm)
  const [editing, setEditing] = useState<Purchase | null>(null)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const submission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const [auditId, setAuditId] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void Promise.all([
      request<Listing[]>('/api/listings', { signal: controller.signal }),
      request<Purchase[]>(`/api/accounts/${account.id}/purchases`, { signal: controller.signal }),
    ]).then(([options, items]) => {
      if (!active) return
      setListings(options)
      setPurchases(sortPurchases(items.filter((item) => options.some((option) => option.id === item.listing_id))))
      setForm((previous) => ({ ...previous, listing_id: previous.listing_id || options[0]?.id || '' }))
      setLoadError('')
      setLoaded(true)
    }).catch(() => { if (active) setLoadError('Nie udało się pobrać zakupów. Spróbuj ponownie.') })
    return () => { active = false; controller.abort() }
  }, [account.id, retry])

  function field(name: keyof Form, value: string) {
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  function beginEdit(purchase: Purchase) {
    setEditing(purchase)
    setForm({
      listing_id: purchase.listing_id, trade_date: purchase.trade_date,
      quantity: purchase.quantity, unit_price: purchase.unit_price,
      commission: purchase.commission, reason: '',
    })
    setMessage(null)
  }

  function cancelEdit() {
    setEditing(null)
    setForm({ ...emptyForm(), listing_id: listings[0]?.id || '' })
    setMessage(null)
    submission.current = null
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (savingRef.current) return
    for (const [key, label] of decimals) {
      const value = normalize(form[key])
      if (!/^[0-9]{1,10}(?:\.[0-9]{1,8})?$/.test(value)) {
        setMessage({ text: label + ': podaj do 10 cyfr przed i 8 po przecinku.', error: true })
        return
      }
      if (key !== 'commission' && /^0+(?:\.0+)?$/.test(value)) {
        setMessage({ text: label + ': wartość musi być większa od zera.', error: true })
        return
      }
    }
    if (!form.trade_date || form.trade_date > todayWarsaw()) {
      setMessage({ text: 'Podaj datę zakupu nie późniejszą niż dzisiaj.', error: true })
      return
    }
    if (editing && !form.reason.trim()) {
      setMessage({ text: 'Podaj powód korekty.', error: true })
      return
    }
    const body = {
      listing_id: form.listing_id, trade_date: form.trade_date, currency: 'EUR',
      quantity: normalize(form.quantity), unit_price: normalize(form.unit_price),
      commission: normalize(form.commission),
    }
    let payload
    if (editing) {
      payload = { ...body, expected_revision: editing.revision, reason: form.reason.trim() }
    } else {
      const fingerprint = JSON.stringify({
        ...body, quantity: canonicalDecimal(body.quantity),
        unit_price: canonicalDecimal(body.unit_price), commission: canonicalDecimal(body.commission),
      })
      if (submission.current?.fingerprint !== fingerprint) {
        submission.current = { fingerprint, requestId: crypto.randomUUID() }
      }
      payload = { ...body, request_id: submission.current.requestId }
    }
    savingRef.current = true
    setSaving(true)
    onBusyChange(true)
    setMessage(null)
    try {
      const saved = await request<Purchase>(
        `/api/accounts/${account.id}/purchases` + (editing ? '/' + editing.id : ''),
        { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) },
      )
      setPurchases((previous) => sortPurchases([
        ...previous.filter((item) => item.id !== saved.id), saved,
      ]))
      setEditing(null)
      setForm({ ...emptyForm(), listing_id: listings[0]?.id || '' })
      submission.current = null
      setMessage({ text: editing ? 'Korekta została zapisana wraz z historią zmian.' : 'Zakup został zapisany.', error: false })
    } catch (error) {
      setMessage({ text: error instanceof ApiError ? error.message : 'Nie udało się zapisać zakupu.', error: true })
    } finally {
      savingRef.current = false
      setSaving(false)
      onBusyChange(false)
    }
  }

  if (!loaded) return <div className="purchase-panel">
    {loadError ? <div role="alert"><p>{loadError}</p><button type="button"
      onClick={() => { setLoadError(''); setRetry((value) => value + 1) }}>Ponów odczyt zakupów</button></div>
      : <p role="status" aria-label="Stan zakupów">Pobieranie zakupów…</p>}
  </div>

  return <>
    {listings[0] && <Valuation accountId={account.id} listingId={listings[0].id}
      ledgerVersion={purchases.map((item) => item.id + ':' + item.revision).join('|')} />}
    <div className="purchase-panel">
    <div className="purchase-form-heading">
      <div><h3>{editing ? 'Popraw zakup' : 'Dodaj zakup'}</h3>
        <p>Zapisz rzeczywiste dane z potwierdzenia transakcji. Kwoty w EUR.</p></div>
      <span className="account-type">{editing ? 'KOREKTA · WERSJA ' + editing.revision : 'NOWA TRANSAKCJA'}</span>
    </div>
    <form onSubmit={(event) => { void save(event) }} noValidate aria-label={editing ? 'Korekta zakupu' : 'Nowy zakup'}>
      <fieldset disabled={saving}>
        <div className="purchase-form-grid">
          <label className="instrument-field" htmlFor="purchase-listing">Instrument
            <select id="purchase-listing" value={form.listing_id} onChange={(event) => field('listing_id', event.target.value)}>
              {listings.map((listing) => <option key={listing.id} value={listing.id}>
                {listing.symbol} · {listing.mic === 'XETR' ? 'Xetra' : listing.mic} · {listing.currency} · {listing.isin}
              </option>)}
            </select></label>
          <label htmlFor="purchase-date">Data zakupu
            <input id="purchase-date" type="date" max={todayWarsaw()} required value={form.trade_date}
              onChange={(event) => field('trade_date', event.target.value)} /></label>
          <label htmlFor="purchase-quantity">Liczba jednostek
            <input id="purchase-quantity" type="text" inputMode="decimal" placeholder="np. 0,125" required
              value={form.quantity} onChange={(event) => field('quantity', event.target.value)} /></label>
          <label htmlFor="purchase-price">Cena jednostki (EUR)
            <input id="purchase-price" type="text" inputMode="decimal" placeholder="np. 100,00" required
              value={form.unit_price} onChange={(event) => field('unit_price', event.target.value)} /></label>
          <label htmlFor="purchase-commission">Prowizja (EUR)
            <input id="purchase-commission" type="text" inputMode="decimal" required value={form.commission}
              onChange={(event) => field('commission', event.target.value)} /></label>
          {editing && <label className="reason-field" htmlFor="purchase-reason">Powód korekty
            <textarea id="purchase-reason" value={form.reason} maxLength={500} required rows={2}
              onChange={(event) => field('reason', event.target.value)} /></label>}
        </div>
        <p className="form-hint">Możesz wpisać przecinek lub kropkę. Dokładność: do 8 miejsc po przecinku.</p>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={!form.listing_id}>
            {saving ? 'Zapisywanie…' : editing ? 'Zapisz korektę' : 'Zapisz zakup'}
          </button>
          {editing && <button type="button" className="secondary-button" onClick={cancelEdit}>Anuluj korektę</button>}
        </div>
      </fieldset>
    </form>
    {message && <div className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}
      role={message.error ? 'alert' : 'status'} aria-label="Wynik zapisu">
      <p>{message.text}</p>
      {message.error && <button type="button" className="text-button" disabled={saving} onClick={() => {
        cancelEdit(); setLoaded(false); setRetry((count) => count + 1)
      }}>Odśwież historię</button>}
    </div>}
    <div className="history-heading"><h3>Historia zakupów</h3><span>{purchases.length} zapisów</span></div>
    {purchases.length === 0
      ? <div className="empty-purchases"><span aria-hidden="true">＋</span><p>Nie dodano jeszcze zakupów.</p></div>
      : <div className="purchase-table-scroll"><table className="purchase-table">
        <caption className="sr-only">Zakupy na rachunku {account.name}</caption>
        <thead><tr><th>Data</th><th>Instrument</th><th>Jednostki</th><th>Cena (EUR)</th>
          <th>Prowizja (EUR)</th><th>Wersja</th><th>Działania</th></tr></thead>
        <tbody>{purchases.map((purchase) => <tr key={purchase.id}>
          <td>{formatDate(purchase.trade_date)}</td><td><strong>{purchase.symbol}</strong></td>
          <td>{formatDecimal(purchase.quantity)}</td><td>{formatDecimal(purchase.unit_price, 2)}</td>
          <td>{formatDecimal(purchase.commission, 2)}</td><td>{purchase.revision}</td>
          <td className="row-actions">
            <button type="button" disabled={saving} className="text-button" onClick={() => beginEdit(purchase)}>Popraw</button>
            <button type="button" disabled={saving} className="text-button"
              aria-expanded={auditId === purchase.id}
              onClick={() => setAuditId((id) => id === purchase.id ? null : purchase.id)}>Zmiany</button>
          </td>
        </tr>)}</tbody>
      </table></div>}
    {auditId && <AuditHistory
      key={auditId + ':' + purchases.find((purchase) => purchase.id === auditId)?.revision}
      accountId={account.id} purchaseId={auditId} />}
    </div>
  </>
}
