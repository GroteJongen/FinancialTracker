import { useEffect, useRef, useState } from 'react'
import { quoteTime, refreshMarket } from './market'
import YahooMapping from './YahooMapping'
import type { FormEvent } from 'react'
import { formatDate, formatDecimal, request, todayWarsaw } from '../purchases/api'

type Allocation = { asset_class: string; amount: string; percent: string; start: string; end: string }
type Totals = { cost: string | null; value: string | null; paid_income: string | null; gain: string | null; gain_percent: string | null; known_value: string; complete: boolean; allocation_value: Allocation[]; allocation_cost: Allocation[] }
type Position = {
  account_id: string; account_name: string; account_kind: string; label: string; asset_class: string
  currency: string; native_cost: string; native_value: string | null; cost_pln: string | null
  value_pln: string | null; gain_pln: string | null; paid_income: string | null; reasons: string[]
  observed_on: string | null; purchase_id?: string; purchase_revision?: number
  price_source?: string | null; quoted_at?: string | null; fetched_at?: string | null; stale_price?: boolean
  yahoo?: { symbol: string; failed: boolean; attempted_at: string | null; quoted_at: string | null; fetched_at: string | null } | null
  quantity: string; mark_id?: string | null; trade_date?: string; listing_id?: string
}
type Snapshot = { scope: string; as_of: string; account_count: number; position_count: number; totals: Totals; positions: Position[]; estimated_fx: boolean; missing_fx: { currency: string; requested_on: string }[]; fx_rates: { currency: string; requested_on: string; effective_on: string; rate: string; table_number: string }[] }
const labels: Record<string, string> = { BOND: 'Obligacje', ETF: 'ETF-y', STOCK: 'Akcje' }
const colors: Record<string, string> = { BOND: '#b58a36', ETF: '#426e42', STOCK: '#387e87' }
const reasons: Record<string, string> = { missing_price: 'Brak ceny', outdated_price: 'Cena sprzed ostatniego zakupu', missing_fx: 'Brak kursu NBP', missing_bond_valuation: 'Uzupełnij wycenę obligacji' }
const scopes = [['ALL', 'Wszystkie'], ['STANDARD', 'Zwykłe'], ['IKE', 'IKE'], ['IKZE', 'IKZE'], ['RETIREMENT', 'IKE + IKZE']]
const amount = (value: string | null | undefined) => value == null ? '—' : formatDecimal(value, 2) + ' PLN'

