# Zakupy obligacji — FT-009

Zakres: ewidencja zakupów detalicznych obligacji TOS, COI i EDO. Użytkownik tworzy rachunek PLN typu zwykły, IKE lub IKZE. Typ jest metadanymi ewidencji: aplikacja nie potwierdza dostępności produktu u pośrednika, nie liczy podatków, limitów wpłat ani korzyści IKE/IKZE.

## Wprowadzanie danych

W sekcji „Instrumenty” kliknij „Dodaj instrument” i wybierz rodzaj aktywa „Obligacje”. Formularz pokaże sekcję „Obligacje skarbowe”, która pozwala utworzyć rachunek, wybrać typ obligacji, wpisać serię, datę zakupu, całkowitą liczbę sztuk oraz rzeczywistą cenę jednej obligacji w PLN. Domyślną cenę 100,00 PLN można zmienić, np. przy zakupie w drodze zamiany. Zapisujemy koszt: sztuki × cena. Nie jest to nominał ani bieżąca wartość obligacji.

Formularz wymaga oprocentowania: stałego dla TOS, pierwszego roku dla COI/EDO. Marża i adres HTTPS dokumentu emisji są opcjonalne. API pozwala zachować starsze wpisy bez stopy; brakujące warunki pobieramy ze strony konkretnej emisji. Puste oprocentowanie nie oznacza 0%. Wpisane ręcznie parametry mają status MANUAL_UNVERIFIED. Podanie adresu nie oznacza weryfikacji dokumentu.

Seria musi mieć format TOS/COI/EDO + miesiąc 01–12 + dwie cyfry roku. Sprawdzamy format, a nie istnienie emisji ani zgodność dnia zakupu z jej okresem sprzedaży. Daty przyszłe są odrzucane względem Europe/Warsaw. Cena jest dodatnia, do 10 cyfr całkowitych i 2 ułamkowych; sztuki 1–999999999; procenty 0–100, do 8 miejsc po kropce. API przyjmuje liczby dziesiętne wyłącznie jako tekst. Frontend normalizuje przecinek.

## Korekty i trwałość

Każdy zapis i korekta tworzą zdarzenie audytu w tej samej transakcji. Korekta wymaga powodu oraz aktualnej rewizji; konflikt zwraca 409. Parametry emisji są niezmiennymi, prywatnymi dla właściciela snapshotami BondIssue. Skrót SHA-256 kanonicznych pól identyfikuje wersję parametrów. Korekta parametrów tworzy lub wybiera inną wersję, nie zmienia zakupów korzystających ze starej wersji. Snapshot nie jest jeszcze kompletnym silnikiem reguł emisji.

POST zakupu posiada request_id unikalne w rachunku. Identyczne ponowienie zwraca istniejący zapis (200), inne dane z tym kluczem — 409. Ponowienie pierwotnego żądania po korekcie zwraca aktualny zakup, nie cofa korekty. Tworzenie rachunku z tą samą nazwą i typem jest idempotentne; ta sama nazwa z innym typem daje 409.

## API

| Metoda | Ścieżka | Wynik |
|---|---|---|
| POST | /api/bond-accounts | Rachunek PLN: name, kind STANDARD/IKE_BONDS/IKZE; właściciel z konfiguracji |
| POST | /api/bonds/refresh | Uzupelnienie brakujacych danych emisji i historycznego CPI, filtry scope i portfolio_id |
| GET | /api/accounts/{id}/bonds | Zakupy danego rachunku, od najnowszych |
| POST | /api/accounts/{id}/bonds | Nowy zakup, 201; ponowienie 200 |
| PUT | /api/accounts/{id}/bonds/{purchase_id} | Korekta z expected_revision i reason |
| GET | /api/accounts/{id}/bonds/{purchase_id}/audit | Historia wartości przed i po korekcie |

Zakupy są dostępne wyłącznie dla właściciela rachunku; obsługiwane rachunki obligacji muszą być w PLN. Nie łączymy kosztu PLN z wynikiem ETF w EUR. Migracja 0004 dodaje trzy tabele bez zmiany wcześniejszych zakupów i cen IUSQ. Seed nie dodaje fikcyjnych obligacji.

## Ograniczenia

Automatyczne naliczanie brutto TOS/COI/EDO opisano ponizej. Nadal brak podatkow, oplat za wczesniejszy wykup, sprzedazy i importu. Nalezny kupon nie potwierdza przelewu.

Źródło ogólnej identyfikacji typów i okresów: https://www.obligacjeskarbowe.pl/oferta/ (sprawdzone 2026-11-27): TOS 3 lata, COI 4 lata, EDO 10 lat. Dokumenty konkretnej serii muszą być podstawą przyszłych obliczeń; dzisiejsze stopy nie są zasadami starszych emisji.

