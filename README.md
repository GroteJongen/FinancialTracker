# FinancialTracker

Prywatny tracker portfela: React + TypeScript, FastAPI i PostgreSQL. Aplikacja zawiera zakupy IUSQ, korekty, historię zmian i ręczną wycenę pozycji z wynikiem w EUR. Automatyczne kursy, PLN i obligacje dodamy w kolejnych etapach. Frontend i backend pozostają w jednym repozytorium, z osobnymi katalogami, obrazami i zadaniami CI.

## Zakupy IUSQ

Po utworzeniu rachunku demonstracyjnego wybierz go w sekcji „Zakupy IUSQ”. Wpisz datę, liczbę jednostek, cenę i prowizję w EUR. Jednostki ułamkowe oraz kwoty obsługują do 8 miejsc po przecinku. Formularz przyjmuje przecinek lub kropkę; backend zapisuje dokładne wartości dziesiętne, odrzuca wartości ujemne, zerową ilość/cenę oraz przyszłe daty według Europe/Warsaw.

„Popraw” otwiera korektę wymagającą powodu. „Zmiany” pokazuje poprzednie i nowe wartości oraz czas korekty. Zapis zakupu i audytu jest atomowy. Ponowienie zapisu po utracie odpowiedzi nie tworzy drugiego zakupu; równoczesne korekty tej samej wersji powodują konflikt, który wymaga odświeżenia historii. Audyt nie ma endpointu edycji ani usuwania; administrator bazy nadal ma techniczny dostęp do danych.

Migracja 0002 dodaje katalog IUSQ (ISIN IE00B6R52259, Xetra/XETR, EUR), nie dodaje żadnych transakcji i zachowuje wcześniejsze rachunki. Rzeczywiste zakupy dodaje użytkownik. Dane demonstracyjne są opcjonalne. Lista zakupów pokazuje dane transakcyjne, nie aktualną wycenę ani wynik inwestycji.

## Ręczna wycena IUSQ

W sekcji „Wycena IUSQ” wpisz cenę jednostki w EUR i datę. Aplikacja pokaże ilość jednostek, łączny koszt z prowizjami, średni koszt, wartość pozycji i niezrealizowany wynik kwotowo oraz procentowo. Przykład: 10 jednostek po 100 EUR i 2 EUR prowizji, wycenionych po 110 EUR, daje wartość 1100 EUR i wynik 98 EUR (9,78%).

Data ceny musi mieścić się pomiędzy ostatnim zakupem a dniem bieżącym według Europe/Warsaw. Późniejszy zakup lub korekta daty mogą sprawić, że cena będzie zbyt stara. Wtedy zobaczysz prośbę o aktualizację, a wartość pozycji i wynik będą niedostępne. Ilość i koszt zakupów pozostaną widoczne. Brak ceny także oznacza brak wyceny, nie wynik zerowy.

Ceny są prywatne dla rachunku i notowania. Każdy zapis zachowuje cenę, datę, źródło ręczne i czas zapisu; historię rozwiniesz pod formularzem. Najnowsza data ceny ma pierwszeństwo, a w obrębie tej samej daty wybierany jest ostatni zapis. Starsza data dodana później nie zastępuje nowszej. Ponowienie po utracie odpowiedzi nie dopisuje duplikatu. Wynik aktualizuje się po zakupie lub korekcie, bez ręcznego odświeżania strony.

Obliczenia używają Decimal i co najmniej 38 cyfr precyzji; prezentacja EUR i procentu stosuje ROUND_HALF_UP do 2 miejsc. Wynik nie obejmuje podatku ani przyszłych kosztów sprzedaży. Ceny bieżące nie są jeszcze pobierane automatycznie.

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

Testy przeglądarkowe wykonuj wyłącznie na oddzielnej instancji z syntetycznymi danymi. Dodają zakupy, korekty i ceny do rachunków testowych. Przed ich uruchomieniem przygotuj demonstrację oraz puste rachunki testowe:

```powershell
docker compose exec backend python -m app.seed
docker compose exec backend python -m tests.seed_browser
```

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

FT-001 przeszedł pełną weryfikację w GitHub Actions: 4 testy backendu, 4 testy przeglądarkowe, typy/lint/build frontendu, kontrola migracji, start/restart Compose oraz awaria i powrót bazy. Szczegóły: [raport](docs/verification.md).

Na komputerze tworzącym projekt brakuje Dockera i Pythona; dostępny jest Node 16 i ograniczony dostęp sieciowy. Aplikacja nie została uruchomiona na tym komputerze. Powyższe polecenia startu, migracji, demonstracji i restartu sprawdzono na runnerze Linux w CI. Lockfile są zapisane w repozytorium; budowanie używa npm ci i zahashowanych zależności Pythona. Polecenie profilu testowego Compose jest przygotowane, ale testy backendu w CI używały oddzielnego serwisu PostgreSQL runnera, więc ten wariant lokalny pozostaje do sprawdzenia na Windows.

## Dokumentacja

- [Zakres](docs/product.md)
- [Architektura](docs/architecture.md)
- [Obliczenia](docs/calculations.md)
- [Backlog](docs/backlog.md)
- [Decyzje](docs/decisions.md)
- [Instrukcje agenta](AGENTS.md)

FT-003 przeszedł wstępny przebieg CI: 73 testy backendu, 12 testów przeglądarkowych i budowanie. Końcowe sprawdzenie ceny po restarcie jest w toku; szczegóły w verification.md. Kolejne zadanie to FT-004: odbiór pierwszej wersji i sprawdzenie kopii zapasowych. Nie udostępniaj obecnego trybu lokalnego w internecie.
