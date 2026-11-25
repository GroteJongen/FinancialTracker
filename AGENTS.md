# Instrukcje agenta — FinancialTracker

## Kontekst

Budujemy rozszerzalny, prywatny tracker finansowy. Przeczytaj README.md oraz docs/product.md, architecture.md, calculations.md, backlog.md i decisions.md przed implementacją. Instrukcje użytkownika mają pierwszeństwo.

## Sposób pracy

- Realizuj jedno gotowe zadanie z backlogu. Zachowuj jego zakres i kryteria odbioru.
- Najpierw sprawdź istniejące pliki, status Git i dostępne narzędzia; nie nadpisuj pracy użytkownika.
- Podejmuj odwracalne decyzje implementacyjne samodzielnie. Zapisuj istotne decyzje w docs/decisions.md.
- Zmiany przygotuj na osobnej gałęzi. Nie publikuj repozytorium ani aplikacji bez zlecenia.
- Po zadaniu zaktualizuj jego status, dokumentację i rzeczywiste komendy. Podaj wykonane sprawdzenia, wyniki i ograniczenia. Nie oznaczaj niewykonanego testu jako zaliczonego.
- Przerwij zależną część pracy, jeśli brakuje źródłowych zasad finansowych. Nie zgaduj warunków emisji ani podatków. Kontynuuj niezależne części.

## Architektura

- Jeden backend podzielony na moduły, jeden frontend, jedna baza PostgreSQL.
- Logika finansowa w backend/app/domain, bez zależności od HTTP, ORM i zewnętrznych API.
- Integracje dostawców oddzielone od modelu domenowego. Brak automatycznego przełączania giełdy lub waluty instrumentu.
- Migracje Alembic dla każdej zmiany bazy. Nie używaj create_all jako zamiennika migracji.
- Przypnij wybrane stabilne wersje zależności i zapisz lockfile. Nie aktualizuj ich bez powodu.

## Dokładność i dane

- Decimal tworzony z tekstu; pieniądze i jednostki w PostgreSQL jako NUMERIC o uzasadnionej precyzji. W JSON przekazuj wartości dziesiętne jako tekst.
- Nie używaj float do trwałych wartości ani obliczeń finansowych. Wykres może otrzymać przybliżoną liczbę po obliczeniach.
- Daty transakcji jako daty kalendarzowe; znaczniki techniczne jako czas UTC ze strefą.
- Nie dopisuj dywidend gotówkowych do akumulującego IUSQ.
- Odróżniaj ceny transakcyjne, rynkowe i prognozy. Zapisuj źródło i moment wyceny.
- Reguły emisji wersjonuj i wiąż z dokumentem źródłowym.
- Importy i zadania pobierania projektuj z ochroną przed duplikatami.

## Bezpieczeństwo

- Sekrety poza Git. W .env.example tylko demonstracyjne wartości; baza lokalna dostępna wyłącznie lokalnie.
- Nie loguj pełnych portfeli, raportów brokera, tokenów ani haseł.
- Pochodzenie właściciela danych ustala backend. Pole user_id z żądania nie jest dowodem uprawnienia.
- Do czasu wdrożenia uwierzytelniania aplikacja działa wyłącznie lokalnie; identyfikator demonstracyjny ustala konfiguracja serwera.
- Testy na danych syntetycznych. Nie wykonuj operacji na rzeczywistych portfelach lub produkcji.
- Nie usuwaj wolumenów bazy w zwykłych instrukcjach restartu i zatrzymania.

## Weryfikacja

- Testuj przypadki finansowe według docs/calculations.md, w tym prowizje, jednostki ułamkowe i wiele zakupów.
- Testy integracyjne bazy uruchamiaj na PostgreSQL, nie na SQLite.
- Testy dostawców w CI z atrapami; sprawdzenie sieciowe raportuj osobno.
- Sprawdzaj typy TypeScript niezależnie od budowania Vite.
- Dla migracji sprawdź przejście od pustej bazy do aktualnej wersji.
- Po wdrożeniu właścicieli danych dodaj testy odmowy dostępu między użytkownikami.
