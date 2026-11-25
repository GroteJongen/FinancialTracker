# FinancialTracker

Prywatny tracker portfela, projektowany z myślą o kolejnych klasach aktywów.

## Stan projektu

Przygotowano specyfikację i zadania implementacyjne. Nie ma jeszcze kodu aplikacji ani działających poleceń uruchomienia. Pierwszym zadaniem agenta jest FT-001 z docs/backlog.md.

## Uzgodniony kierunek

- Interfejs po polsku, uruchamianie lokalnie na Windows przez przeglądarkę.
- React, TypeScript i Vite; Python i FastAPI; PostgreSQL, SQLAlchemy i Alembic.
- Docker Compose do lokalnego uruchamiania; pytest i Playwright do sprawdzania aplikacji.
- Pierwszy instrument: IUSQ, ISIN IE00B6R52259, notowanie Xetra w EUR.
- Rachunek IKE; dokładny broker pozostaje do ustalenia.
- Kolejne moduły: kursy automatyczne, PLN, obligacje TOS, COI i EDO.

## Dokumentacja

1. [Zakres produktu](docs/product.md)
2. [Architektura i model danych](docs/architecture.md)
3. [Zasady obliczeń](docs/calculations.md)
4. [Zadania i kryteria odbioru](docs/backlog.md)
5. [Decyzje projektowe](docs/decisions.md)
6. [Instrukcje dla agenta](AGENTS.md)

## Rozpoczęcie pracy z agentem

Otwórz katalog FinancialTracker jako katalog projektu i użyj zadania:

> Przeczytaj AGENTS.md i dokumenty w docs. Zrealizuj FT-001 z docs/backlog.md. Zainicjalizuj lokalne repozytorium Git, jeśli go nie ma. Nie publikuj go. Zbuduj szkielet środowiska, migrację początkową i sprawdzenia opisane w zadaniu. Uzupełnij README rzeczywistymi komendami uruchomienia i testów. Wykonaj dostępne sprawdzenia i podaj ich wyniki oraz ograniczenia. Nie rozpoczynaj FT-002.

## Sprawy do ustalenia później

- Broker: przed projektowaniem importów raportów.
- Zwykły rachunek czy IKE-Obligacje: przed obsługą obligacji i podatków.
- Serie i daty zakupów obligacji: przed wdrożeniem ich wyceny.
- Dostępność Docker Desktop i narzędzi: podczas FT-001.

Żaden z tych punktów nie blokuje przygotowania fundamentu. Dane demonstracyjne muszą być syntetyczne.
