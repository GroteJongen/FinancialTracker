# FinancialTracker

Prywatny tracker portfela: React + TypeScript, FastAPI i PostgreSQL. Aplikacja obsluguje wlasne portfele grupujace rachunki, rozne ETF-y, akcje, gieldowe REIT-y i obligacje, z historia zakupow i wycen. Dodawanie obligacji COI, TOS i EDO opisuje [instrukcja](docs/bonds.md). Kursy ETF/akcji pobieramy z Yahoo Finance; TOS, COI i EDO maja automatyczne naliczanie odsetek brutto, z kapitalizacja lub kuponami oraz historyczna inflacja GUS i marza konkretnej emisji. Frontend i backend pozostają w jednym repozytorium, z osobnymi katalogami, obrazami i zadaniami CI.

Dodawanie instrumentu w sekcji „Instrumenty” wymaga wyboru istniejącego rachunku. Jeśli nie masz zgodnego rachunku, najpierw utwórz go w pokazanym formularzu. Nieistniejący lub niedostępny rachunek powoduje komunikat błędu, a wpisane dane instrumentu pozostają zachowane.

## Historia zakupów instrumentu

W sekcji „Instrumenty” karta „Historia zakupów instrumentu” łączy wybór instrumentu i rachunku z listą zakupów. Wyszukiwanie filtruje bieżącą listę po dacie, liczbie jednostek, cenie, prowizji lub lacznym koszcie zakupu; sortowanie po dacie działa w obu kierunkach (domyślnie najnowsze). „Popraw instrument” otwiera korektę wybranego zakupu, wymagającą powodu; „Zmiany instrumentu” pokazuje audyt. Formularz korekty jest domyślnie ukryty.

Panel Pozycja, kafelki wyceny, formularze ręcznej ceny i nowego zakupu oraz historia cen zostały usunięte z tego widoku. Wartości aktywów i wynik są prezentowane w dashboardzie. Istniejące zakupy, ceny i audyt pozostają w bazie; wspólne API finansowe i integracje nadal działają. Zmiany historii nie usuwaja danych. Naliczanie obligacji wymaga migracji 0010, wykonywanej przy aktualizacji aplikacji.

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

## Gotowe obrazy GHCR

Po merge do main i zaliczeniu CI publikowane sa obrazy frontendu i backendu ze wspolnym tagiem commita. Pobierasz je recznie, bez harmonogramu:

```powershell
.\scripts\update.ps1 -PullOnly
```

Pobranie i uruchomienie nowego wydania z migracjami: `.\scripts\update.ps1`.
Nowe pakiety sa domyslnie prywatne; pierwsze pobranie moze wymagac `docker login ghcr.io -u GroteJongen` z tokenem classic read:packages. Obrazy pojawia sie po pierwszym udanym publish-images na main. Zachowaj dotychczasowy .env i wolumen bazy. [Pelna instrukcja i reczne polecenia Compose](docs/ghcr.md).

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

FT-003 przeszedł pełny przebieg CI: 73 testy backendu, 12 testów przeglądarkowych, budowanie oraz zachowanie ręcznej ceny i wyniku po restarcie kontenerów. Szczegóły w verification.md. Kolejne zadanie to FT-004: odbiór pierwszej wersji i sprawdzenie kopii zapasowych. Nie udostępniaj obecnego trybu lokalnego w internecie.

## Zakupy obligacji

Sekcja „Obligacje skarbowe” pozwala tworzyć rachunki PLN (zwykły, IKE, IKZE), zapisywać serie i zakupy COI/TOS/EDO oraz poprawiać dane z historią zmian. Opcjonalne parametry emisji są podane ręcznie i niezweryfikowane. Koszt zakupu nie jest bieżącą wyceną; odsetki i podatki nie są naliczane. Pełna [instrukcja i kontrakt API](docs/bonds.md).

## Instrumenty gieldowe

Sekcja „Instrumenty” w panelu operacji pozwala dodawac ETF-y, akcje i gieldowe REIT-y, wybierac notowania, zapisywac zakupy, ceny oraz korekty z audytem. Waluty: PLN, EUR, USD. [Zasady portfeli i katalogu](docs/portfolios.md).

## Dashboard portfela

„Mój portfel” pokazuje koszt, wartość aktywów i wynik w PLN, filtry zwykłe/IKE/IKZE/wszystkie oraz wykres udziałów. Wyceny giełdowe pochodzą z Yahoo Finance lub wpisów ręcznych; dla obligacji można zapisać bieżącą wartość i skumulowane wypłacone odsetki brutto. Waluty wymagają pobrania referencyjnych kursów NBP. Braki nie są traktowane jako zero. [Zasady i ograniczenia](docs/portfolio.md).

## Kursy Yahoo Finance

Po otwarciu lub odswiezeniu aplikacji pobieramy ceny posiadanych ETF/akcji z Yahoo, najwyzej raz na 5 minut na notowanie. IUSQ.DE jest ustawiony automatycznie; symbole akcji przypiszesz w dashboardzie, w „Automatyczne kursy Yahoo Finance”. Wyceny moga byc opoznione (Xetra okolo 15 minut). Ostatnia poprawna cena zostaje przy awarii; nowsza reczna wycena ma pierwszenstwo. Brak klucza i platnego API. [Obsluga, pierwszenstwo i ograniczenia](docs/yahoo.md).

## Wlasne portfele i katalog aktywow

Wybierz lub utworz portfel grupujacy rachunki. Podsumowanie i tabela dotycza tego portfela oraz wybranego filtra IKE/IKZE. Lista pokazuje liczbe jednostek, nazwe, cene jednostki, wartosc oraz wynik kwotowo i procentowo. Operacje i katalog aktywow otwierasz ponizej lub nazwa instrumentu w tabeli. Katalog obsluguje rozne ETF-y, akcje i gieldowe REIT-y; obligacje pozostaja we wspolnym podsumowaniu. [Zasady, zgodnosc i ograniczenia](docs/portfolios.md).

Kursy NBP do podsumowania w PLN pobierają się automatycznie po otwarciu strony. Brakujące kursy historyczne uzupełniane są partiami. Przy niedostępności NBP pozostają poprzednie dane i znane kwoty w walucie instrumentu; przycisk NBP pozwala ponowić pobranie.
