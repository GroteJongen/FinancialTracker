import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, formatDate, formatDecimal, request, todayWarsaw } from '../shared/api'
import type { Account, Audit } from '../shared/api'

type BondType = 'TOS' | 'COI' | 'EDO'
type Bond = {
  id: string; account_id: string; series: string; bond_type: BondType; term_years: number
  trade_date: string; quantity: number; unit_price: string; cost: string
  annual_rate: string | null; margin: string | null; source_url: string | null
  interest_mode: 'PAYOUT' | 'CAPITALIZE'; revision: number; created_at: string
}
type Form = {
  bond_type: BondType; series: string; trade_date: string; quantity: string; unit_price: string
  interest_mode: string; annual_rate: string; margin: string; source_url: string; reason: string
}
const terms = { TOS: '3 lata · stałe oprocentowanie', COI: '4 lata · indeksowane inflacją', EDO: '10 lat · indeksowane inflacją' }
const freshForm = (): Form => ({
  bond_type: 'TOS', series: '', trade_date: todayWarsaw(), quantity: '', unit_price: '100,00',
  interest_mode: 'CAPITALIZE', annual_rate: '', margin: '', source_url: '', reason: '',
})
const normalize = (value: string) => value.trim().replace(',', '.')
const canonical = (value: string) => {
  const [whole, fraction = ''] = value.split('.')
  const digits = fraction.replace(/0+$/, '')
  return whole.replace(/^0+(?=[0-9])/, '') + (digits ? '.' + digits : '')
}
const sort = (items: Bond[]) => [...items].sort((a, b) =>
  b.trade_date.localeCompare(a.trade_date) || b.created_at.localeCompare(a.created_at) || a.id.localeCompare(b.id),
)
const accountKinds: Record<string, string> = { STANDARD: 'Zwykły', IKE_BONDS: 'IKE', IKZE: 'IKZE' }