## Uruchomienie aktualizacji

Po pobraniu gałęzi/mergu, w katalogu projektu:

```powershell
docker compose up --build -d --wait --wait-timeout 300
```

Jeśli kontener migrate ma już zakończony wcześniejszy przebieg, Compose odtworzy go po zmianie obrazu backendu. Gotowość API wymaga rewizji 0004. W razie niezgodności sprawdź `docker compose logs migrate backend`, a migrację można jawnie wykonać przez `docker compose run --rm migrate`. Nie usuwaj wolumenu postgres-data.

## Weryfikacja

Testy API obejmują typy rachunków, zapis, korekty, niezmienne snapshoty, walidację, utratę odpowiedzi, konflikt klucza i wersji, równoczesne zapisy, odmowę dostępu i wycofanie transakcji przy błędzie audytu. Testy Playwright obejmują TOS/COI/EDO, trzy typy rachunków, przecinek dziesiętny, korektę, audyt, odświeżenie, ponowienie i szerokość mobilną. `scripts/smoke-bonds.mjs` sprawdza trwałość po restarcie całego Compose na syntetycznych danych CI. Wyniki wykonania opisujemy w verification.md.

## Automatyczne naliczanie FT-021

Wymagane dane formularza to seria/typ, rachunek, data, liczba sztuk, cena zakupu i oprocentowanie: stałe dla TOS, z pierwszego roku dla COI/EDO. Tryb wynika z produktu: TOS/EDO kapitalizują rocznie, COI wypłaca roczne kupony. Nie można przypisać produktu do niezgodnego trybu. Brakującą marżę i stopę pierwszego roku dla starych wpisów pobieramy ze strony danej serii MF; nie z bieżącej oferty innej emisji. Inflacja pochodzi z tabeli GUS „analogiczny miesiąc poprzedniego roku = 100”, pomniejszonej o 100 punktów. Dla okresu rozpoczynającego się w listopadzie używamy wrześniowego CPI, ogłoszonego w październiku. Ujemną inflację ograniczamy do zera przed dodaniem marży.

Nominał to 100 PLN na sztukę, niezależnie od ceny nabycia (np. 99,90). Stosujemy ACT/ACT dla niepełnego rocznego okresu, z uwzględnieniem lat przestępnych. Wartości zaokrąglamy na sztukę do grosza. TOS używa zaokrąglonego kapitału z poprzedniego okresu przy naliczaniu części roku; EDO iloczynu kolejnych stóp, zgodnie z załącznikami listów. COI liczy kupony od nominału; zakończone kupony zwiększają wynik, bez ponownego dodawania do wartości obligacji. Kapitalizacja zwiększa wartość, bez drugiego doliczania jako wypłata. Naliczanie kończy się w terminie wykupu; samo nadejście tej daty nie potwierdza umorzenia ani transferu pieniędzy.

Wynik jest brutto, bez podatku i opłat za wcześniejszy wykup. Należny kupon nie potwierdza przelewu na rachunek. Ręcznie zapisana wycena dla aktualnej rewizji zakupu ma pierwszeństwo. Brak stopy, marży lub właściwego CPI pozostaje brakiem pełnej wyceny — nie zastępujemy danych stopą pierwszego roku ani zerem. Nominał może być pokazany osobno i nie udaje pełnej wartości aktywa.

GET portfolio liczy tylko z lokalnych danych. POST /api/bonds/refresh pobiera do czterech brakujących serii równolegle i jedną tabelę GUS, poza transakcją bazy. Do dostawców nie wysyłamy rachunków, ilości ani wartości zakupów. Cache jest uzupełniany bez nadpisywania historycznych odczytów. Błędy nie usuwają znanych danych. Frontend pobiera brakujące dane automatycznie po otwarciu i dodaniu obligacji; ponowienie jest dostępne przyciskiem.

Źródła zweryfikowane 2026-11-28:
- https://www.obligacjeskarbowe.pl/media_files/0f23ffd0-a3d6-467d-b3cc-c3ffcc190ecd.pdf (TOS0829, załączniki 1 i 2)
- https://www.obligacjeskarbowe.pl/media_files/21db12fd-35ec-4cbd-b3f4-28a9a7ae2c7e.pdf (COI0930, załączniki 1–3)
- https://www.obligacjeskarbowe.pl/media_files/25f35d9b-0ea3-4cb9-b3c2-cd9200473a57.pdf (EDO1136, załączniki 1–3)
- https://stat.gov.pl/obszary-tematyczne/ceny-handel/wskazniki-cen/wskazniki-cen-towarow-i-uslug-konsumpcyjnych-pot-inflacja-/miesieczne-wskazniki-cen-towarow-i-uslug-konsumpcyjnych-od-1982-roku/
