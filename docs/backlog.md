# Backlog

Statusy: Do ustalenia → Gotowe → W trakcie → Do sprawdzenia → Ukończone.
Zadanie zakończone oznacza kod, właściwe sprawdzenia, dokumentację i opis ograniczeń. Agent nie zmienia statusu na ukończone wyłącznie na podstawie wygenerowania kodu.

## FT-001 — Uruchamialny fundament

Status: Ukończone — zweryfikowane w CI. Lokalny start na Windows wymaga Docker Desktop; szczegóły w verification.md. Zależności: brak.

Zakres: lokalne Git (jeżeli brak), frontend React/TypeScript/Vite, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Docker Compose, .env.example, .gitignore i automatyczne kontrole. Początkowy model Owner oraz Account z właścicielem i typem rachunku. Dane demonstracyjne tworzone idempotentnie jawną komendą. Testowa baza oddzielona od użytkowej.

Kryteria:

- Compose buduje i uruchamia aplikację; porty dostępne lokalnie.
- Frontend po polsku potwierdza komunikację z backendem.
- Endpoint gotowości sprawdza połączenie z bazą, zwraca 503 przy jej niedostępności i nie ujawnia sekretów.
- Migracja od pustej bazy działa, dane przetrwają zwykły restart kontenerów.
- Kontrole obejmują pytest, typy TypeScript, lint i build; workflow CI wykonuje je na danych syntetycznych.
- README zawiera rzeczywiście sprawdzone komendy instalacji, migracji, startu, zatrzymania i testów. Niewykonane kontrole są wyraźnie oznaczone.
- Nie ma jeszcze pobierania kursów, płatności ani pozornego formularza logowania.

## FT-002 — Instrument i historia zakupów

Status: Ukończone — 38 testów backendu oraz testy przeglądarkowe i trwałości w CI zaliczone. Zależności: FT-001 zakończone. Szczegóły w verification.md.

Dodaj Instrument, Listing, zakup i ślad korekty. Skonfiguruj IUSQ na Xetra, EUR. Formularz i historia po polsku. Obsłuż walidację, jednostki ułamkowe, wiele zakupów i przypisanie do rachunku. Testy API i PostgreSQL obejmują zapis, korektę i odmowę dostępu do obcego rachunku. Żądanie nie wybiera właściciela. Ponowne uruchomienie nie duplikuje instrumentu ani danych demonstracyjnych.

## FT-003 — Ręczna wycena i wynik

Status: Ukończone — 73 testy backendu, 12 testów przeglądarkowych i trwałość ceny po restarcie potwierdzone w CI. Zależności: FT-002 zakończone. Szczegóły w verification.md.

Wprowadź PriceObservation, czyste funkcje obliczeń i podsumowanie. Wszystkie przykłady calculations.md przechodzą. API przekazuje wartości dziesiętne jako tekst. Brak ceny nie jest zerem. Zapisuj datę i źródło, obsłuż granice dat. Wynik po korekcie zakupu jest przeliczany.

## FT-004 — Odbiór pierwszej wersji

Status: Gotowe. Zależności: FT-003 zakończone.

Playwright: zakup 10 × 100 + 2 EUR, cena 110 EUR, wynik 98 EUR; odświeżenie strony zachowuje dane. Sprawdź niedostępną wycenę, korektę oraz jednostki ułamkowe. Przygotuj i sprawdź procedurę kopii i odtworzenia lokalnej bazy w oddzielnej bazie. Zaktualizuj dokumentację i listę znanych ograniczeń. Pierwsza wersja wymaga FT-001 do FT-004.

## FT-005 — Automatyczne ceny IUSQ

Status: Do ustalenia po FT-004.

Zweryfikuj pobieranie IUSQ.DE i warunki użycia. Adapter, symbol dostawcy, dzienne kursy, identyfikacja zamkniętej sesji, timeout i brak duplikatów. Przycisk odświeżenia, data/źródło i zachowanie ostatniej ceny podczas awarii. Cena ręczna i automatyczna mają jawny priorytet ustalony przed implementacją. Testy bez sieci oraz osobny test rzeczywistej integracji.

## FT-006 — PLN

Status: Do ustalenia.

NBP API, historyczny koszt i aktualna wycena według calculations.md. Ustal zachowanie w dni bez tabeli i oznaczenie szacunków. Nie implementuj rozliczeń podatkowych przy okazji wyceny.

## FT-007 — TOS

Status: Do ustalenia; wymagane seria, list emisyjny, tabele i typ rachunku.

Parametry emisji, zakup, harmonogram kapitalizacji, wycena i testy zgodności z oficjalnymi tabelami. Reguły zaokrągleń i wcześniejszy wykup wymagają weryfikacji źródłowej.

## FT-008 — COI i EDO

Status: Do ustalenia; po FT-007 i z dokumentami konkretnych emisji.

Oddziel wypłaty COI od kapitalizacji EDO. Dodaj znane stopy dla okresów i osobne założenia prognozy. Zweryfikuj daty graniczne i zgodność z tabelami.

## Dalszy backlog

Eksport/import, sprzedaż i rozliczenie partii, dywidendy wypłacane, podziały jednostek, transfery, kolejne klasy aktywów, rzeczywiste logowanie i wdrożenie sieciowe. Każde wymaga własnego opisu i kryteriów. Abonamenty i komercjalizacja nie są bieżącym zakresem.

## FT-009 — Ewidencja zakupów obligacji

Status: Ukończone — 105 testów backendu, 16 testów przeglądarkowych oraz migracje i trwałość Compose potwierdzone w CI. Priorytet nadany przez użytkownika przed FT-004–FT-008.

Zakres: tworzenie rachunków PLN zwykły/IKE/IKZE, zakupy TOS/COI/EDO, niezmienne wersje parametrów emisji, koszt zakupu Decimal, korekty z audytem, izolacja właścicieli, idempotencja, migracja 0004, formularz i testy. Szczegóły w bonds.md. Nie obejmuje silnika odsetek ani zasad podatkowych; FT-007 i FT-008 pozostają osobnymi zadaniami wymagającymi dokumentów źródłowych.

## FT-010 — Dodawanie i podgląd akcji

Status: Ukończone — 127 testów backendu, 21 testów przeglądarkowych oraz migracje i trwałość Compose potwierdzone w CI. Priorytet nadany przez użytkownika.

Pusty, prywatny katalog akcji, ręczna rejestracja spółki/notowania, rachunki zwykłe/IKE/IKZE, zakupy i korekty, ręczna wycena, koszt i wynik w walucie notowania PLN/EUR/USD. Migracja 0005, izolacja właścicieli, idempotencja oraz regresja ETF i obligacji. Automatyczne kursy, FX, dywidendy i sprzedaż pozostają osobnymi zadaniami. Patrz stocks.md.
