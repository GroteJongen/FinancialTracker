# FinancialTracker

Prywatny tracker portfela: React + TypeScript, FastAPI i PostgreSQL. FT-001 dostarcza fundament aplikacji, kontrolę połączenia i lokalny rachunek demonstracyjny IKE. Zakupy IUSQ i obligacje powstaną w kolejnych zadaniach.

## Uruchomienie na Windows

Wymagany Docker Desktop z uruchomionym silnikiem Linux i Docker Compose v2. Python i Node są dostarczane w kontenerach (3.13 i 24); nie musisz instalować ich lokalnie. Pierwsze budowanie wymaga internetu.

W PowerShell, w katalogu repozytorium:

```powershell
Copy-Item .env.example .env
```

Ustaw własne lokalne hasło POSTGRES_PASSWORD w .env, następnie:

```powershell
docker compose up --build -d --wait --wait-timeout 180
```

Otwórz [aplikację](http://127.0.0.1:5173). Backend: [gotowość](http://127.0.0.1:8000/api/health/ready), [dokumentacja API](http://127.0.0.1:8000/docs).

Start czeka na PostgreSQL i wykonuje migrację Alembic. Początkowo lista rachunków jest pusta. Baza nie ma portu wystawionego na hosta; frontend i backend dostępne są wyłącznie lokalnie.

## Opcjonalny rachunek demonstracyjny

```powershell
docker compose exec backend python -m app.seed
```

Komendę można ponawiać. Tworzy jednego syntetycznego właściciela i rachunek „IKE — demonstracja”, bez aktywów i transakcji. Odśwież stronę. LOCAL_OWNER_ID jest konfiguracją serwera, nie mechanizmem logowania lub przełączania użytkowników. Zmiana właściciela wymaga świadomego przygotowania odrębnych danych.

## Zatrzymanie i ponowne uruchomienie

```powershell
docker compose down
docker compose up -d --wait --wait-timeout 180
```

Wolumen postgres-data zachowuje dane. Nie dodawaj -v do zwykłego zatrzymania. Zmiana hasła w .env po inicjalizacji wolumenu nie zmienia automatycznie hasła istniejącego użytkownika bazy.

Po aktualizacji kodu powtórz start z --build. Migracje wykonuje serwis migrate. Ręczna kontrola:

```powershell
docker compose run --rm migrate alembic current
```

## Sprawdzenia

Backend na oddzielnej, efemerycznej bazie PostgreSQL:

```powershell
docker compose --profile test run --build --rm test
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend ruff format --check .
```

TEST_DATABASE_URL musi wskazywać bazę PostgreSQL z końcówką _test. Compose dostarcza oddzielny serwis test-db. Testy nie usuwają tabel aplikacji użytkowej. Usługi można zatrzymać przez docker compose --profile test down, zachowując wolumen aplikacji.

Frontend, opcjonalnie z lokalnym Node 24:

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

Testy przeglądarkowe wymagają działającego Compose i rachunku demonstracyjnego. Node 16 nie jest obsługiwany. npm run dev uruchamia Vite z proxy do backendu; najpierw zwolnij port 5173 przez docker compose stop frontend.

CI sprawdza backend na PostgreSQL, zgodność migracji, izolację rachunków, idempotencję demonstracji, frontend oraz pełny Compose: start, restart, awarię/powrót bazy i rzeczywiste połączenie w przeglądarce.

## Stan weryfikacji

FT-001 jest w trakcie weryfikacji. Wyniki: [raport](docs/verification.md). Na komputerze tworzącym projekt brakuje Dockera i Pythona; dostępny jest Node 16 i ograniczony dostęp sieciowy. Nie oznaczamy niewykonanych lokalnie komend jako zaliczonych. Lockfile zostaną wygenerowane w CI i zapisane w repozytorium; budowanie używa npm ci oraz zahashowanych zależności Pythona.

## Dokumentacja

- [Zakres](docs/product.md)
- [Architektura](docs/architecture.md)
- [Obliczenia](docs/calculations.md)
- [Backlog](docs/backlog.md)
- [Decyzje](docs/decisions.md)
- [Instrukcje agenta](AGENTS.md)

Po odbiorze FT-001 kolejne zadanie to FT-002: instrument IUSQ i zakupy. Nie udostępniaj obecnego trybu lokalnego w internecie.
