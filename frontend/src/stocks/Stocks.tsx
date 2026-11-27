import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { request } from '../purchases/api'
import type { Account, Listing } from '../purchases/api'
import StockPosition from './StockPosition'

const initial = () => ({ name: '', symbol: '', mic: '', currency: 'PLN', isin: '' })
const kinds: Record<string, string> = { STANDARD: 'Zwykły', IKE: 'IKE', IKZE: 'IKZE' }

export default function Stocks({ accounts, onAccountsChanged }: { accounts: Account[]; onAccountsChanged: () => void }) {
  const [refresh, setRefresh] = useState(0)
  const [catalogue, setCatalogue] = useState<{ version: number; items: Listing[] } | null>(null)
  const [loadError, setLoadError] = useState('')
  const [listingId, setListingId] = useState('')
  const [accountId, setAccountId] = useState(accounts.find((item) => item.kind in kinds)?.id ?? '')
  const [createStock, setCreateStock] = useState(false)
  const [createAccount, setCreateAccount] = useState(false)
  const [stockForm, setStockForm] = useState(initial)
  const [accountForm, setAccountForm] = useState({ name: 'Rachunek akcji', kind: 'STANDARD', currency: 'PLN' })
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [ledgerBusy, setLedgerBusy] = useState(false)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const current = catalogue?.version === refresh ? catalogue : null
  const listings = current?.items ?? []
  const listing = listings.find((item) => item.id === listingId) ?? listings[0]
  const eligible = accounts.filter((item) => item.kind in kinds)
  const account = eligible.find((item) => item.id === accountId) ?? eligible[0]
  const blocked = saving || ledgerBusy

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    void request<Listing[]>('/api/listings?kind=STOCK', { signal: controller.signal })
      .then((items) => { if (active) { setCatalogue({ version: refresh, items }); setLoadError('') } })
      .catch(() => { if (active) setLoadError('Nie udało się pobrać katalogu akcji.') })
    return () => { active = false; controller.abort() }
  }, [refresh])

  async function save(event: FormEvent, mode: 'stock' | 'account') {
    event.preventDefault()
    if (savingRef.current || ledgerBusy) return
    savingRef.current = true; setSaving(true); setMessage(null)
    try {
      if (mode === 'stock') {
        const saved = await request<Listing>('/api/stocks', { method: 'POST', body: JSON.stringify({
          ...stockForm, name: stockForm.name.trim(), symbol: stockForm.symbol.trim().toUpperCase(),
          mic: stockForm.mic.trim().toUpperCase(), isin: stockForm.isin.trim().toUpperCase() || null,
        }) })
        setListingId(saved.id); setCreateStock(false); setStockForm(initial()); setRefresh((value) => value + 1)
        setMessage({ text: 'Spółka została zapisana w katalogu akcji.', error: false })
      } else {
        const saved = await request<Account>('/api/investment-accounts', { method: 'POST', body: JSON.stringify({ ...accountForm, name: accountForm.name.trim() }) })
        setAccountId(saved.id); setCreateAccount(false); onAccountsChanged()
        setMessage({ text: 'Rachunek inwestycyjny został zapisany.', error: false })
      }
    } catch (failure) {
      setMessage({ text: failure instanceof Error ? failure.message : 'Nie udało się zapisać danych.', error: true })
    } finally { savingRef.current = false; setSaving(false) }
  }

  return <section className="purchases-section stocks-section" aria-labelledby="stocks-title">
    <div className="section-heading"><h2 id="stocks-title">Akcje</h2><span>KATALOG I POZYCJE</span></div>
    <p className="valuation-note">Dodaj spółkę z giełdą i walutą notowania, a potem zapisz zakupy i cenę wyceny.
      Dane spółki i ceny wpisujesz ręcznie.</p>
    <div className="form-actions stock-toolbar">
      <button type="button" className="secondary-button" disabled={blocked} aria-expanded={createStock || listings.length === 0}
        onClick={() => setCreateStock((value) => !value)}>Dodaj spółkę</button>
      <button type="button" className="secondary-button" disabled={blocked} aria-expanded={createAccount || !account}
        onClick={() => setCreateAccount((value) => !value)}>Dodaj rachunek akcji</button>
    </div>
    {(createStock || (current && listings.length === 0)) && <form className="purchase-panel stock-catalogue-form" aria-label="Nowa spółka"
      noValidate onSubmit={(event) => { void save(event, 'stock') }}>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <label className="instrument-field" htmlFor="stock-company-name">Nazwa spółki<input id="stock-company-name" required maxLength={200} value={stockForm.name} onChange={(event) => setStockForm((previous) => ({ ...previous, name: event.target.value }))} /></label>
        <label htmlFor="stock-symbol">Ticker akcji<input id="stock-symbol" required maxLength={30} value={stockForm.symbol} onChange={(event) => setStockForm((previous) => ({ ...previous, symbol: event.target.value }))} /></label>
        <label htmlFor="stock-mic">Giełda akcji (MIC)<input id="stock-mic" required maxLength={4} placeholder="np. XWAR" value={stockForm.mic} onChange={(event) => setStockForm((previous) => ({ ...previous, mic: event.target.value }))} /></label>
        <div className="bond-select-field"><label htmlFor="stock-currency">Waluta notowania akcji</label>
          <select id="stock-currency" value={stockForm.currency} onChange={(event) => setStockForm((previous) => ({ ...previous, currency: event.target.value }))}>
            {['PLN', 'EUR', 'USD'].map((currency) => <option key={currency} value={currency}>{currency}</option>)}
          </select></div>
        <label htmlFor="stock-isin">ISIN akcji — opcjonalnie<input id="stock-isin" maxLength={12} value={stockForm.isin} onChange={(event) => setStockForm((previous) => ({ ...previous, isin: event.target.value }))} /></label>
      </div><p className="form-hint">Ticker nie wystarcza do identyfikacji. Podaj giełdę i walutę z potwierdzenia transakcji.</p>
      <button className="primary-button" type="submit">Zapisz spółkę</button></fieldset>
    </form>}
    {(createAccount || !account) && <form className="purchase-panel stock-catalogue-form" aria-label="Nowy rachunek akcji" noValidate onSubmit={(event) => { void save(event, 'account') }}>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <label htmlFor="stock-account-name">Nazwa rachunku akcji<input id="stock-account-name" required maxLength={120} value={accountForm.name} onChange={(event) => setAccountForm((previous) => ({ ...previous, name: event.target.value }))} /></label>
        <div className="bond-select-field"><label htmlFor="stock-account-kind">Typ rachunku akcji</label>
          <select id="stock-account-kind" value={accountForm.kind} onChange={(event) => setAccountForm((previous) => ({ ...previous, kind: event.target.value }))}>
            {Object.entries(kinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></div>
        <div className="bond-select-field"><label htmlFor="stock-account-currency">Waluta bazowa rachunku akcji</label>
          <select id="stock-account-currency" value={accountForm.currency} onChange={(event) => setAccountForm((previous) => ({ ...previous, currency: event.target.value }))}>
            {['PLN', 'EUR', 'USD'].map((currency) => <option key={currency} value={currency}>{currency}</option>)}
          </select></div>
      </div><p className="form-hint">Typ rachunku nie nalicza podatków ani limitów IKE/IKZE. Kwoty pozycji pozostają w walucie notowania.</p>
      <button className="primary-button" type="submit">Zapisz rachunek akcji</button></fieldset>
    </form>}
    {message && <p role={message.error ? 'alert' : 'status'} aria-label="Zapis katalogu akcji" className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}>{message.text}</p>}
    {!current && !loadError && <p role="status">Pobieranie katalogu akcji…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt katalogu akcji</button></div>}
    {current && listings.length === 0 && <p className="empty-purchases">Katalog akcji jest pusty. Dodaj pierwszą spółkę.</p>}
    {listing && <>
      <div className="purchase-account-picker"><label htmlFor="stock-listing">Podgląd akcji</label>
        <select id="stock-listing" value={listing.id} disabled={blocked} onChange={(event) => { setListingId(event.target.value); setMessage(null) }}>
          {listings.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.symbol} · {item.mic} · {item.currency}</option>)}
        </select></div>
      <div className="stock-reference"><strong>{listing.name}</strong><p>{listing.symbol} · {listing.mic} · {listing.currency} · ISIN: {listing.isin ?? 'nie podano'}</p><p>Dane spółki podane ręcznie.</p></div>
      {account && <><div className="purchase-account-picker"><label htmlFor="stock-account">Rachunek akcji</label>
        <select id="stock-account" value={account.id} disabled={blocked} onChange={(event) => { setAccountId(event.target.value); setMessage(null) }}>
          {eligible.map((item) => <option key={item.id} value={item.id}>{item.name} · {kinds[item.kind]}</option>)}
        </select></div>
        <StockPosition key={account.id + '/' + listing.id} accountId={account.id} listing={listing} onBusy={setLedgerBusy}
          disabled={saving || (!!accountId && !eligible.some((item) => item.id === accountId))} /></>}
    </>}
  </section>
}