export default function Bonds({ accounts, onAccountsChanged, onBusyChange }: {
  accounts: Account[]; onAccountsChanged: () => void; onBusyChange?: (value: boolean) => void
}) {
  const options = accounts.filter((item) => item.currency === 'PLN' && item.kind in accountKinds)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('Obligacje skarbowe')
  const [kind, setKind] = useState('STANDARD')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [error, setError] = useState('')
  const account = selected ? options.find((item) => item.id === selected) : options[0]

  async function createAccount(event: FormEvent) {
    event.preventDefault()
    if (savingRef.current || busy) return
    savingRef.current = true; setSaving(true); onBusyChange?.(true); setError('')
    try {
      const saved = await request<Account>('/api/bond-accounts', {
        method: 'POST', body: JSON.stringify({ name: name.trim(), kind }),
      })
      setSelected(saved.id); setCreating(false); onAccountsChanged()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nie udało się dodać rachunku.')
    } finally { savingRef.current = false; setSaving(false); onBusyChange?.(false) }
  }

  return <section className="purchases-section bonds-section" aria-labelledby="bonds-title">
    <div className="section-heading"><h2 id="bonds-title">Obligacje skarbowe</h2><span>COI · TOS · EDO · PLN</span></div>
    <p className="valuation-note">Zapisuj zakupy i warunki konkretnej serii. Wartość obligacji naliczamy brutto z uwzględnieniem wypłaty lub kapitalizacji.
      Dla COI i EDO kolejne stopy wynikają z inflacji GUS i marży emisji.</p>
    {selected && !account && <p role="alert">Wybrany rachunek nie istnieje lub nie obsługuje obligacji. Wybierz istniejący rachunek.</p>}
    {!options.length && <p role="status" aria-label="Wymagany rachunek obligacji">Najpierw dodaj rachunek obligacji. Dopiero potem możesz zapisać zakup.</p>}
    <div className="purchase-account-picker">
      {options.length > 0 && <><label htmlFor="bond-account">Rachunek obligacji</label>
        <select id="bond-account" value={account?.id ?? selected} disabled={busy || saving}
          onChange={(event) => setSelected(event.target.value)}>
          {!account && <option value={selected}>Wybierz istniejący rachunek</option>}
          {options.map((item) => <option key={item.id} value={item.id}>{item.name} · {accountKinds[item.kind]}</option>)}
        </select></>}
      <button type="button" className="secondary-button" disabled={busy || saving}
        aria-expanded={creating || !account} onClick={() => setCreating((value) => !value)}>Dodaj rachunek obligacji</button>
    </div>
    {(creating || !account) && <form className="purchase-panel bond-account-form" aria-label="Nowy rachunek obligacji"
      onSubmit={(event) => { void createAccount(event) }}>
      <fieldset disabled={saving || busy}><div className="purchase-form-grid">
        <label htmlFor="bond-account-name">Nazwa rachunku
          <input id="bond-account-name" required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="bond-select-field"><label htmlFor="bond-account-kind">Typ rachunku</label>
          <select id="bond-account-kind" value={kind} onChange={(event) => setKind(event.target.value)}>
            {Object.entries(accountKinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></div>
      </div><p className="form-hint">Waluta: PLN. Typ rachunku służy ewidencji; nie nalicza podatków ani limitów IKE/IKZE.</p>
      <button className="primary-button" type="submit">{saving ? 'Zapisywanie…' : 'Zapisz rachunek obligacji'}</button></fieldset>
    </form>}
    {error && <p role="alert" className="purchase-message message-error">{error}</p>}
    {account && <BondLedger key={account.id} account={account} onBusy={(value) => { setBusy(value); onBusyChange?.(value) }}
      disabled={saving || (!!selected && !options.some((item) => item.id === selected))} />}
  </section>
}

function BondLedger({ account, onBusy, disabled }: {
  account: Account; onBusy: (value: boolean) => void; disabled: boolean
}) {
  const [items, setItems] = useState<Bond[]>([])
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [retry, setRetry] = useState(0)
  const [form, setForm] = useState<Form>(freshForm)
  const [editing, setEditing] = useState<Bond | null>(null)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const submission = useRef<{ fingerprint: string; requestId: string } | null>(null)
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const [auditId, setAuditId] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void request<Bond[]>(`/api/accounts/${account.id}/bonds`, { signal: controller.signal })
      .then((rows) => { if (active) { setItems(sort(rows)); setLoaded(true); setLoadError('') } })
      .catch(() => { if (active) setLoadError('Nie udało się pobrać obligacji. Spróbuj ponownie.') })
    return () => { active = false; controller.abort() }
  }, [account.id, retry])

  function field(key: keyof Form, value: string) { setForm((previous) => ({ ...previous, [key]: value })) }
  function reset() { setEditing(null); setForm(freshForm()); submission.current = null; setMessage(null) }
  function edit(item: Bond) {
    setEditing(item)
    setForm({
      bond_type: item.bond_type, series: item.series, trade_date: item.trade_date,
      quantity: String(item.quantity), unit_price: item.unit_price, annual_rate: item.annual_rate ?? '',
      interest_mode: item.interest_mode, margin: item.margin ?? '', source_url: item.source_url ?? '', reason: '',
    })
    setMessage(null)
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (savingRef.current || disabled) return
    const series = form.series.trim().toUpperCase()
    if (!/^(TOS|COI|EDO)(0[1-9]|1[0-2])[0-9]{2}$/.test(series) || !series.startsWith(form.bond_type)) {
      setMessage({ text: 'Podaj serię zgodną z rodzajem obligacji, np. TOS1129.', error: true }); return
    }
    if (!/^[0-9]{1,9}$/.test(form.quantity.trim()) || /^0+$/.test(form.quantity.trim())) {
      setMessage({ text: 'Liczba obligacji: podaj całkowitą liczbę od 1 do 999999999.', error: true }); return
    }
    if (!form.annual_rate.trim()) {
      setMessage({ text: 'Podaj oprocentowanie roczne: stałe dla TOS lub z pierwszego roku dla COI/EDO.', error: true }); return
    }
    const body = {
      interest_mode: form.interest_mode, series, trade_date: form.trade_date, quantity: Number(form.quantity.trim()),
      unit_price: normalize(form.unit_price), annual_rate: normalize(form.annual_rate) || null,
      margin: form.bond_type === 'TOS' ? null : normalize(form.margin) || null,
      source_url: form.source_url.trim() || null,
    }
    const fingerprint = JSON.stringify({ ...body, unit_price: canonical(body.unit_price),
      annual_rate: body.annual_rate === null ? null : canonical(body.annual_rate),
      margin: body.margin === null ? null : canonical(body.margin),
    })
    if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, requestId: crypto.randomUUID() }
    const payload = editing ? { ...body, expected_revision: editing.revision, reason: form.reason.trim() }
      : { ...body, request_id: submission.current.requestId }
    savingRef.current = true; setSaving(true); onBusy(true); setMessage(null)
    try {
      const saved = await request<Bond>(`/api/accounts/${account.id}/bonds` + (editing ? '/' + editing.id : ''), {
        method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload),
      })
      setItems((previous) => sort([...previous.filter((item) => item.id !== saved.id), saved]))
      reset()
      setMessage({ text: editing ? 'Korekta obligacji została zapisana.' : 'Zakup obligacji został zapisany.', error: false })
    } catch (failure) {
      setMessage({ text: failure instanceof Error ? failure.message : 'Nie udało się zapisać obligacji.', error: true })
      if (failure instanceof ApiError && failure.status === 409) setRetry((value) => value + 1)
    } finally { savingRef.current = false; setSaving(false); onBusy(false) }
  }

  if (!loaded) return <div className="purchase-panel">{loadError
    ? <div role="alert"><p>{loadError}</p><button onClick={() => setRetry((value) => value + 1)}>Ponów odczyt obligacji</button></div>
    : <p role="status">Pobieranie obligacji…</p>}</div>

  return <div className="purchase-panel">
    <div className="purchase-form-heading"><div><h3>{editing ? 'Popraw zakup obligacji' : 'Dodaj zakup obligacji'}</h3>
      <p>Rachunek: {account.name}. Wpisz dane z potwierdzenia zakupu.</p></div><span className="account-type">PLN</span></div>
    <form aria-label={editing ? 'Korekta obligacji' : 'Nowy zakup obligacji'} noValidate onSubmit={(event) => { void save(event) }}>
      <fieldset disabled={saving || disabled}><div className="purchase-form-grid">
        <div className="bond-select-field"><label htmlFor="bond-type">Rodzaj obligacji</label>
          <select id="bond-type" value={form.bond_type} onChange={(event) => setForm((previous) => ({
            ...previous, bond_type: event.target.value as BondType, series: '', margin: '', interest_mode: event.target.value === 'COI' ? 'PAYOUT' : 'CAPITALIZE',
          }))}>{Object.entries(terms).map(([type, text]) => <option key={type} value={type}>{type} · {text}</option>)}</select></div>
        <label htmlFor="bond-series">Seria obligacji
          <input id="bond-series" required maxLength={7} placeholder="np. TOS1129" value={form.series}
            onChange={(event) => field('series', event.target.value.toUpperCase())} /></label>
        <label htmlFor="bond-date">Data zakupu obligacji
          <input id="bond-date" type="date" required max={todayWarsaw()} value={form.trade_date}
            onChange={(event) => field('trade_date', event.target.value)} /></label>
        <label htmlFor="bond-quantity">Liczba obligacji
          <input id="bond-quantity" inputMode="numeric" required placeholder="np. 10" value={form.quantity}
            onChange={(event) => field('quantity', event.target.value)} /></label>
        <label htmlFor="bond-price">Cena jednej obligacji (PLN)
          <input id="bond-price" inputMode="decimal" required value={form.unit_price}
            onChange={(event) => field('unit_price', event.target.value)} /></label>
        <div className="bond-select-field"><label htmlFor="bond-interest-mode">Sposób rozliczania odsetek</label>
          <select id="bond-interest-mode" value={form.interest_mode} onChange={(event) => field('interest_mode', event.target.value)}>
            <option value="CAPITALIZE" disabled={form.bond_type === 'COI'}>Kapitalizacja co roku (TOS / EDO)</option>
            <option value="PAYOUT" disabled={form.bond_type !== 'COI'}>Wypłata co roku (COI)</option>
          </select></div>
        <label htmlFor="bond-rate">Oprocentowanie roczne (%)
          <input id="bond-rate" inputMode="decimal" value={form.annual_rate} placeholder="Z listu emisyjnego"
            onChange={(event) => field('annual_rate', event.target.value)} /></label>
        {form.bond_type !== 'TOS' && <label htmlFor="bond-margin">Marża ponad inflację (%) — opcjonalnie
          <input id="bond-margin" inputMode="decimal" value={form.margin} onChange={(event) => field('margin', event.target.value)} /></label>}
        <label className="instrument-field" htmlFor="bond-source">Link do listu emisyjnego — opcjonalnie
          <input id="bond-source" type="url" maxLength={2000} placeholder="https://…" value={form.source_url}
            onChange={(event) => field('source_url', event.target.value)} /></label>
        {editing && <label className="reason-field" htmlFor="bond-reason">Powód korekty obligacji
          <textarea id="bond-reason" required maxLength={500} rows={2} value={form.reason}
            onChange={(event) => field('reason', event.target.value)} /></label>}
      </div><p className="form-hint">Oprocentowanie: dla TOS stałe, dla COI/EDO z pierwszego roku.
        TOS i EDO kapitalizują odsetki co roku, COI wypłaca je co roku. Brakującą marżę pobieramy dla wskazanej serii; nie zastępujemy inflacji stopą z pierwszego roku.</p>
      <div className="form-actions"><button className="primary-button" type="submit">
        {saving ? 'Zapisywanie…' : editing ? 'Zapisz korektę obligacji' : 'Zapisz zakup obligacji'}</button>
        {editing && <button className="secondary-button" type="button" onClick={reset}>Anuluj korektę obligacji</button>}
      </div></fieldset>
    </form>
    {message && <p role={message.error ? 'alert' : 'status'} aria-label="Wynik zapisu obligacji"
      className={'purchase-message ' + (message.error ? 'message-error' : 'message-success')}>{message.text}</p>}
    {loadError && loaded && <p role="alert">{loadError}</p>}
    <div className="history-heading"><h3>Historia zakupów obligacji</h3><span>{items.length} zapisów</span></div>
    {items.length === 0 ? <p className="empty-purchases">Nie dodano jeszcze obligacji na tym rachunku.</p>
      : <div className="purchase-table-scroll"><table className="purchase-table"><caption className="sr-only">Obligacje na rachunku {account.name}</caption>
        <thead><tr><th>Data</th><th>Seria / okres</th><th>Sztuki</th><th>Cena (PLN)</th><th>Koszt (PLN)</th><th>Warunki</th><th>Działania</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id}>
          <td>{formatDate(item.trade_date)}</td><td><strong>{item.series}</strong><br />{item.term_years} {item.term_years === 3 || item.term_years === 4 ? 'lata' : 'lat'}</td>
          <td>{item.quantity}</td><td>{formatDecimal(item.unit_price, 2)}</td><td>{formatDecimal(item.cost, 2)}</td>
          <td>{item.annual_rate === null ? 'Brak stopy' : formatDecimal(item.annual_rate) + '%'}
            {item.margin !== null && <><br />Marża: {formatDecimal(item.margin)}%</>}<br />Podane ręcznie
            {item.source_url && <><br /><a className="text-button" href={item.source_url} target="_blank" rel="noopener noreferrer">Dokument emisji</a></>}</td>
          <td className="row-actions"><button type="button" className="text-button" disabled={saving || disabled} onClick={() => edit(item)}>Popraw obligacje</button>
            <button type="button" className="text-button" disabled={saving || disabled} aria-expanded={auditId === item.id}
              onClick={() => setAuditId((previous) => previous === item.id ? null : item.id)}>Zmiany obligacji</button></td>
        </tr>)}</tbody></table></div>}
    {auditId && <BondHistory key={auditId + ':' + items.find((item) => item.id === auditId)?.revision} accountId={account.id} purchaseId={auditId} />}
  </div>
}

