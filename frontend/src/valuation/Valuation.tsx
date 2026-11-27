import { useEffect, useRef, useState } from 'react'
import { quoteTime } from '../portfolio/market'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from '../purchases/api'

type Price = {
  id: string; listing_id: string; price: string; currency: string
  observed_on: string; source: 'MANUAL' | 'YAHOO'; recorded_at: string; quoted_at?: string | null
}
type Figures = {
  cost: string; average_cost: string | null; market_value: string | null
  gain: string | null; gain_percent: string | null
}
type Summary = {
  status: 'empty' | 'unpriced' | 'outdated' | 'priced'
  quantity: string; latest_trade_date: string | null; currency: string
  price: Price | null; history: Price[]; display: Figures
}
type Loaded = { key: string; summary: Summary } | { key: string; error: string }

function canonical(value: string) {
  const [whole, fraction = ''] = value.split('.')
  const digits = fraction.replace(/0+$/, '')
  return whole.replace(/^0+(?=[0-9])/, '') + (digits ? '.' + digits : '')
}

export default function Valuation({ accountId, listingId, ledgerVersion }: {
  accountId: string; listingId: string; ledgerVersion: string
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [price, setPrice] = useState('')
  const [observedOn, setObservedOn] = useState(todayWarsaw)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const submission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null)
  const key = accountId + '/' + listingId + '/' + ledgerVersion + '/' + refresh
  const current = loaded?.key === key ? loaded : null
  const summary = current && 'summary' in current ? current.summary : null
  const error = current && 'error' in current ? current.error : null

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void request<Summary>(
      `/api/accounts/${accountId}/valuation?listing_id=${listingId}`,
      { signal: controller.signal },
    ).then((result) => { if (active) setLoaded({ key, summary: result }) })
      .catch(() => { if (active) setLoaded({ key, error: 'Nie udało się pobrać wyceny.' }) })
    return () => { active = false; controller.abort() }
  }, [accountId, listingId, key])

  useEffect(() => {
    const update = () => setRefresh((value) => value + 1)
    window.addEventListener('financialtracker:quotes-updated', update)
    return () => window.removeEventListener('financialtracker:quotes-updated', update)
  }, [])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (savingRef.current || !summary) return
    const normalized = price.trim().replace(',', '.')
    if (!/^[0-9]{1,10}(?:\.[0-9]{1,8})?$/.test(normalized) || /^0+(?:\.0+)?$/.test(normalized)) {
      setMessage({ error: true, text: 'Podaj dodatnią cenę: do 10 cyfr przed i 8 po przecinku.' })
      return
    }
    if (!observedOn || observedOn > todayWarsaw() ||
        (summary.latest_trade_date !== null && observedOn < summary.latest_trade_date)) {
      setMessage({ error: true, text: 'Data wyceny musi być pomiędzy ostatnim zakupem a dzisiaj.' })
      return
    }
    const fingerprint = JSON.stringify({ price: canonical(normalized), date: observedOn, listingId })
    if (submission.current?.fingerprint !== fingerprint) {
      submission.current = { fingerprint, requestId: crypto.randomUUID() }
    }
    savingRef.current = true
    setSaving(true)
    setMessage(null)
    try {
      await request<Price>(`/api/accounts/${accountId}/prices`, {
        method: 'POST',
        body: JSON.stringify({
          listing_id: listingId, request_id: submission.current.requestId,
          price: normalized, observed_on: observedOn, currency: 'EUR',
        }),
      })
      submission.current = null
      setPrice('')
      setMessage({ error: false, text: 'Cena została zapisana. Wycenę obliczamy dla najnowszej daty ceny.' })
      setRefresh((value) => value + 1)
    } catch (problem) {
      setMessage({ error: true, text: problem instanceof ApiError ? problem.message : 'Nie udało się zapisać ceny.' })
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  const amount = (value: string | null | undefined) =>
    value === null || value === undefined ? '—' : formatDecimal(value, 2) + ' EUR'
  const cards = [
    ['Kurs jednostki IUSQ', amount(summary?.price?.price)],
    ['Liczba jednostek', summary ? formatDecimal(summary.quantity) : '—'],
    ['Koszt zakupów', amount(summary?.display.cost)],
    ['Średni koszt jednostki', amount(summary?.display.average_cost)],
    ['Wartość pozycji', amount(summary?.display.market_value)],
    ['Zysk / strata', amount(summary?.display.gain)],
    ['Wynik procentowy', summary?.display.gain_percent == null
      ? '—' : formatDecimal(summary.display.gain_percent, 2) + '%'],
  ]
  const negative = summary?.display.gain?.startsWith('-')
  return <section className="valuation-section" aria-labelledby="valuation-title">
    <div className="valuation-heading"><h3 id="valuation-title">Wycena IUSQ</h3><span>EUR · {summary?.price?.source === 'YAHOO' ? 'YAHOO FINANCE' : 'CENA RĘCZNA'}</span></div>
    {!current && <p role="status" aria-label="Stan wyceny">Przeliczanie pozycji…</p>}
    {error && <div role="alert"><p>{error}</p>
      <button type="button" className="text-button" onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt wyceny</button>
    </div>}
    <dl className="valuation-cards">{cards.map(([label, value]) =>
      <div key={label} className={label === 'Kurs jednostki IUSQ' ? 'unit-quote' : ['Zysk / strata', 'Wynik procentowy'].includes(label) && summary?.status === 'priced' ? (negative ? 'loss' : 'profit') : ''}>
        <dt>{label}</dt><dd>{value}</dd>
      </div>,
    )}</dl>
    {summary?.status === 'empty' && <p className="valuation-note">Brak zakupów na tym rachunku.</p>}
    {summary?.status === 'unpriced' && <p className="valuation-note">Brak wyceny — wpisz cenę jednostki.</p>}
    {summary?.status === 'outdated' && <p className="valuation-warning">
      Cena wymaga aktualizacji: jest wcześniejsza niż ostatni zakup
      {summary.latest_trade_date && ' (' + formatDate(summary.latest_trade_date) + ')'}.
      Wartość pozycji i wynik będą dostępne po zapisaniu nowszej ceny.
    </p>}
    {summary?.price && <p className="price-reference">
      Cena: <strong>{formatDecimal(summary.price.price, 2)} EUR</strong> ·
      Data: <strong>{formatDate(summary.price.observed_on)}</strong> · Źródło: {summary.price.source === 'YAHOO' ? 'Yahoo Finance' : 'ręczne'}
      {summary.price.quoted_at && <> · Notowanie: {quoteTime(summary.price.quoted_at)} · Pobrano: {quoteTime(summary.price.recorded_at)}</>}
    </p>}
    <p className="form-hint">Wynik niezrealizowany uwzględnia prowizje zakupu. Bez podatku i kosztu przyszłej sprzedaży.</p>
    <form onSubmit={(event) => { void save(event) }} noValidate aria-label="Cena wyceny">
      <fieldset disabled={saving || !summary}>
        <div className="price-form-grid">
          <label htmlFor="valuation-price">Cena wyceny (EUR)
            <input id="valuation-price" type="text" inputMode="decimal" required placeholder="np. 110,00"
              value={price} onChange={(event) => setPrice(event.target.value)} /></label>
          <label htmlFor="valuation-date">Data wyceny
            <input id="valuation-date" type="date" required max={todayWarsaw()}
              min={summary?.latest_trade_date ?? undefined} value={observedOn}
              onChange={(event) => setObservedOn(event.target.value)} /></label>
          <button type="submit" className="primary-button">{saving ? 'Zapisywanie ceny…' : 'Zapisz cenę'}</button>
        </div>
      </fieldset>
    </form>
    <p className="form-hint">Data ceny nie może być wcześniejsza niż ostatni zakup ani późniejsza niż dzisiaj.</p>
    {message && <p className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}
      role={message.error ? 'alert' : 'status'} aria-label="Zapis ceny">{message.text}</p>}
    {summary && summary.history.length > 0 && <details className="price-history">
      <summary>Historia cen ręcznych ({summary.history.length})</summary>
      <div className="purchase-table-scroll"><table className="purchase-table">
        <caption className="sr-only">Historia cen wyceny</caption>
        <thead><tr><th>Data ceny</th><th>Cena (EUR)</th><th>Źródło</th><th>Zapisano</th></tr></thead>
        <tbody>{summary.history.map((item) => <tr key={item.id}>
          <td>{formatDate(item.observed_on)}</td><td>{formatDecimal(item.price, 2)}</td><td>Ręczne</td>
          <td>{new Intl.DateTimeFormat('pl-PL', {
            timeZone: 'Europe/Warsaw', dateStyle: 'short', timeStyle: 'medium',
          }).format(new Date(item.recorded_at))}</td>
        </tr>)}</tbody>
      </table></div>
    </details>}
  </section>
}