export default function Portfolio() {
  const [scope, setScope] = useState('ALL')
  const [version, setVersion] = useState(0)
  const [loaded, setLoaded] = useState<{ key: string; data: Snapshot } | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [marketMessage, setMarketMessage] = useState('')
  const [marketBusy, setMarketBusy] = useState(false)
  const marketLock = useRef(false)
  const [basis, setBasis] = useState<'value' | 'cost'>('value')
  const [busy, setBusy] = useState(false)
  const savingRef = useRef(false)
  const [editing, setEditing] = useState<string | null>(null)
  const key = scope + '/' + version
  const data = loaded?.key === key ? loaded.data : null

  useEffect(() => {
    const refresh = () => setVersion((value) => value + 1)
    window.addEventListener('financialtracker:updated', refresh)
    return () => window.removeEventListener('financialtracker:updated', refresh)
  }, [])
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    void request<Snapshot>('/api/portfolio?scope=' + scope, { signal: controller.signal })
      .then((result) => { if (active) { setLoaded({ key, data: result }); setError('') } })
      .catch(() => { if (active) setError('Nie udało się pobrać podsumowania portfela.') })
    return () => { active = false; controller.abort() }
  }, [scope, key])

  async function fetchMarket() {
    if (marketLock.current) return
    marketLock.current = true; setMarketBusy(true); setMarketMessage('Pobieranie kursów Yahoo Finance...')
    try {
      const result = await refreshMarket()
      setMarketMessage('Yahoo Finance: odświeżono ' + result.updated + ' notowań.' + (result.failed ? ' Nie pobrano ' + result.failed + '; zachowano ostatnie poprawne ceny.' : ' Zapytania najwyżej raz na 5 minut dla każdego notowania.'))
    } catch { setMarketMessage('Nie udało się odświeżyć Yahoo. Zachowano poprzednie ceny; możesz wpisać cenę ręcznie.') }
    finally { marketLock.current = false; setMarketBusy(false) }
  }
  useEffect(() => {
    let active = true
    void refreshMarket().then((result) => {
      if (active) setMarketMessage(result.failed ? 'Yahoo: nie pobrano ' + result.failed + ' notowań. Zachowano poprzednie ceny.' : 'Yahoo Finance: sprawdzono dostępne kursy. Zapytania najwyżej raz na 5 minut.')
    }).catch(() => { if (active) setMarketMessage('Yahoo jest niedostępne. Zachowano poprzednie ceny.') })
    return () => { active = false }
  }, [])

  async function fetchFx() {
    if (savingRef.current) return
    savingRef.current = true; setBusy(true); setMessage('')
    try {
      const result = await request<{ updated: number; failed: number; remaining: number }>('/api/portfolio/fx/refresh?scope=' + scope, { method: 'POST' })
      setMessage(`Kursy NBP: odświeżono ${result.updated}. Brakujących kursów: ${result.remaining}.` + (result.failed ? ' Część zapytań nie powiodła się; zachowano poprzednie dane.' : result.remaining ? ' Kliknij ponownie, aby pobrać kolejną partię.' : ''))
    } catch (failure) { setMessage(failure instanceof Error ? failure.message : 'Nie udało się pobrać kursów.') }
    finally { savingRef.current = false; setBusy(false) }
  }
  const totals = data?.totals
  const allocation = (basis === 'value' ? totals?.allocation_value : totals?.allocation_cost) ?? []
  const gradient = allocation.map((item) => `${colors[item.asset_class]} ${item.start}% ${item.end}%`).join(', ')
  const cards = [
    ['Koszt zakupów', amount(totals?.cost)], ['Wartość aktywów', amount(totals?.value)],
    ['Wypłacone odsetki', amount(totals?.paid_income)], ['Łączny zysk / strata', amount(totals?.gain)],
    ['Wynik względem kosztu', totals?.gain_percent == null ? '—' : formatDecimal(totals.gain_percent, 2) + '%'],
  ]
  const bondData = data ?? (loaded?.data.scope === scope ? loaded.data : null)
  const bond = bondData?.positions.find((item) => item.purchase_id === editing)
  return <section className="portfolio-section" aria-labelledby="portfolio-title">
    <div className="section-heading"><h2 id="portfolio-title">Mój portfel</h2><span>WSPÓLNE PODSUMOWANIE · PLN</span></div>
    <div className="portfolio-filters" role="group" aria-label="Filtr portfela">
      {scopes.map(([value, label]) => <button key={value} type="button" aria-pressed={scope === value} disabled={busy}
        onClick={() => { setScope(value); setEditing(null); setMessage('') }}>{label}</button>)}
    </div>
    <div className="portfolio-actions"><button type="button" className="text-button" disabled={busy || marketBusy} onClick={() => { setVersion((value) => value + 1); void fetchMarket() }}>Odśwież podsumowanie</button>
      <button type="button" className="secondary-button" disabled={busy || !data} onClick={() => { void fetchFx() }}>{busy ? 'Pobieranie…' : 'Pobierz kursy NBP'}</button></div>
    {!data && !error && <p role="status">Pobieranie podsumowania portfela…</p>}
    {error && <p role="alert" className="portfolio-warning">{error}</p>}
    {message && <p role="status" aria-label="Informacja portfela" className="valuation-note">{message}</p>}
    {marketMessage && <p role="status" aria-label="Stan Yahoo" className="valuation-note">{marketMessage}</p>}
    <p className="form-hint">Yahoo Finance: notowania mogą być opóźnione; Xetra około 15 minut. Czas notowania nie jest czasem pobrania. Nowsza cena ręczna ma pierwszeństwo do pojawienia się późniejszego notowania. NBP aktualizujesz osobnym przyciskiem. Jedno odświeżenie obejmuje do 8 notowań; przy większym portfelu powtórz odświeżenie.</p>
    <dl className="portfolio-cards">{cards.map(([label, value]) => <div key={label} className={label === 'Łączny zysk / strata' && totals?.gain?.startsWith('-') ? 'portfolio-loss' : ''}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {data && !totals?.complete && <p className="portfolio-warning" role="status" aria-label="Kompletność portfela">
      Podsumowanie jest niepełne. Wartość pozycji z dostępną wyceną: {amount(totals?.known_value)}.
      Uzupełnij brakujące ceny, wyceny obligacji lub kursy NBP. Braki nie są traktowane jako zero.</p>}
    {data?.estimated_fx && <p className="valuation-note">Kwoty walutowe są przeliczane na PLN. Koszt historyczny jest szacunkiem po kursie NBP z dnia zakupu lub ostatniej wcześniejszej publikacji; bieżąca wartość korzysta z ostatniego dostępnego kursu dla dnia podsumowania.</p>}
    <div className="portfolio-chart-panel"><div>
      <h3>Struktura portfela</h3>
      <div className="portfolio-filters" role="group" aria-label="Podstawa wykresu">
        <button type="button" aria-pressed={basis === 'value'} onClick={() => setBasis('value')}>Według wartości</button>
        <button type="button" aria-pressed={basis === 'cost'} onClick={() => setBasis('cost')}>Według kosztu</button>
      </div>
      {allocation.length > 0 ? <ul className="portfolio-legend">{allocation.map((item) => <li key={item.asset_class}>
        <span className="portfolio-dot" style={{ background: colors[item.asset_class] }} />
        <span>{labels[item.asset_class]}</span><strong>{formatDecimal(item.percent, 2)}%</strong><span>{amount(item.amount)}</span>
      </li>)}</ul> : <p className="valuation-note">{data?.position_count === 0 ? 'Dodaj pierwsze aktywa, aby zobaczyć proporcje.' : 'Wykres wymaga kompletu wycen i kursów dla wybranej podstawy.'}</p>}
    </div>{allocation.length > 0 && <div className="portfolio-pie" role="img"
      aria-label={'Udziały portfela: ' + allocation.map((item) => labels[item.asset_class] + ' ' + formatDecimal(item.percent, 2) + '%').join(', ')}
      style={{ background: `conic-gradient(${gradient})` }} />}</div>
    <p className="form-hint">Wypłacone odsetki zwiększają wynik, ale nie są dodawane do aktywów na wykresie. Gotówka i dywidendy akcji nie są jeszcze ewidencjonowane. Wynik brutto, bez podatków i kosztu przyszłej sprzedaży lub wykupu.</p>
    {data?.position_count === 0 && <p className="empty-purchases">Brak zakupionych aktywów w wybranym filtrze.</p>}
    {data && data.positions.length > 0 && <div className="purchase-table-scroll"><table className="purchase-table portfolio-table">
      <caption className="sr-only">Wszystkie aktywa wybranego portfela</caption>
      <thead><tr><th>Aktywo</th><th>Rachunek</th><th>Koszt (PLN)</th><th>Wartość (PLN)</th><th>Wynik (PLN)</th><th>Wycena</th></tr></thead>
      <tbody>{data.positions.map((item) => <tr key={item.account_id + '/' + (item.purchase_id ?? item.listing_id)}>
        <td><strong>{item.label}</strong><br />{labels[item.asset_class]} · {formatDecimal(item.quantity)} szt.
          {item.trade_date && <small>Zakup: {formatDate(item.trade_date)}</small>}</td>
        <td>{item.account_name}<br />{item.account_kind === 'STANDARD' ? 'Zwykły' : item.account_kind}</td>
        <td>{amount(item.cost_pln)}{item.currency !== 'PLN' && <small>{formatDecimal(item.native_cost, 2)} {item.currency}</small>}</td>
        <td>{amount(item.value_pln)}{item.currency !== 'PLN' && item.native_value !== null && <small>{formatDecimal(item.native_value, 2)} {item.currency}</small>}</td>
        <td>{amount(item.gain_pln)}</td><td>{item.observed_on && <span>{formatDate(item.observed_on)}<br /></span>}
          {item.reasons.map((reason) => <span key={reason}>{reasons[reason]}<br /></span>)}
          {item.price_source && <small>{item.price_source === 'YAHOO' ? 'Yahoo Finance' : 'Cena ręczna'}</small>}
          {item.quoted_at && <small>Notowanie: {quoteTime(item.quoted_at)}</small>}
          {item.price_source === 'YAHOO' && item.fetched_at && <small>Pobrano: {quoteTime(item.fetched_at)}</small>}
          {item.stale_price && <small>Cena starsza niż 4 dni</small>}
          {item.yahoo?.failed && <small>Ostatnia próba Yahoo nieudana; poprzednia cena zachowana</small>}
          {item.purchase_id && <button type="button" className="text-button" disabled={busy} onClick={() => setEditing(item.purchase_id!)}>Wycena obligacji</button>}</td>
      </tr>)}</tbody></table></div>}
    {bond && <BondMark key={bond.purchase_id + ':' + bond.purchase_revision + ':' + bond.mark_id} position={bond} onBusy={setBusy}
      onSaved={() => { setEditing(null); setMessage('Wycena obligacji została zapisana.') }} onCancel={() => setEditing(null)} />}
    {bondData && bondData.positions.some((item) => item.listing_id) && <details className="portfolio-fx"><summary>Automatyczne kursy Yahoo Finance</summary>
      <p className="form-hint">IUSQ ma domyślnie symbol IUSQ.DE. Dla akcji przypisz symbol z Yahoo dla tej samej giełdy i waluty. Obsługiwane giełdy: XETR, XNAS, XNYS, XWAR. Odpowiedź dostawcy musi potwierdzić giełdę, walutę i typ aktywa. Symbol innej spółki na tej samej giełdzie wymaga Twojej kontroli.</p>
      {[...new Map(bondData.positions.filter((item) => item.listing_id).map((item) => [item.listing_id, item])).values()].map((item) =>
        <YahooMapping key={item.listing_id} listingId={item.listing_id!} label={item.label} current={item.yahoo?.symbol ?? null} />)}
    </details>}
    {data && data.fx_rates.length > 0 && <details className="portfolio-fx"><summary>Kursy NBP użyte w podsumowaniu</summary>
      <div className="purchase-table-scroll"><table className="purchase-table"><caption className="sr-only">Kursy przeliczenia portfela</caption>
        <thead><tr><th>Waluta</th><th>Dla dnia</th><th>Data tabeli</th><th>PLN / jednostkę</th><th>Tabela NBP</th></tr></thead>
        <tbody>{data.fx_rates.map((rate) => <tr key={rate.currency + rate.requested_on}><td>{rate.currency}</td><td>{formatDate(rate.requested_on)}</td><td>{formatDate(rate.effective_on)}</td><td>{formatDecimal(rate.rate)}</td><td>{rate.table_number}</td></tr>)}</tbody>
      </table></div></details>}
  </section>
}

function BondMark({ position, onBusy, onSaved, onCancel }: { position: Position; onBusy: (value: boolean) => void; onSaved: () => void; onCancel: () => void }) {
  const [value, setValue] = useState(position.native_value ?? '')
  const [paid, setPaid] = useState(position.paid_income ?? '0')
  const [day, setDay] = useState(todayWarsaw)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const submission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const [error, setError] = useState('')
  async function save(event: FormEvent) {
    event.preventDefault()
    if (savingRef.current) return
    const body = { purchase_revision: position.purchase_revision, value: value.trim().replace(',', '.'), paid_interest: paid.trim().replace(',', '.'), observed_on: day }
    const canonical = (text: string) => {
      const [whole, fraction = ''] = text.split('.')
      const digits = fraction.replace(/0+$/, '')
      return whole.replace(/^0+(?=[0-9])/, '') + (digits ? '.' + digits : '')
    }
    const fingerprint = JSON.stringify({ ...body, value: canonical(body.value), paid_interest: canonical(body.paid_interest) })
    if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, requestId: crypto.randomUUID() }
    savingRef.current = true; setSaving(true); onBusy(true); setError('')
    try {
      await request(`/api/accounts/${position.account_id}/bonds/${position.purchase_id}/valuations`, { method: 'POST', body: JSON.stringify({ ...body, request_id: submission.current.requestId }) })
      onSaved()
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Nie udało się zapisać wyceny.') }
    finally { savingRef.current = false; setSaving(false); onBusy(false) }
  }
  return <form className="purchases-section purchase-panel portfolio-bond-form" aria-label="Wycena partii obligacji" noValidate onSubmit={(event) => { void save(event) }}>
    <h3>Wycena {position.label} · {formatDecimal(position.quantity)} szt.</h3>
    <p className="valuation-note">Rachunek: {position.account_name}. Zakup: {position.trade_date && formatDate(position.trade_date)}. Wpisz rzeczywiste dane dla tej partii obligacji.</p>
    <fieldset disabled={saving}><div className="purchase-form-grid">
      <label htmlFor="portfolio-bond-value">Bieżąca wartość obligacji (PLN)<input id="portfolio-bond-value" inputMode="decimal" required value={value} onChange={(event) => setValue(event.target.value)} /></label>
      <label htmlFor="portfolio-bond-paid">Łączne wypłacone odsetki brutto (PLN)<input id="portfolio-bond-paid" inputMode="decimal" required value={paid} onChange={(event) => setPaid(event.target.value)} /></label>
      <label htmlFor="portfolio-bond-day">Data wyceny obligacji<input id="portfolio-bond-day" type="date" required min={position.trade_date} max={todayWarsaw()} value={day} onChange={(event) => setDay(event.target.value)} /></label>
    </div><p className="form-hint">Wartość obejmuje kapitał i odsetki pozostające w obligacjach. Nie dodawaj do niej już wypłaconych odsetek — wpisz je osobno jako sumę od zakupu, nie nową pojedynczą wypłatę. Podaj kwoty brutto, przed podatkiem. Dane są ręczne.</p>
    <div className="form-actions"><button type="submit" className="primary-button">Zapisz wycenę obligacji</button><button type="button" className="secondary-button" onClick={onCancel}>Anuluj wycenę obligacji</button></div></fieldset>
    {error && <p role="alert" className="purchase-message message-error">{error}</p>}
  </form>
}
