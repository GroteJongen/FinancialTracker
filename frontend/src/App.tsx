import { useCallback, useEffect, useState } from 'react'
import Purchases from './purchases/Purchases'
import Stocks from './stocks/Stocks'
import Portfolio from './portfolio/Portfolio'

type Account = { id: string; name: string; kind: string; currency: string }
type Connection =
  | { status: 'loading' }
  | { status: 'ready'; accounts: Account[] }
  | { status: 'error' }

async function getJson(path: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(path, { signal })
  if (!response.ok) throw new Error('Odpowiedź serwera jest niedostępna.')
  return response.json()
}

function isAccount(value: unknown): value is Account {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return ['id', 'name', 'kind', 'currency'].every((key) => typeof item[key] === 'string')
}

export default function App() {
  const [connection, setConnection] = useState<Connection>({ status: 'loading' })
  const [selectedAsset, setSelectedAsset] = useState<{ listingId: string; accountId: string } | null>(null)
  const [operationsOpen, setOperationsOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const refresh = useCallback(() => setRefreshKey((value) => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 12000)
    let active = true
    async function load() {
      try {
        const health = await getJson('/api/health/ready', controller.signal)
        if (typeof health !== 'object' || health === null ||
            !('status' in health) || health.status !== 'ok') throw new Error('Brak gotowości.')
        const accounts = await getJson('/api/accounts', controller.signal)
        if (!Array.isArray(accounts) || !accounts.every(isAccount)) throw new Error('Błędne dane.')
        if (active) setConnection({ status: 'ready', accounts })
      } catch {
        if (active) setConnection({ status: 'error' })
      } finally {
        window.clearTimeout(timeout)
      }
    }
    void load()
    return () => {
      active = false
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [refreshKey])

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="FinancialTracker — strona główna">
          <span className="brand-mark" aria-hidden="true">f<span>t</span></span>
          <span>Financial<span className="brand-light">Tracker</span></span>
        </a>
        <p className="sidebar-caption">TWOJE FINANSE</p>
        <nav aria-label="Nawigacja główna">
          <a className="nav-item active" href="/" aria-current="page">
            <span aria-hidden="true">◫</span> Przegląd portfela <span className="nav-arrow">↗</span>
          </a>
        </nav>
        <div className="sidebar-bottom">
          <span className="local-indicator" /> Tryb lokalny
          <p>Twoja przestrzeń na spokojne decyzje.</p>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>Przegląd portfela</span>
          <span className="private-badge"><span aria-hidden="true">◇</span> Prywatna przestrzeń</span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div><p className="eyebrow">FINANCIALTRACKER / START</p>
              <h1>Portfele inwestycyjne</h1>
              <p className="subtitle">Twoje rachunki i aktywa. W jednym, uporządkowanym miejscu.</p>
            </div>
            <span className="version">WERSJA ROZWOJOWA · 0.1</span>
          </div>
          {connection.status === 'ready' && <Portfolio accounts={connection.accounts} onOpenAsset={(listingId, accountId) => {
            setSelectedAsset({ listingId, accountId }); setOperationsOpen(true)
            window.setTimeout(() => document.getElementById('security-operations')?.scrollIntoView({ behavior: 'smooth' }), 0)
          }} />}
          <div className="section-heading"><h2>Twoje rachunki</h2><span>POŁĄCZENIE Z APLIKACJĄ</span></div>
          <section className="accounts-panel" aria-label="Rachunki" aria-busy={connection.status === 'loading'}>
            {connection.status === 'loading' && <p role="status">Łączenie z aplikacją…</p>}
            {connection.status === 'error' && <div role="alert" className="error-state">
              <h3>Nie udało się połączyć z aplikacją</h3>
              <p>Sprawdź, czy usługi są uruchomione, i spróbuj ponownie.</p>
              <button onClick={() => { setConnection({ status: 'loading' }); refresh() }}>Spróbuj ponownie</button>
            </div>}
            {connection.status === 'ready' && <>
              <div className="connection-ok" role="status" aria-label="Stan połączenia"><span /> Aplikacja i baza danych są połączone</div>
              {connection.accounts.length === 0
                ? <div className="empty-state"><div className="empty-icon" aria-hidden="true">＋</div>
                  <h3>Jeszcze nie masz rachunków</h3>
                  <p>Po przygotowaniu rachunku pojawi się on w tym miejscu.</p>
                  <a className="text-button" href="#security-operations" onClick={() => setOperationsOpen(true)}>Dodaj pierwszy rachunek w sekcji Instrumenty</a>
                </div>
                : <div className="account-grid">{connection.accounts.map((account) =>
                  <article className="account-card" key={account.id}>
                    <div className="account-top"><span className="account-symbol" aria-hidden="true">◈</span>
                      <span className="account-type">{account.kind === 'IKE_BONDS' ? 'IKE' : account.kind === 'STANDARD' ? 'Zwykły' : account.kind}</span></div>
                    <h3>{account.name}</h3><p>Waluta rachunku <strong>{account.currency}</strong></p>
                    <div className="account-footer">Rachunek inwestycyjny</div>
                  </article>,
                )}</div>}
            </>}
          </section>
          <details className="operations-panel" open={operationsOpen} onToggle={(event) => setOperationsOpen(event.currentTarget.open)}><summary>Operacje i katalog aktywów</summary>
          {connection.status === 'ready' && <Stocks key={selectedAsset?.listingId + '/' + selectedAsset?.accountId} accounts={connection.accounts} onAccountsChanged={refresh} focus={selectedAsset} />}
          {connection.status === 'ready' && connection.accounts.some((account) => account.currency === 'EUR') && <details className="etf-operations"><summary>Operacje ETF w EUR</summary>
            <Purchases accounts={connection.accounts.filter((account) => account.currency === 'EUR')} />
          </details>}
          </details>
          <footer>FinancialTracker <span>Przejrzystość na każdym etapie.</span></footer>
        </div>
      </main>
    </div>
  )
}

