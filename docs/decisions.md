# Decyzje projektowe

Stan: uzgodniony kierunek z rozmowy; szczegóły implementacji potwierdzamy podczas FT-001.

| ID | Decyzja | Powód i konsekwencja |
|---|---|---|
| ADR-001 | PostgreSQL od początku | Jeden silnik lokalnie i w przyszłym wdrożeniu; większy koszt startu niż SQLite, mniej różnic później |
| ADR-002 | React/TypeScript/Vite i FastAPI/Python | Interaktywny interfejs i osobny moduł obliczeń oraz integracji; dwa środowiska uruchomieniowe |
| ADR-003 | Jeden backend z modułami | Prosty rozwój i wdrożenie; granice wewnątrz kodu umożliwiają późniejszą rozbudowę |
| ADR-004 | Decimal i NUMERIC, wartości dziesiętne w JSON jako tekst | Dokładność i jawne zaokrąglenia; frontend odpowiada za prezentację |
| ADR-005 | Oddzielnie instrument, notowanie, rachunek, operacja i wycena | Obsługa wielu giełd, rachunków i różnych sposobów wyceny |
| ADR-006 | Najpierw ręczna cena i zakupy IUSQ | Sprawdzenie kompletnego przepływu bez zależności od dostępności dostawcy |
| ADR-007 | Właściciel danych od pierwszej migracji | Przygotowanie kontroli dostępu; nie zastępuje rzeczywistego uwierzytelniania |
| ADR-008 | Wersjonowanie reguł obligacji według emisji | Unikanie stosowania aktualnych warunków do dawnych zakupów |
| ADR-009 | Prywatny tryb lokalny w pierwszym wydaniu | Brak publicznego wdrożenia i płatności; porty tylko lokalne |
| ADR-010 | Python 3.13, Node 24 i PostgreSQL 17 w kontenerach | Zgodność środowiska CI i Compose bez zależności od starego lokalnego Node |
| ADR-011 | Interfejs korzysta z proxy /api | Jeden origin, brak CORS i kluczy w przeglądarce |
| ADR-012 | Demonstracja jawną komendą | Pierwszy start nie udaje prawdziwego portfela |
| ADR-013 | Lockfile wygenerowane przez CI na gałęzi FT-001 | Bootstrap został usunięty; standardowe CI ma wyłącznie odczyt repozytorium |
| ADR-014 | Zakupy: NUMERIC(18,8), JSON jako tekst | Do 10 cyfr całkowitych i 8 ułamkowych; walidacja odrzuca nadmiar zamiast zaokrąglać |
| ADR-015 | Operation i PurchaseDetails rozdzielone | Wspólna tożsamość operacji, osobne dane zakupu; instrument oddzielony od notowania |
| ADR-016 | Powód korekty, rewizja i audyt w jednej transakcji | Zachowujemy wartości przed i po; konflikt wersji zwraca 409, nie nadpisuje cudzego zapisu |
| ADR-017 | Klucz ponowienia unikalny dla rachunku | Ponowienie identycznego zakupu nie tworzy duplikatu; inna treść z tym kluczem zwraca 409 |
| ADR-018 | Dzień transakcji względem Europe/Warsaw | Backend odrzuca przyszłe daty; kontener instaluje systemowe dane stref czasowych |
| ADR-019 | Cena ręczna prywatna dla rachunku i notowania | Zapis ceny nie zmienia wycen na innych rachunkach; historia jest dopisywana |
| ADR-020 | Cena co najmniej z dnia ostatniego zakupu | Późniejszy zakup lub korekta daty unieważnia użycie wcześniejszej ceny; koszt i ilość nadal są widoczne |
| ADR-021 | Obliczenia Decimal, prezentacja HALF_UP do 2 miejsc | Nie zaokrąglamy średniego kosztu przed obliczeniem wyniku; kwoty w API są tekstem |
| ADR-022 | Frontend i backend pozostają w jednym repozytorium | Oddzielne moduły, obrazy i zadania CI; wspólne zmiany kontraktu są atomowe. Podział repo rozważymy przy niezależnych cyklach wydań lub zespołach |
| ADR-027 | GHCR po zielonym main, reczne pobranie wspolnego wydania SHA | Osobny Compose bez build; pakiety domyslnie prywatne, packages:write tylko dla publikatora, zachowany wolumen i lokalne porty. Brak harmonogramu; zasady migracji i pierwszego pobrania w ghcr.md |

## Źródła identyfikacji i integracji

- BlackRock, instrument i notowania: https://www.blackrock.com/de/privatanleger/produkt/251850/ishares-msci-acwi-ucits-etf
- Yahoo, symbol do testu: https://finance.yahoo.com/quote/IUSQ.DE/
- yfinance, charakter integracji i warunki: https://github.com/ranaroussi/yfinance
- NBP API: https://api.nbp.pl/
- Obligacje, oferta: https://www.obligacjeskarbowe.pl/oferta/
- Dokumenty emisji i tabele należy wybrać dla wskazanych przez użytkownika serii; nie przyjmujemy stawek z bieżącej oferty jako parametrów wszystkich zakupów.

