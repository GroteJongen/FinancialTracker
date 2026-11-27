import { useEffect, useRef, useState } from 'react'
import { quoteTime } from '../portfolio/market'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from '../purchases/api'
import type { Listing, Purchase } from '../purchases/api'
import AuditHistory from '../purchases/AuditHistory'

type Summary = {
  status: 'empty' | 'unpriced' | 'outdated' | 'priced'; quantity: string
  latest_trade_date: string | null
  price: { price: string; observed_on: string; source?: string; quoted_at?: string | null; recorded_at: string } | null
  display: { cost: string; average_cost: string | null; market_value: string | null; gain: string | null; gain_percent: string | null }
}
type TradeForm = { trade_date: string; quantity: string; unit_price: string; commission: string; reason: string }
const initial = (): TradeForm => ({ trade_date: todayWarsaw(), quantity: '', unit_price: '', commission: '0', reason: '' })
const normalize = (value: string) => value.trim().replace(',', '.')
const canonical = (value: string) => {
  const [whole, fraction = ''] = value.split('.')
  const digits = fraction.replace(/0+$/, '')
  return whole.replace(/^0+(?=[0-9])/, '') + (digits ? '.' + digits : '')
}

export default function StockPosition({ accountId, listing, onBusy, disabled }: {
  accountId: string; listing: Listing; onBusy: (value: boolean) => void; disabled: boolean
}) {
  const [refresh, setRefresh] = useState(0)
  const [loaded, setLoaded] = useState<{ version: number; purchases: Purchase[]; summary: Summary } | null>(null)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState<TradeForm>(initial)
  const [editing, setEditing] = useState<Purchase | null>(null)
  const [price, setPrice] = useState('')
  const [priceDate, setPriceDate] = useState(todayWarsaw)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const tradeSubmission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const priceSubmission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const [auditId, setAuditId] = useState<string | null>(null)
  const current = loaded?.version === refresh ? loaded : null
  const blocked = saving || disabled || !current

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    void Promise.all([
      request<Purchase[]>(`/api/accounts/${accountId}/purchases`, { signal: controller.signal }),
      request<Summary>(`/api/accounts/${accountId}/valuation?listing_id=${listing.id}`, { signal: controller.signal }),
    ]).then(([purchases, summary]) => {
      if (active) { setLoaded({ version: refresh, purchases: purchases.filter((item) => item.listing_id === listing.id), summary }); setLoadError('') }
    }).catch(() => { if (active) setLoadError('Nie udało się pobrać pozycji akcji. Spróbuj ponownie.') })
    return () => { active = false; controller.abort() }
  }, [accountId, listing.id, refresh])

  useEffect(() => {
    const update = () => setRefresh((value) => value + 1)
    window.addEventListener('financialtracker:quotes-updated', update)
    return () => window.removeEventListener('financialtracker:quotes-updated', update)
  }, [])

  function field(key: keyof TradeForm, value: string) { setForm((previous) => ({ ...previous, [key]: value })) }
  function cancel() { setEditing(null); setForm(initial()); setMessage(null); tradeSubmission.current = null }
  function edit(item: Purchase) {
    setEditing(item)
    setForm({ trade_date: item.trade_date, quantity: item.quantity, unit_price: item.unit_price, commission: item.commission, reason: '' })
    setMessage(null)
  }

  async function save(event: FormEvent, mode: 'trade' | 'price') {
    event.preventDefault()
    if (savingRef.current || disabled || !current) return
    const fields: Record<string, string> = mode === 'trade'
      ? { quantity: normalize(form.quantity), unit_price: normalize(form.unit_price), commission: normalize(form.commission) }
      : { price: normalize(price) }
    for (const [key, value] of Object.entries(fields)) {
      if (!/^[0-9]{1,10}(?:\.[0-9]{1,8})?$/.test(value) || (key !== 'commission' && /^0+(?:\.0+)?$/.test(value))) {
        setMessage({ text: 'Podaj dodatnie kwoty i liczbę akcji (prowizja może wynosić zero), do 8 miejsc po przecinku.', error: true }); return
      }
    }
    const body = { listing_id: listing.id, currency: listing.currency, ...fields,
      ...(mode === 'trade' ? { trade_date: form.trade_date } : { observed_on: priceDate }),
    }
    const fingerprint = JSON.stringify({ ...body, ...Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, canonical(value)])) })
    const submission = mode === 'trade' ? tradeSubmission : priceSubmission
    if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, requestId: crypto.randomUUID() }
    const correction = mode === 'trade' && editing
    const payload = correction ? { ...body, expected_revision: correction.revision, reason: form.reason.trim() }
      : { ...body, request_id: submission.current.requestId }
    savingRef.current = true; setSaving(true); onBusy(true); setMessage(null)
    try {
      await request(`/api/accounts/${accountId}/` + (mode === 'price' ? 'prices' : 'purchases' + (correction ? '/' + correction.id : '')), {
        method: correction ? 'PUT' : 'POST', body: JSON.stringify(payload),
      })
      if (mode === 'trade') { setEditing(null); setForm(initial()) } else setPrice('')
      submission.current = null
      setMessage({ text: mode === 'price' ? 'Cena akcji została zapisana.' : correction ? 'Korekta akcji została zapisana.' : 'Zakup akcji został zapisany.', error: false })
      setRefresh((value) => value + 1)
    } catch (failure) {
      setMessage({ text: failure instanceof Error ? failure.message : 'Nie udało się zapisać danych akcji.', error: true })
      if (failure instanceof ApiError && failure.status === 409) setRefresh((value) => value + 1)
    } finally { savingRef.current = false; setSaving(false); onBusy(false) }
  }

  const summary = current?.summary
  const amount = (value: string | null | undefined) => value == null ? '—' : formatDecimal(value, 2) + ' ' + listing.currency
  const cards = [
    ['Liczba akcji', summary ? formatDecimal(summary.quantity) : '—'], ['Koszt akcji', amount(summary?.display.cost)],
    ['Średni koszt akcji', amount(summary?.display.average_cost)], ['Wartość akcji', amount(summary?.display.market_value)],
    ['Zysk / strata akcji', amount(summary?.display.gain)], ['Wynik akcji (%)', summary?.display.gain_percent == null ? '—' : formatDecimal(summary.display.gain_percent, 2) + '%'],
  ]
  return <div className="purchase-panel" aria-busy={!current}>
    <h3>Pozycja: {listing.symbol} · {listing.mic}</h3>
    {!current && !loadError && <p role="status">Pobieranie pozycji akcji…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt akcji</button></div>}
    <dl className="stock-position-cards">{cards.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {summary?.status === 'empty' && <p className="valuation-note">Nie zapisano zakupów tej akcji na wybranym rachunku.</p>}
    {summary?.status === 'unpriced' && <p className="valuation-note">Brak wyceny akcji — wpisz cenę poniżej.</p>}
    {summary?.status === 'outdated' && <p className="valuation-warning">Cena akcji wymaga aktualizacji po ostatnim zakupie. Wynik pozostaje niedostępny do podania nowszej ceny.</p>}
    {summary?.price && <p className="price-reference">{summary.price.source === 'YAHOO' ? 'Yahoo Finance' : 'Cena ręczna'}: <strong>{amount(summary.price.price)}</strong> · {formatDate(summary.price.observed_on)}{summary.price.quoted_at && <> · Notowanie: {quoteTime(summary.price.quoted_at)} · Pobrano: {quoteTime(summary.price.recorded_at)}</>}</p>}
    <p className="form-hint">Kwoty w walucie notowania. Wynik uwzględnia prowizje zakupu, bez podatku, dywidend i kosztu przyszłej sprzedaży.</p>
    <form aria-label="Cena wyceny akcji" noValidate onSubmit={(event) => { void save(event, 'price') }}>
      <fieldset disabled={blocked}><div className="price-form-grid">
        <label htmlFor="stock-current-price">Cena wyceny akcji ({listing.currency})
          <input id="stock-current-price" inputMode="decimal" value={price} required onChange={(event) => setPrice(event.target.value)} /></label>
        <label htmlFor="stock-price-date">Data wyceny akcji
          <input id="stock-price-date" type="date" value={priceDate} required max={todayWarsaw()} min={summary?.latest_trade_date ?? undefined} onChange={(event) => setPriceDate(event.target.value)} /></label>
        <button className="primary-button" type="submit">Zapisz cenę akcji</button>
      </div></fieldset>
    </form>
    <div className="history-heading"><h3>{editing ? 'Popraw zakup akcji' : 'Dodaj zakup akcji'}</h3></div>
    <form aria-label={editing ? 'Korekta zakupu akcji' : 'Nowy zakup akcji'} noValidate onSubmit={(event) => { void save(event, 'trade') }}>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <label htmlFor="stock-trade-date">Data zakupu akcji<input id="stock-trade-date" type="date" required max={todayWarsaw()} value={form.trade_date} onChange={(event) => field('trade_date', event.target.value)} /></label>
        <label htmlFor="stock-quantity">Liczba akcji<input id="stock-quantity" inputMode="decimal" required value={form.quantity} onChange={(event) => field('quantity', event.target.value)} /></label>
        <label htmlFor="stock-unit-price">Cena zakupu akcji ({listing.currency})<input id="stock-unit-price" inputMode="decimal" required value={form.unit_price} onChange={(event) => field('unit_price', event.target.value)} /></label>
        <label htmlFor="stock-commission">Prowizja zakupu akcji ({listing.currency})<input id="stock-commission" inputMode="decimal" required value={form.commission} onChange={(event) => field('commission', event.target.value)} /></label>
        {editing && <label className="reason-field" htmlFor="stock-reason">Powód korekty akcji<textarea id="stock-reason" required maxLength={500} value={form.reason} onChange={(event) => field('reason', event.target.value)} /></label>}
      </div><p className="form-hint">Możesz wpisać przecinek lub kropkę. Dopuszczalne są ułamkowe akcje.</p>
      <div className="form-actions"><button className="primary-button" type="submit">{editing ? 'Zapisz korektę akcji' : 'Zapisz zakup akcji'}</button>
        {editing && <button className="secondary-button" type="button" onClick={cancel}>Anuluj korektę akcji</button>}</div></fieldset>
    </form>
    {message && <p role={message.error ? 'alert' : 'status'} aria-label="Wynik zapisu akcji" className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}>{message.text}</p>}
    <div className="history-heading"><h3>Historia zakupów akcji</h3></div>
    <div className="purchase-table-scroll"><table className="purchase-table"><caption className="sr-only">Zakupy akcji {listing.symbol}</caption>
      <thead><tr><th>Data</th><th>Akcje</th><th>Cena ({listing.currency})</th><th>Prowizja ({listing.currency})</th><th>Działania</th></tr></thead>
      <tbody>{current?.purchases.map((item) => <tr key={item.id}><td>{formatDate(item.trade_date)}</td><td>{formatDecimal(item.quantity)}</td>
        <td>{formatDecimal(item.unit_price, 2)}</td><td>{formatDecimal(item.commission, 2)}</td><td className="row-actions">
          <button className="text-button" type="button" disabled={blocked} onClick={() => edit(item)}>Popraw akcje</button>
          <button className="text-button" type="button" disabled={blocked} aria-expanded={auditId === item.id} onClick={() => setAuditId((previous) => previous === item.id ? null : item.id)}>Zmiany akcji</button>
        </td></tr>)}</tbody></table></div>
    {auditId && <AuditHistory key={auditId + ':' + current?.purchases.find((item) => item.id === auditId)?.revision} accountId={accountId} purchaseId={auditId} currency={listing.currency} />}
  </div>
}
