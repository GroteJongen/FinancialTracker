import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { request } from '../shared/api'
import type { Account, Listing } from '../shared/api'
import PurchaseHistory from './PurchaseHistory'
import Bonds from '../bonds/Bonds'

const initial = () => ({ name: '', symbol: '', mic: '', currency: 'PLN', isin: '', kind: 'STOCK' })
const kinds: Record<string, string> = { STANDARD: 'Zwykły', IKE: 'IKE', IKZE: 'IKZE' }

export default function Instruments({ accounts, onAccountsChanged, focus }: { accounts: Account[]; onAccountsChanged: () => void; focus?: { listingId: string; accountId: string } | null }) {
  const [refresh, setRefresh] = useState(0)
  const [catalogue, setCatalogue] = useState<{ version: number; items: Listing[] } | null>(null)
  const [loadError, setLoadError] = useState('')
  const [listingId, setListingId] = useState(focus?.listingId ?? '')
  const [accountId, setAccountId] = useState(focus?.accountId ?? '')
  const [instrumentAccountId, setInstrumentAccountId] = useState('')
  const [createStock, setCreateStock] = useState(false)
  const [createAccount, setCreateAccount] = useState(false)
  const [stockForm, setStockForm] = useState(initial)
  const [accountForm, setAccountForm] = useState({ name: 'Rachunek instrumentu', kind: 'STANDARD', currency: 'PLN' })
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [ledgerBusy, setLedgerBusy] = useState(false)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const current = catalogue?.version === refresh ? catalogue : null
  const listings = current?.items ?? []
  const listing = listings.find((item) => item.id === listingId) ?? listings[0]
  const eligible = accounts.filter((item) => item.kind in kinds)
  const account = eligible.find((item) => item.id === accountId) ?? eligible.find((item) => listing?.account_ids?.includes(item.id)) ?? eligible[0]
  const draftAccountId = instrumentAccountId || account?.id || ''
  const draftAccount = eligible.find((item) => item.id === draftAccountId)
  const blocked = saving || ledgerBusy

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    void request<Listing[]>('/api/listings?kind=ALL', { signal: controller.signal })
      .then((items) => { if (active) { setCatalogue({ version: refresh, items }); setLoadError('') } })
      .catch(() => { if (active) setLoadError('Nie udało się pobrać katalogu instrumentu.') })
    return () => { active = false; controller.abort() }
  }, [refresh])

  async function save(event: FormEvent, mode: 'stock' | 'account') {
    event.preventDefault()
    if (savingRef.current || ledgerBusy) return
    if (mode === 'stock' && !draftAccount) {
      setMessage({ text: eligible.length ? 'Wybrany rachunek nie istnieje lub jest niedostępny. Wybierz istniejący rachunek.' : 'Najpierw dodaj rachunek, aby zapisać instrument.', error: true }); return
    }
    savingRef.current = true; setSaving(true); setMessage(null)
    try {
      if (mode === 'stock') {
        const saved = await request<Listing>('/api/securities', { method: 'POST', body: JSON.stringify({
          ...stockForm, account_id: draftAccountId, name: stockForm.name.trim(), symbol: stockForm.symbol.trim().toUpperCase(),
          mic: stockForm.mic.trim().toUpperCase(), isin: stockForm.isin.trim().toUpperCase() || null,
        }) })
        setAccountId(draftAccountId); setListingId(saved.id); setCreateStock(false); setStockForm(initial()); setRefresh((value) => value + 1)
        setMessage({ text: 'Instrument został zapisany w katalogu instrumentu.', error: false })
      } else {
        const saved = await request<Account>('/api/investment-accounts', { method: 'POST', body: JSON.stringify({ ...accountForm, name: accountForm.name.trim() }) })
        setAccountId(saved.id); setInstrumentAccountId(saved.id); setCreateAccount(false); onAccountsChanged()
        setMessage({ text: 'Rachunek inwestycyjny został zapisany.', error: false })
      }
    } catch (failure) {
      setMessage({ text: failure instanceof Error ? failure.message : 'Nie udało się zapisać danych.', error: true })
    } finally { savingRef.current = false; setSaving(false) }
  }

  return <section id="security-operations" className="purchases-section stocks-section" aria-labelledby="stocks-title">
    <div className="section-heading"><h2 id="stocks-title">Instrumenty</h2><span>KATALOG I POZYCJE</span></div>
    <p className="valuation-note">Wybierz rodzaj aktywa: akcje, ETF, REIT lub obligacje. Formularz dopasuje się do wybranego rodzaju.
      Dane instrumentu i ceny wpisujesz ręcznie.</p>
    <div className="form-actions stock-toolbar">
      <button type="button" className="secondary-button" disabled={blocked} aria-expanded={createStock || listings.length === 0}
        onClick={() => setCreateStock((value) => !value)}>Dodaj instrument</button>
      {stockForm.kind !== 'BOND' && <button type="button" className="secondary-button" disabled={blocked} aria-expanded={createAccount || !account}
        onClick={() => setCreateAccount((value) => !value)}>Dodaj rachunek instrumentu</button>}
    </div>
    {(createStock || (current && listings.length === 0)) && <div className="purchase-panel stock-catalogue-form">
      <div className="purchase-form-grid"><div className="bond-select-field"><label htmlFor="security-kind">Rodzaj aktywa</label>
        <select id="security-kind" disabled={blocked} value={stockForm.kind} onChange={(event) => { setStockForm({ ...stockForm, kind: event.target.value }); setMessage(null) }}>
          <option value="STOCK">Akcje</option><option value="ETF">ETF</option><option value="REIT">REIT giełdowy</option><option value="BOND">Obligacje</option>
        </select></div></div>
      {stockForm.kind === 'BOND' ? <Bonds accounts={accounts} onAccountsChanged={onAccountsChanged} onBusyChange={setLedgerBusy} /> :
        eligible.length === 0 ? <p role="status" aria-label="Wymagany rachunek">Nie masz rachunku dla tego rodzaju instrumentu. Najpierw dodaj rachunek w formularzu poniżej.</p> : <form aria-label="Nowy instrument" noValidate onSubmit={(event) => { void save(event, 'stock') }}>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <div className="bond-select-field"><label htmlFor="instrument-account">Rachunek dla nowego instrumentu</label>
          <select id="instrument-account" required value={draftAccountId} onChange={(event) => { setInstrumentAccountId(event.target.value); setMessage(null) }}>
            {!draftAccount && <option value={draftAccountId}>Wybierz istniejący rachunek</option>}
            {eligible.map((item) => <option key={item.id} value={item.id}>{item.name} · {kinds[item.kind]}</option>)}
          </select></div>
        <label className="instrument-field" htmlFor="stock-company-name">Nazwa instrumentu<input id="stock-company-name" required maxLength={200} value={stockForm.name} onChange={(event) => setStockForm((previous) => ({ ...previous, name: event.target.value }))} /></label>
        <label htmlFor="stock-symbol">Ticker instrumentu<input id="stock-symbol" required maxLength={30} value={stockForm.symbol} onChange={(event) => setStockForm((previous) => ({ ...previous, symbol: event.target.value }))} /></label>
        <label htmlFor="stock-mic">Giełda instrumentu (MIC)<input id="stock-mic" required maxLength={4} placeholder="np. XWAR" value={stockForm.mic} onChange={(event) => setStockForm((previous) => ({ ...previous, mic: event.target.value }))} /></label>
        <div className="bond-select-field"><label htmlFor="stock-currency">Waluta notowania instrumentu</label>
          <select id="stock-currency" value={stockForm.currency} onChange={(event) => setStockForm((previous) => ({ ...previous, currency: event.target.value }))}>
            {['PLN', 'EUR', 'USD'].map((currency) => <option key={currency} value={currency}>{currency}</option>)}
          </select></div>
        <label htmlFor="stock-isin">ISIN instrumentu — opcjonalnie<input id="stock-isin" maxLength={12} value={stockForm.isin} onChange={(event) => setStockForm((previous) => ({ ...previous, isin: event.target.value }))} /></label>
      </div><p className="form-hint">Ticker nie wystarcza do identyfikacji. Podaj giełdę i walutę z potwierdzenia transakcji.</p>
      <button className="primary-button" type="submit">Zapisz instrument</button></fieldset>
    </form>}
    </div>}
    {stockForm.kind !== 'BOND' && (createAccount || !account) && <form className="purchase-panel stock-catalogue-form" aria-label="Nowy rachunek instrumentu" noValidate onSubmit={(event) => { void save(event, 'account') }}>
      <fieldset disabled={blocked}><div className="purchase-form-grid">
        <label htmlFor="stock-account-name">Nazwa rachunku instrumentu<input id="stock-account-name" required maxLength={120} value={accountForm.name} onChange={(event) => setAccountForm((previous) => ({ ...previous, name: event.target.value }))} /></label>
        <div className="bond-select-field"><label htmlFor="stock-account-kind">Typ rachunku instrumentu</label>
          <select id="stock-account-kind" value={accountForm.kind} onChange={(event) => setAccountForm((previous) => ({ ...previous, kind: event.target.value }))}>
            {Object.entries(kinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></div>
        <div className="bond-select-field"><label htmlFor="stock-account-currency">Waluta bazowa rachunku instrumentu</label>
          <select id="stock-account-currency" value={accountForm.currency} onChange={(event) => setAccountForm((previous) => ({ ...previous, currency: event.target.value }))}>
            {['PLN', 'EUR', 'USD'].map((currency) => <option key={currency} value={currency}>{currency}</option>)}
          </select></div>
      </div><p className="form-hint">Typ rachunku nie nalicza podatków ani limitów IKE/IKZE. Kwoty pozycji pozostają w walucie notowania.</p>
      <button className="primary-button" type="submit">Zapisz rachunek instrumentu</button></fieldset>
    </form>}
    {message && <p role={message.error ? 'alert' : 'status'} aria-label="Zapis katalogu instrumentu" className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}>{message.text}</p>}
    {!current && !loadError && <p role="status">Pobieranie katalogu instrumentu…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => setRefresh((value) => value + 1)}>Ponów odczyt katalogu instrumentu</button></div>}
    {current && listings.length === 0 && <p className="empty-purchases">Katalog instrumentu jest pusty. Dodaj pierwszy instrument.</p>}
    {stockForm.kind !== 'BOND' && listing && <>
      <div className="purchase-account-picker"><label htmlFor="stock-listing">Wybierz instrument</label>
        <select id="stock-listing" value={listing.id} disabled={blocked} onChange={(event) => { setListingId(event.target.value); setAccountId(''); setMessage(null) }}>
          {listings.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.symbol} · {item.mic} · {item.currency}</option>)}
        </select></div>
      <div className="stock-reference"><strong>{listing.name}</strong><p>{listing.symbol} · {listing.mic} · {listing.currency} · ISIN: {listing.isin ?? 'nie podano'}</p><p>Dane instrumentu podane ręcznie.</p></div>
      {account && <><div className="purchase-account-picker"><label htmlFor="stock-account">Rachunek instrumentu</label>
        <select id="stock-account" value={account.id} disabled={blocked} onChange={(event) => { setAccountId(event.target.value); setMessage(null) }}>
          {eligible.map((item) => <option key={item.id} value={item.id}>{item.name} · {kinds[item.kind]}</option>)}
        </select></div>
        <PurchaseHistory key={account.id + '/' + listing.id} accountId={account.id} listing={listing} onBusy={setLedgerBusy}
          disabled={saving || (!!accountId && !eligible.some((item) => item.id === accountId))} /></>}
    </>}
  </section>
}
