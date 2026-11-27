import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { request } from '../purchases/api'
import type { Account } from '../purchases/api'

type Group = { id: string; name: string; revision: number; account_ids: string[] }
export default function PortfolioPicker({ accounts, value, onChange }: {
  accounts: Account[]; value: string; onChange: (value: string) => void
}) {
  const [groups, setGroups] = useState<Group[]>([])
  const [version, setVersion] = useState(0)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState<{ group: Group | null; name: string; ids: string[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const saving = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void request<Group[]>('/api/portfolios', { signal: controller.signal }).then((rows) => { if (active) { setGroups(rows); setError('') } })
      .catch(() => { if (!controller.signal.aborted) setError('Nie udało się pobrać listy portfeli.') })
    return () => { active = false; controller.abort() }
  }, [version])
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!draft || saving.current) return
    saving.current = true; setBusy(true); setError('')
    try {
      const row = await request<Group>('/api/portfolios' + (draft.group ? '/' + draft.group.id : ''), {
        method: draft.group ? 'PUT' : 'POST',
        body: JSON.stringify({ name: draft.name.trim(), account_ids: draft.ids, ...(draft.group ? { expected_revision: draft.group.revision } : {}) }),
      })
      setGroups((previous) => [...previous.filter((item) => item.id !== row.id), row]); setVersion((n) => n + 1); setDraft(null); onChange(row.id)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Nie udało się zapisać portfela.'); setVersion((n) => n + 1) }
    finally { saving.current = false; setBusy(false) }
  }
  const selected = groups.find((row) => row.id === value)
  return <div className="portfolio-picker">
    <div className="portfolio-picker-bar"><label htmlFor="portfolio-select">Portfel
      <select id="portfolio-select" value={value} disabled={busy} onChange={(event) => { onChange(event.target.value); setDraft(null) }}>
        <option value="">Wszystkie rachunki</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
      </select></label>
      <button type="button" className="secondary-button" disabled={busy} onClick={() => { setDraft({ group: null, name: '', ids: [] }); setError('') }}>Nowy portfel</button>
      {selected && <button type="button" className="text-button" disabled={busy} onClick={() => { setDraft({ group: selected, name: selected.name, ids: [...selected.account_ids] }); setError('') }}>Edytuj portfel</button>}
    </div>
    {draft && <form aria-label={draft.group ? 'Edycja portfela' : 'Nowy portfel'} className="portfolio-group-form" onSubmit={(event) => { void save(event) }}>
      <fieldset disabled={busy}><label>Nazwa portfela<input value={draft.name} required maxLength={120} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
        <legend>Rachunki w portfelu</legend>
        {accounts.length === 0 && <p>Dodaj rachunek w sekcji operacji, a następnie przypisz go do portfela.</p>}
        {accounts.map((account) => <label key={account.id} className="portfolio-account-check"><input type="checkbox" checked={draft.ids.includes(account.id)} onChange={(event) => setDraft({ ...draft, ids: event.target.checked ? [...draft.ids, account.id] : draft.ids.filter((id) => id !== account.id) })} />{account.name} · {account.kind === 'IKE_BONDS' ? 'IKE' : account.kind === 'STANDARD' ? 'Zwykły' : account.kind}</label>)}
        <p className="form-hint">Rachunek może należeć do kilku portfeli. Widok wszystkich rachunków liczy go tylko raz.</p>
        <div className="form-actions"><button type="submit" className="primary-button">Zapisz portfel</button><button type="button" className="text-button" onClick={() => setDraft(null)}>Anuluj portfel</button></div>
      </fieldset></form>}
    {error && <p role="alert">{error}</p>}
  </div>
}
