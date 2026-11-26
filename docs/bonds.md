# Zakupy obligacji — FT-009

Zakres: ewidencja zakupów detalicznych obligacji TOS, COI i EDO. Użytkownik tworzy rachunek PLN typu zwykły, IKE lub IKZE. Typ jest metadanymi ewidencji: aplikacja nie potwierdza dostępności produktu u pośrednika, nie liczy podatków, limitów wpłat ani korzyści IKE/IKZE.

## Wprowadzanie danych

Sekcja „Obligacje skarbowe” pozwala utworzyć rachunek, wybrać typ obligacji, wpisać serię, datę zakupu, całkowitą liczbę sztuk oraz rzeczywistą cenę jednej obligacji w PLN. Domyślną cenę 100,00 PLN można zmienić, np. przy zakupie w drodze zamiany. Zapisujemy koszt: sztuki × cena. Nie jest to nominał ani bieżąca wartość obligacji.

Opcjonalnie użytkownik wpisuje oprocentowanie (stałe dla TOS, pierwszego roku dla COI/EDO), marżę dla COI/EDO i adres HTTPS dokumentu emisji. Stopy nie są uzupełniane aktualną ofertą. Puste oprocentowanie jest brakiem danych, nie stopą 0%. Parametry zawsze mają status MANUAL_UNVERIFIED. Podanie adresu nie oznacza, że aplikacja pobrała lub zweryfikowała dokument.

Seria musi mieć format TOS/COI/EDO + miesiąc 01–12 + dwie cyfry roku. Sprawdzamy format, a nie istnienie emisji ani zgodność dnia zakupu z jej okresem sprzedaży. Daty przyszłe są odrzucane względem Europe/Warsaw. Cena jest dodatnia, do 10 cyfr całkowitych i 2 ułamkowych; sztuki 1–999999999; procenty 0–100, do 8 miejsc po kropce. API przyjmuje liczby dziesiętne wyłącznie jako tekst. Frontend normalizuje przecinek.

## Korekty i trwałość

Każdy zapis i korekta tworzą zdarzenie audytu w tej samej transakcji. Korekta wymaga powodu oraz aktualnej rewizji; konflikt zwraca 409. Parametry emisji są niezmiennymi, prywatnymi dla właściciela snapshotami BondIssue. Skrót SHA-256 kanonicznych pól identyfikuje wersję parametrów. Korekta parametrów tworzy lub wybiera inną wersję, nie zmienia zakupów korzystających ze starej wersji. Snapshot nie jest jeszcze kompletnym silnikiem reguł emisji.

POST zakupu posiada request_id unikalne w rachunku. Identyczne ponowienie zwraca istniejący zapis (200), inne dane z tym kluczem — 409. Ponowienie pierwotnego żądania po korekcie zwraca aktualny zakup, nie cofa korekty. Tworzenie rachunku z tą samą nazwą i typem jest idempotentne; ta sama nazwa z innym typem daje 409.

## API

| Metoda | Ścieżka | Wynik |
|---|---|---|
| POST | /api/bond-accounts | Rachunek PLN: name, kind STANDARD/IKE_BONDS/IKZE; właściciel z konfiguracji |
| GET | /api/accounts/{id}/bonds | Zakupy danego rachunku, od najnowszych |
| POST | /api/accounts/{id}/bonds | Nowy zakup, 201; ponowienie 200 |
| PUT | /api/accounts/{id}/bonds/{purchase_id} | Korekta z expected_revision i reason |
| GET | /api/accounts/{id}/bonds/{purchase_id}/audit | Historia wartości przed i po korekcie |

Zakupy są dostępne wyłącznie dla właściciela rachunku; obsługiwane rachunki obligacji muszą być w PLN. Nie łączymy kosztu PLN z wynikiem ETF w EUR. Migracja 0004 dodaje trzy tabele bez zmiany wcześniejszych zakupów i cen IUSQ. Seed nie dodaje fikcyjnych obligacji.

## Ograniczenia i dalszy etap

Brak naliczania odsetek, prognoz, wypłat kuponów, daty wykupu, opłat za wcześniejszy wykup, sprzedaży, importu i automatycznej weryfikacji emisji. Nie wyliczamy wyniku inwestycji z kosztu zakupu. FT-007/FT-008 nadal wymagają dokumentów konkretnych emisji, tabel odsetkowych i testów dat granicznych.

Źródło ogólnej identyfikacji typów i okresów: https://www.obligacjeskarbowe.pl/oferta/ (sprawdzone 2026-11-27): TOS 3 lata, COI 4 lata, EDO 10 lat. Dokumenty konkretnej serii muszą być podstawą przyszłych obliczeń; dzisiejsze stopy nie są zasadami starszych emisji.

## Uruchomienie aktualizacji

Po pobraniu gałęzi/mergu, w katalogu projektu:

```powershell
docker compose up --build -d --wait --wait-timeout 300
```

Jeśli kontener migrate ma już zakończony wcześniejszy przebieg, Compose odtworzy go po zmianie obrazu backendu. Gotowość API wymaga rewizji 0004. W razie niezgodności sprawdź `docker compose logs migrate backend`, a migrację można jawnie wykonać przez `docker compose run --rm migrate`. Nie usuwaj wolumenu postgres-data.

## Weryfikacja

Testy API obejmują typy rachunków, zapis, korekty, niezmienne snapshoty, walidację, utratę odpowiedzi, konflikt klucza i wersji, równoczesne zapisy, odmowę dostępu i wycofanie transakcji przy błędzie audytu. Testy Playwright obejmują TOS/COI/EDO, trzy typy rachunków, przecinek dziesiętny, korektę, audyt, odświeżenie, ponowienie i szerokość mobilną. `scripts/smoke-bonds.mjs` sprawdza trwałość po restarcie całego Compose na syntetycznych danych CI. Wyniki wykonania opisujemy w verification.md.