function BondHistory({ accountId, purchaseId }: { accountId: string; purchaseId: string }) {
  const [events, setEvents] = useState<Audit[] | null>(null)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void request<Audit[]>(`/api/accounts/${accountId}/bonds/${purchaseId}/audit`, { signal: controller.signal })
      .then((rows) => { if (active) { setEvents(rows); setError(false) } })
      .catch(() => { if (active) setError(true) })
    return () => { active = false; controller.abort() }
  }, [accountId, purchaseId, retry])
  return <section className="audit-history" aria-label="Historia zmian obligacji"><h3>Historia zmian obligacji</h3>
    {error ? <div role="alert">Nie udało się odczytać historii. <button onClick={() => setRetry((value) => value + 1)}>Ponów odczyt zmian</button></div>
      : events === null ? <p role="status">Pobieranie historii…</p> : <ol>{events.map((event) => <li key={event.id}>
        <div className="audit-heading"><strong>Wersja {event.revision} · {event.kind === 'CREATE' ? 'Dodanie' : 'Korekta'}</strong>
          <span>{new Date(event.created_at).toLocaleString('pl-PL', { timeZone: 'Europe/Warsaw' })}</span></div>
        {event.reason && <p className="audit-reason">{event.reason}</p>}
        <dl>{(['series', 'trade_date', 'quantity', 'unit_price', 'annual_rate', 'margin', 'source_url'] as const).map((key) => {
          const labels = { series: 'Seria', trade_date: 'Data zakupu', quantity: 'Sztuki', unit_price: 'Cena (PLN)', annual_rate: 'Oprocentowanie (%)', margin: 'Marża (%)', source_url: 'Dokument emisji' }
          return <div key={key}><dt>{labels[key]}</dt><dd>{event.before && <span>{event.before[key] || '—'} → </span>}{event.after[key] || '—'}</dd></div>
        })}</dl>
      </li>)}</ol>}
  </section>
}