Źródła służą weryfikacji implementacji; projekt nie gwarantuje stałej dostępności ani prawa do komercyjnej redystrybucji danych. Przed doborem wersji bibliotek agent sprawdza ich oficjalną dokumentację i kompatybilność.

## Otwarta lista decyzji

Broker, serie i rachunek obligacji; dopuszczalna precyzja wejścia; nazwa i waluta prezentacji rachunku; przyszła metoda rozliczenia sprzedaży; priorytet ceny ręcznej; dostawca logowania i sposób hostingu. Nie wdrażaj domyślnych zasad podatkowych na podstawie samej etykiety IKE.

## ADR-023 — Zakupy obligacji przed wyceną

Na prośbę użytkownika FT-009 wdraża samą ewidencję COI/TOS/EDO przed FT-007/FT-008. BondPurchase jest osobną encją bez fikcyjnego giełdowego Listing. BondIssue przechowuje prywatny, niezmienny snapshot parametrów ręcznych i referencję do dokumentu; wersja jest skrótem kanonicznych pól. Nie jest zweryfikowanym modelem reguł. Brak stopy to null, nie 0%. Cena zakupu PLN ma NUMERIC(12,2), stopy NUMERIC(11,8), sztuki są całkowite. Typ rachunku zwykły/IKE/IKZE jest metadanymi i nie wdraża zasad podatkowych ani nie potwierdza dostępności produktu u brokera.

## ADR-024 — Prywatny katalog akcji i wspólny rejestr papierów

Akcje używają istniejących Instrument/Listing, Operation/PurchaseDetails, AuditEvent i PriceObservation. Instrument.owner_id izoluje prywatne dane katalogu; publiczny IUSQ ma owner_id null. ISIN jest unikalny w katalogu właściciela, a publiczny katalog zachowuje własną unikalność. Identyczne rejestracje są rozpoznawane po tickerze/MIC/walucie pod blokadą właściciela, bez automatycznego pobierania danych. Zakupy i wyceny są w walucie notowania; rachunek bazowy nie uruchamia przeliczenia FX. Korekta nie zmienia notowania zakupu.

## ADR-025 — Wspólny dashboard w PLN

Koszt walutowy przeliczamy historycznie jako jawny szacunek NBP, a wartość aktualnym dostępnym kursem referencyjnym. Wypłacone odsetki są skumulowanym dochodem, nie kolejnym aktywem ani kolejnymi wpłatami. Brak pełnej wyceny daje null i blokuje pełny wykres wartości. Ręczna wycena partii obligacji nie udaje automatycznego silnika reguł emisji. Konto IKE_BONDS należy do filtra IKE. Blokadę właściciela zmieniono na FOR NO KEY UPDATE, aby umożliwić równoczesne kontrole klucza obcego podczas zapisu zakupów/audytu; test wymusza tę kolejność współbieżną.

## ADR-026 - Yahoo jako wymienny adapter i trwaly cache

Nieoficjalny endpoint chart, bez nowej zaleznosci, sluzy prywatnej aplikacji. Surowy JSON jest parsowany do Decimal, bez float. Tylko zweryfikowane symbol/gielda/waluta/typ trafiaja do oddzielnego cache YahooListing. Reczne ceny pozostaja niezmienne i prywatne dla rachunku; nowszy dzien/czas wyceny wygrywa, a uzytkownik moze wylaczyc Yahoo. Rezerwacja proby trwa 5 minut i jest zatwierdzana przed HTTP; token chroni przed zapisem po zmianie mapowania. Brak automatycznego zgadywania symboli akcji. Dokumentacja: yahoo.md.

## ADR-028 - Portfel jako prywatna grupa rachunkow

PortfolioGroup i PortfolioAccount tworza relacje wiele-do-wielu; portfel prezentacyjny nie przenosi zakupow ani historii. Suma wszystkich rachunkow nie laczy wynikow grup, wiec ich przeciecia nie duplikuja kapitalu. Rachunki/tax wrapper i instrumenty/notowania pozostaja oddzielne. Prywatny katalog dopuszcza ETF/akcje/gieldowe REIT, a obligacje zachowuja odrebna wycene. Pozycje sa rozdzielone rachunkiem, by nie mieszac prywatnych cen. Bez zgadywania regul dla przyszlych klas aktywow.

## ADR-029 - Rejestracja instrumentu na rachunku

Przypisanie notowania do rachunku jest osobną relacją account_listings, bez tworzenia zerowych lub fikcyjnych zakupów. Walidacja rachunku i zapis instrumentu oraz przypisania odbywają się w jednej transakcji, pod istniejącą blokadą właściciela. Katalog odczytuje także rachunki z rzeczywistych operacji; nie przenosimy historii ani nie zmieniamy wycen. Właściciela ustala serwer. Usunięcie rachunku/notowania usuwa jedynie metadata przypisania przez FK CASCADE; operacje finansowe nadal mają dotychczasowe ograniczenia.
