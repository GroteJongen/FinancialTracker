# Architektura i model danych

## Układ docelowy

- frontend/: React, TypeScript, Vite.
- backend/app/domain/: typy i czyste obliczenia finansowe.
- backend/app/application/: przypadki użycia, transakcje bazodanowe i autoryzacja.
- backend/app/infrastructure/: SQLAlchemy, dostawcy danych i konfiguracja.
- backend/app/api/: FastAPI, walidacja wejścia i odpowiedzi.
- backend/migrations/: Alembic.
- backend/tests/ i frontend/: testy odpowiednich warstw.
- e2e/: testy Playwright.
- docs/: źródło zakresu i decyzji; compose.yaml: środowisko lokalne.

To docelowy podział, nie istniejący jeszcze kod. Twórz katalogi wraz z rzeczywistą implementacją.

## Encje

| Encja | Rola |
|---|---|
| Owner | Właściciel rachunków, początkowo lokalny użytkownik demonstracyjny |
| Account | Rachunek właściciela; rodzaj IKE lub inny, waluta bazowa |
| Instrument | Tożsamość aktywa, typ i opcjonalny ISIN |
| Listing | Instrument, giełda/MIC i waluta notowania |
| ProviderSymbol | Mapowanie notowania na symbol konkretnego dostawcy |
| Operation | Rachunek, instrument/notowanie, data i typ operacji |
| PurchaseDetails | Liczba jednostek, cena, prowizja i waluty; na start EUR |
| PriceObservation | Notowanie, cena, waluta, data/czas notowania, moment pobrania i źródło |
| AuditEvent | Właściciel, identyfikator operacji, rodzaj korekty i czas zmiany |
| BondIssue — później | Seria, warunki, okresy i referencja do dokumentu emisji |
| BondPurchase — później | Rachunek, emisja, dzień zakupu, ilość i faktyczny koszt |
| FxObservation — później | Para walutowa, kurs, data i źródło |

ISIN jest opcjonalny: przyszłe aktywa mogą go nie mieć. Sam ticker nie jest globalnym identyfikatorem. Ilość jest stanem wyliczanym z operacji. Korekty muszą być atomowe i audytowalne; usuwanie lub anulowanie to jawna operacja, nie niezauważalna zmiana historii.

## Rozszerzalność

Każda klasa aktywów otrzymuje własne walidacje i sposób wyceny. Wspólny rezultat zawiera kwotę, walutę, moment wyceny, źródła i informację, czy jest prognozą. Nie narzucaj jednej struktury cenowej obligacjom detalicznym i aktywom giełdowym.

Cena rynkowa, wartość nominalna, odsetki naliczone, wypłacone i kwota wcześniejszego wykupu są oddzielnymi pojęciami. Szczegółowe parametry przechowuj w tabelach właściwych dla klasy aktywów. JSON służy tylko pomocniczym metadanym lub surowym odpowiedziom.

Portfele i operacje są prywatne. Obserwacje publicznych notowań mogą być współdzielone, jeśli warunki źródła na to pozwalają. Dostawca zwraca dane do modelu wewnętrznego; jego odpowiedź nie staje się kontraktem API aplikacji.

## Lokalna izolacja i przyszłe konta

Domyślnie porty związane z aplikacją i bazą wiążemy z 127.0.0.1. Identyfikator właściciela pochodzi z serwera. Każde wyszukiwanie i zmiana operacji sprawdzają właściciela rachunku. Relacje bazodanowe i unikalność wspierają te ograniczenia. Przed dostępem sieciowym potrzebne są rzeczywiste uwierzytelnianie i ponowny przegląd dostępu.

## Integracje później

IUSQ.DE jest kandydatem do pobierania dziennych cen. Dostępność i format wymagają testu integracji. Zapisuj walutę i źródło; nie zastępuj braku notowania ceną innej giełdy bez jawnej decyzji. Odświeżanie ma timeout, ograniczone ponowienia i ochronę przed duplikatami. Brak sieci nie kasuje ostatniej ceny. Licencje komercyjne pozostają osobną decyzją przed ewentualnym udostępnieniem produktu.
