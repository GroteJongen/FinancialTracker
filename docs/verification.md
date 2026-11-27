# Weryfikacja FT-001

## FT-012 - GHCR i reczne aktualizacje, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46015621011 zaliczony dla kodu konfiguracji: 161 testow backendu, 26 Playwright, ruff/format, TypeScript/ESLint/build, Alembic oraz pelny Compose. Wspolny scripts/build-images.sh zbudowal obrazy z etykietami commita; compose.ghcr.yaml uruchomil je bez build i bez pobierania z rejestru, na istniejacym syntetycznym wolumenie. Odczyty zakupow, cen, audytu, obligacji, akcji i sumy portfela po przelaczeniu zaliczone.

Kontrola scripts/check-ghcr.mjs potwierdza brak build, wspolna wersje backend/migrate, wymagany APP_VERSION, zachowanie nazwy wolumenu oraz brak publicznego portu bazy i lokalne porty aplikacji. Skrypt update.ps1 zaliczyl izolowane scenariusze: odrzucenie CI bez publikatora, wybor ostatniego kompletnego wydania, PullOnly bez startu, jawne SHA bez API, kolejnosc migracji/startu, bledy pobierania/migracji/gotowosci backendu, niezgodna rewizja obrazu, zachowanie pliku wybranego wydania i przywrocenie zmiennych sesji. Testy PowerShell lokalnie na Windows PowerShell 5.1 i pwsh 7 oraz w CI pwsh; bez rzeczywistego Dockera/rejestru/bazy. Lokalne git diff --check i kontrola Compose zaliczone.

Job publish-images jest celowo skipped na galezi PR. Logowanie/push do GHCR i pobranie rzeczywistych opublikowanych obrazow nie byly jeszcze wykonane: pierwsza publikacja nastapi po scaleniu na main, przy uzyciu GITHUB_TOKEN z packages:write. Nie scalano PR, nie zmieniano widocznosci pakietow, nie uruchamiano aktualizatora na bazie uzytkownika ani nie konfigurowano harmonogramu. Konfiguracja GHCR jest osobnym PR od oczekujacej integracji Yahoo.


Windows: Git, Node 16.1.0 i npm 7.11.2. Brak Dockera i zainstalowanego Pythona. DNS GitHub i npm niedostępny z lokalnego procesu; zapis kodu przez autoryzowaną integrację GitHub.

Lokalnie: node --check scripts/smoke.mjs i git diff --check poprawne. To nie zastępuje testów aplikacji.

## Wyniki GitHub Actions — 25 listopada 2026

[Przebieg CI](https://github.com/GroteJongen/FinancialTracker/actions/runs/45701187352), kod aplikacji w commicie deb666fcaf14f6db9aa6d27ff39af3d469d5e8e2.

| Kontrola | Wynik |
|---|---|
| Instalacja z lockfile Pythona z weryfikacją hashy | Poprawna |
| Ruff lint i format | Poprawne |
| PostgreSQL: migracja, gotowość, awaria, idempotencja i izolacja właściciela | 4 testy zaliczone |
| Alembic: zgodność bazy z modelami | Brak nowych operacji migracji |
| npm ci, typy TypeScript, ESLint i build | Poprawne |
| Budowanie obrazów i start całego Compose | Poprawne |
| Dwukrotne tworzenie demonstracji | Jeden rachunek |
| Restart db/backend/frontend | Rachunek zachowany |
| Wyłączenie bazy | Odpowiedź gotowości 503 bez szczegółów połączenia |
| Powrót bazy | Gotowość i odczyt rachunku wróciły |
| Playwright: rzeczywiste API, widok mobilny, pusty stan, ponowienie po błędzie | 4 testy zaliczone |

CI działało na Linux; obrazy dostarczają Python 3.13, Node 24 i PostgreSQL 17. Lockfile są zapisane w repozytorium. Tymczasowy job generowania lockfile i jego uprawnienia zapisu usunięto przed powyższym przebiegiem.

## Ograniczenia

Nie wykonano uruchomienia na komputerze użytkownika z powodu braku Docker Desktop. Profil Compose test/test-db jest przygotowany; testy backendu w CI wykonano na osobnym PostgreSQL runnera, nie przez ten profil. Nie potwierdzamy wariantu Windows ani tego profilu jako uruchomionych.

Pozostały nieblokujące ostrzeżenia narzędzi: starszy sposób konfiguracji separatora ścieżek Alembic, deprecjacja httpx w TestClient Starlette oraz wersje akcji GitHub korzystające z automatycznej migracji runtime Node. Nie wpływały na wynik testów; ich aktualizacja jest oddzielnym zadaniem utrzymaniowym.

FT-001 nie zawierał jeszcze dodawania inwestycji. Program pozostaje lokalny, bez uwierzytelniania internetowego i publicznego wdrożenia.

## FT-002 — zakupy IUSQ

[Przebieg weryfikacji](https://github.com/GroteJongen/FinancialTracker/actions/runs/45704671684) zakończył się powodzeniem we wszystkich trzech jobach: backend, frontend i Compose.

- 38 testów backendu na PostgreSQL: liczby ułamkowe i granice precyzji, odrzucanie błędnych danych oraz przyszłych dat, wiele zakupów, korekta i historia wartości, odczyt po ponownym uruchomieniu aplikacji, izolacja właściciela, klucz ponowienia, równoczesne korekty i zapisy, wycofanie transakcji przy błędzie audytu.
- Migracja od pustej bazy i zgodność modeli z bazą. Osobny schemat testowy sprawdza przejście 0001 → 0002, zachowanie istniejących rachunków, cofnięcie i ponowne zastosowanie migracji. Transakcja schematu testowego jest wycofywana po teście.
- Lint i format Python, typy TypeScript, ESLint i build frontendu.
- Pełny start kontenerów, utworzenie zakupu i korekty z audytem, ponowienie zapisu bez duplikatu i odczyt tych samych danych po restarcie db/backend/frontend.
- Playwright: formularz z przecinkiem, 8 miejsc dziesiętnych, korekta z powodem i historią zmian, odświeżenie strony, kolejne zakupy, odrzucenie nadmiaru precyzji i braku powodu, utrata odpowiedzi po udanym POST oraz ponowienie bez duplikatu, widok mobilny. Zachowano również sprawdzenia z FT-001.

W CI użyto tymczasowego kroku formatowania i odczytano dokładne zmiany źródeł. Poprawki zapisano w repozytorium; tymczasowy krok usunięto. Standardowe CI tylko sprawdza kod i ma wyłącznie odczyt repozytorium. Po jego usunięciu wykonywany jest również końcowy przebieg.

Ograniczenia lokalnego środowiska i profilu testowego Compose pozostają takie jak w FT-001. FT-002 nie wdrażał jeszcze wyceny. Cena zapisana przy zakupie pozostaje ceną transakcyjną, oddzielną od ceny wyceny.

## FT-003 — ręczna wycena i wynik

[Pierwszy pełny przebieg](https://github.com/GroteJongen/FinancialTracker/actions/runs/45707784227): backend, frontend i Compose zakończone powodzeniem.

- 73 testy backendu: przykłady z calculations.md, prowizje, wiele zakupów, ułamki, utrata i zaokrąglenie małych wartości, HALF_UP, ujemne zero, duże sumy i niezależność od globalnej precyzji Decimal.
- Integracja PostgreSQL: wycena bez ceny, ręczna cena, ponowienie bez duplikatu, historia i porządek cen, prywatność między właścicielami i rachunkami, stare/przyszłe daty, aktualizacja po zakupie oraz korekcie, unieważnienie starej ceny i odtworzenie po podaniu nowszej.
- Migracja 0002 → 0003 zachowuje istniejący zakup; cofnięcie 0003 zachowuje zakup i rachunek. Alembic nie wykrywa różnic między modelami i bazą.
- 12 testów Playwright: poprzednie funkcje oraz przykład 98 EUR / 9,78%, odświeżenie strony, korekta i przeliczenie wyniku, za stara data, późniejszy zakup, przywrócenie wyceny, utrata odpowiedzi ceny i ponowienie bez duplikatu oraz mobilna szerokość strony.
- Typy TypeScript, ESLint, build, Ruff i format przechodzą. Lockfile pozostały bez zmian.

Zmiany formatowania z CI zapisano w źródłach; tymczasowy krok formatowania usunięto. [Końcowy przebieg CI](https://github.com/GroteJongen/FinancialTracker/actions/runs/45708396119) przeszedł we wszystkich trzech jobach, bez zmieniania kodu przez CI. Potwierdzono 73 testy backendu, 12 testów przeglądarkowych, lint/typy/build, zgodność migracji oraz pełny Compose.

Skrypt smoke-valuation.mjs potwierdził przed i po restarcie db/backend/frontend: prywatną cenę ręczną, brak duplikatu po ponowieniu, historię ceny i identyczny wynik. Dla syntetycznej pozycji 0,25 jednostki po 100,12345678 EUR oraz 0,10 EUR prowizji, cena 110 EUR daje koszt 25,13 EUR, wartość 27,50 EUR i wynik 2,37 EUR po zaokrągleniu. Przeszły również kontrola awarii bazy i odzyskanie gotowości.

Testy przeglądarkowe mają oddzielne syntetyczne rachunki TEST utworzone jawną komendą tests.seed_browser, bez dodawania danych przy zwykłym starcie aplikacji. Baza testów pytest pozostaje oddzielona od bazy aplikacji. Lokalnego startu na Windows nadal nie wykonano z powodu braku Dockera; działanie sprawdzane jest na runnerze Linux.

## FT-009 — Zakupy obligacji, 2026-11-27

Zaliczony pełny [przebieg CI](https://github.com/GroteJongen/FinancialTracker/actions/runs/45912108634). Backend: 105 testów na PostgreSQL 17, ruff check, ruff format --check, alembic check; migracje od pustej bazy oraz od wcześniejszych rewizji zachowują zakupy ETF. Frontend: TypeScript, ESLint i build Vite. Przeglądarka: 16 testów Playwright, w tym 4 nowe scenariusze obligacji i 12 dotychczasowych.

Nowe scenariusze obejmują TOS/COI/EDO na rachunkach zwykły/IKE/IKZE, koszt PLN z ceną zamiany, korektę z powodem, audyt, odświeżenie, niepoprawną liczbę sztuk, ponowienie po utracie odpowiedzi i szerokość mobilną. Testy API sprawdzają też izolację właścicieli i rachunków, konflikt klucza i rewizji, równoczesne zapisy, niezmienne współdzielone wersje emisji oraz atomowe wycofanie przy błędzie audytu.

Compose: start z migracją 0004, syntetyczny zakup obligacji i audyt, ich trwałość po restarcie db/backend/frontend oraz kontrolowana niedostępność i powrót bazy. Wszystkie sprawdzenia wykonano na danych syntetycznych w CI. Lokalnie sprawdzono konfigurację Compose z .env.example i git diff --check; środowisko agenta nie ma dostępu do lokalnego silnika Docker (odmowa dostępu do named pipe), więc nie wykonano testów na lokalnej bazie użytkownika.

Zakres nie obejmuje odsetek, podatków, wykupu, importu i potwierdzania istnienia emisji. Parametry są ręczne i niezweryfikowane. FT-007/FT-008 nadal wymagają listów emisyjnych i tabel konkretnych serii. Użytkownik potwierdził zwykły rachunek jako podstawowy oraz potrzebę typów IKE/IKZE; typ nie zastępuje zasad podatkowych.

## FT-010 — Dodawanie i podgląd akcji, 2026-11-27

Pełny [przebieg CI](https://github.com/GroteJongen/FinancialTracker/actions/runs/46001066830) zakończony powodzeniem. Backend: 127 testów PostgreSQL, ruff check, ruff format --check i alembic check. Obejmuje migracje od pustej i wcześniejszych wersji, zachowanie rachunków i zakupów, prywatność katalogu, różne giełdy i waluty, identyczne ponowienia, konflikty, równoczesną rejestrację, wyceny PLN/EUR/USD oraz odmowę zmiany notowania podczas korekty. Dotychczasowy kontrakt walidacji błędów pozostał zgodny.

Frontend: TypeScript, ESLint i build Vite zaliczone. Playwright: 21 testów, w tym 5 nowych scenariuszy akcji i 16 dotychczasowych. Nowe scenariusze sprawdzają dodanie spółki i rachunku zwykłego/IKE/IKZE, pozycję i wynik w trzech walutach, korektę z audytem, odświeżenie, utratę odpowiedzi katalogu i zakupu, brak duplikatów po ponowieniu i odświeżeniu, pusty katalog oraz szerokość mobilną.

Compose: start z migracją 0005, zapis syntetycznego katalogu, zakupu, ceny i audytu, wynik 98 PLN i 9,78%, trwałość po restarcie db/backend/frontend oraz niedostępność i powrót bazy. Wszystko na izolowanych danych syntetycznych CI. Lokalnie sprawdzono git diff --check i docker compose --env-file .env.example config --quiet. Nie wykonywano operacji na lokalnym portfelu ani dodawania rzeczywistych spółek.

Katalog użytkownika startuje pusty; dane i ceny są ręczne. Brak automatycznych notowań, FX, dywidend, sprzedaży, splitów i podatków. ISIN/MIC/ticker mają walidację formatu, bez weryfikacji notowania u dostawcy. Ograniczenia i aktualizacja opisane w stocks.md.

## FT-011 — Dashboard portfela, 2026-11-27

Pełny [przebieg CI](https://github.com/GroteJongen/FinancialTracker/actions/runs/46006000473) zakończony powodzeniem: 161 testów backendu na PostgreSQL, ruff check, ruff format --check, alembic check, TypeScript, ESLint i build Vite. Migracja 0006 od pustej i wcześniejszych wersji oraz zgodność modeli z bazą zaliczone.

Testy finansowe obejmują przykład kosztu 175000 PLN, wartości 185000 PLN i wyniku 10000 PLN, wypłacone odsetki bez podwójnego liczenia, sumowanie przed zaokrągleniem, niepełne dane, ujemne i zerowe wyniki oraz udziały sumujące się do 100%. Testy API obejmują filtry zwykłe/IKE/IKZE/razem, IKE_BONDS w IKE, prywatność portfela i wycen, rewizje, niezmienne obserwacje, idempotencję, historyczny koszt FX względem bieżącego kursu, zachowanie cache po awarii i brak HTTP przy pustym portfelu. Test współbieżny wymusza jednoczesny odczyt dashboardu i zapis zakupu/audytu, bez zakleszczenia kluczy obcych.

Playwright: 26 testów, w tym 5 nowych scenariuszy dashboardu. Sprawdzono filtry, kwoty przykładu, faktyczne renderowanie gradientu diagramu przy aktualnej CSP, szerokość mobilną, brak fikcyjnej wyceny przy brakach, wykres kosztu, rzeczywistą aktualizację wiersza portfela po zmianie ceny akcji bez przeładowania, zapis i trwałość wypłaconych odsetek obligacji oraz komunikat awarii NBP.

Compose potwierdził trwałość dashboardu, ręcznej wyceny obligacji, odsetek i proporcji po restarcie db/backend/frontend, wraz z dotychczasowymi scenariuszami ETF, akcji i obligacji oraz kontrolowaną niedostępnością i powrotem bazy. Adapter NBP ma testy z atrapami; osobny krok rzeczywistej sieci zakończył się PASS dla EUR, publikacja 2025-01-03, tabela 002/A/NBP/2025. Nie korzysta z danych portfela i nie blokuje pozostałych testów w razie awarii dostawcy.

Lokalnie zaliczono git diff --check oraz docker compose --env-file .env.example config --quiet. Nie wykonywano zapisów do lokalnego portfela użytkownika. Testy używają wyłącznie danych syntetycznych; partia TOS1129 ma ręcznie podaną wycenę i nie stanowi testu silnika naliczania odsetek z listu emisyjnego. Ograniczenia: ręczne ceny aktywów i wyceny obligacji, szacunkowy historyczny FX NBP, brak gotówki, sprzedaży, dywidend i podatków. Szczegóły w portfolio.md.

## FT-005 - Yahoo Finance, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46009835322 zaliczony: 196 testow backendu (35 nowych), 29 testow Playwright (3 nowe), ruff, TypeScript/ESLint/build, Alembic, pelny Compose z migracja 0007, restartem, trwaloscia syntetycznej ceny/mapowania i historia reczna oraz awaria/powrotem bazy. Powstal tez dodatkowy odczyt rzeczywistego Yahoo: PASS IUSQ.DE / XETR / EUR, czas notowania 2026-11-27T13:31:15+00:00. Rzeczywisty odczyt NBP rowniez zaliczony. Nie jest to gwarancja dostepnosci Yahoo z kazdego IP.

Testy sprawdzaja metadane, Decimal, bledne/niepelne ceny, zakres czasu, 429, zakaz przekierowan, cooldown takze po awarii, zachowanie cache, brak podwojnego pobierania przy rownoczesnych odswiezeniach, brak transakcji podczas HTTP, prywatnosc akcji, zmiane/wylaczenie mapowania w trakcie zapytania, cofniecie czasu repliki, date ostatniego zakupu i pierwszenstwo nowszej ceny recznej. Przegladarka pokazuje odswiezenie, oba czasy, awarie i konfiguracje.

Lokalnie git diff --check i docker compose --env-file .env.example config --quiet zaliczone. Agent nie ma dostepu do lokalnego silnika Docker; nie uruchamial testow na bazie uzytkownika i nie dopisal rzeczywistych ani demonstracyjnych aktywow. Pytest zglasza istniejace ostrzezenie przestarzalego httpx TestClient, bez bledu testow.

## FT-013 - Kurs jednostki IUSQ, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46023471827: 196 testow backendu, 29 Playwright, ruff/format, TypeScript/ESLint/build, migracje Alembic, start/restart Compose i przejscie na gotowe obrazy zaliczone. Rozszerzono istniejace scenariusze: 10 jednostek po kursie 110 EUR nadal daje wartosc pozycji 1100 EUR, kurs ma osobny kafelek, brak wyceny daje kreske, a dashboard pokazuje jednostkowa cene Yahoo oddzielnie od wartosci pakietu. Pole API unit_price jest tekstem Decimal z wybranej ceny, bez nowych obliczen lub zaokraglen. Bez zmian schematu, zasad pobierania i priorytetu cen. Lokalnie git diff --check zaliczone. Testy nie byly uruchamiane na bazie uzytkownika; publikator GHCR jest pominiety na galezi i uruchomi sie po merge na main.

## FT-014 - Portfele mieszane, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46065625042 zaliczony: 200 testow backendu, 31 Playwright, ruff/format, TypeScript/ESLint/build, Alembic, pelny Compose z migracja 0008, restartem i przejsciem na obrazy. Nowe scenariusze sprawdzaja grupy/filtry, przeciecia bez podwojnego liczenia, rewizje, idempotencje, izolacje wlascicieli, katalog prywatnych ETF/REIT, brak FX jako brak danych, szesc kolumn i wejscie w instrument. Smoke potwierdza trwalosc skladu portfela i wynikow na syntetycznych zakupach, obligacjach oraz cenach. Dotychczasowe scenariusze ewidencji pozostaly aktywne i otwieraja wtorny panel operacji jawnie.

Lokalnie git diff --check zaliczone. Nie uruchamiano testow na portfelu uzytkownika ani nie tworzono w nim aktywow/grup. Brak nowych zasad odsetek/podatkow/dywidend i migracji operacji pomiedzy rachunkami. REIT oznacza papier gieldowy. Dokumentacja definicji: portfolios.md.

## FT-015 - Automatyczne kursy NBP, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46068427463: 202 testy backendu, 34 Playwright, TypeScript/ESLint/build, Ruff, Alembic oraz pełny Compose i przejście na obrazy zaliczone. Sprawdzono pobranie NBP przy otwarciu strony z pustym i istniejącym cache, aktualizację sum PLN bez klikania, wartość i wynik w EUR przy awarii bez pętli ponowień oraz uzupełnienie 14 par waluta/data w partiach 8+6 bez powtarzania bieżącego kursu. Frontend pobiera kolejne partie w trybie only_missing. Publiczne odczyty NBP i Yahoo również zaliczone, osobno od testów z atrapami. Końcowy kod podlega standardowym kontrolom CI bez kroku formatowania źródeł w workflow.

Lokalnie git diff --check i docker compose --env-file .env.example config --quiet zaliczone. Bez migracji i operacji na bazie użytkownika. Suma portfela pozostaje niepełna, gdy brak kursów; znane kwoty i wynik pozycji pokazujemy w walucie instrumentu z jawnym oznaczeniem.

## FT-016 - Obligacje w Dodaj instrument, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46070421678: 202 testy backendu, 35 Playwright, TypeScript/ESLint/build, Ruff, Alembic, pełny Compose i przejście na gotowe obrazy zaliczone. Testy obligacji przechodzą teraz przez wybór Rodzaj aktywa → Obligacje: zapis TOS/COI/EDO, rachunki zwykły/IKE/IKZE, korekta, audyt, ponowienie i trwałość. Nowy scenariusz sprawdza zamianę pól giełdowych na obligacje, marżę wyłącznie dla COI/EDO, powrót do ETF z zachowaniem szkicu danych instrumentu i brak zagnieżdżonych formularzy.

Sekcja Instrumenty korzysta z dotychczasowego komponentu obligacji i endpointów. Podczas zapisu zablokowana jest zmiana rodzaju i zamknięcie formularza. Brak zmian schematu bazy i zasad odsetek. Lokalnie git diff --check oraz docker compose --env-file .env.example config --quiet zaliczone; bez operacji na rzeczywistych aktywach użytkownika.

## FT-017 - Rachunek przy rejestracji instrumentu, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46072611500: 207 testów backendu, 38 Playwright, Ruff/format, TypeScript/ESLint/build, Alembic, pełny Compose, restart i przejście na gotowe obrazy zaliczone. Nowe scenariusze obejmują trwałe przypisanie akcji/ETF/REIT do istniejących rachunków, idempotencję, wiele rachunków, odrzucenie braku/nieistniejącego/cudzego/niezgodnego rachunku, izolację katalogu i brak fikcyjnych pozycji finansowych. Migracja 0008 → 0009 zachowuje dotychczasowe zakupy i ich przypisania odczytywane przez katalog.

Przeglądarka sprawdza wybór i przywrócenie rachunku po odświeżeniu, brak pól instrumentu przed utworzeniem rachunku, przejście przez utworzenie pierwszego rachunku, zachowanie szkicu po błędzie 404 i analogiczną blokadę zakupu obligacji bez zgodnego rachunku. Lokalnie git diff --check oraz docker compose --env-file .env.example config --quiet zaliczone. Testy wyłącznie na danych syntetycznych; brak operacji na bazie użytkownika.

## FT-018 - Jeden widok instrumentów, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46074516765: 208 testów backendu i 39 Playwright, Ruff/format, TypeScript/ESLint/build, Alembic, pełny Compose, restart i przejście na obrazy zaliczone. Dotychczasowe osiem scenariuszy zakupów/wyceny ETF przechodzi przez wspólny widok: ułamki, walidacja precyzji, korekta z audytem, utracona odpowiedź, historia cen, przeterminowana wycena, ponowne otwarcie i mobile. Nowy scenariusz potwierdza dostęp do istniejących zakupów i cen IUSQ bez sekcji Operacje ETF EUR. Backend wymaga jawnego listing_id, brak parametru zwraca 422.

Usunięto dwa duplikaty komponentów, ich style, domyślny IUSQ w routingu wyceny oraz nieużywane przygotowywanie pustych rachunków starej sekcji (seed_browser i krok CI). Testy tworzą własne syntetyczne rachunki przez wspólne API. Klient API i audyt są w shared, katalog i pozycja w instruments. Zachowano wspólną logikę zakupów, cen, wycen, audytu oraz katalog i mapowanie Yahoo IUSQ. Bez migracji, usuwania danych i testów na bazie użytkownika. Lokalnie git diff --check oraz docker compose --env-file .env.example config --quiet zaliczone.

## FT-019 - Historia zakupów bez panelu Pozycja, 2026-11-27

CI https://github.com/GroteJongen/FinancialTracker/actions/runs/46076765321: 208 testów backendu, 35 Playwright, Ruff/format, TypeScript/ESLint/build, Alembic oraz pełny Compose i gotowe obrazy zaliczone. Regresja sprawdza brak nagłówka Pozycja, kafelków, formularza ceny i nowego zakupu oraz brak GET valuation z widoku historii. Istniejące zakupy i ceny pozostają w bazie, a wycena nadal jest dostępna w dashboardzie i API. Korekty ułamkowych zakupów, wymagany powód, zachowanie błędnego szkicu, anulowanie, audyt, różne rachunki/waluty, ponowne otwarcie i mobile zaliczone.

Usunięto InstrumentPosition, jego stan i pobieranie wyceny, obsługę zapisu ceny/nowego zakupu oraz nieużywane style. PurchaseHistory wyświetla zakupy i otwiera formularz korekty tylko po wybraniu wiersza. Cztery scenariusze UI usuniętych formularzy wyceny usunięto; logika finansowa nadal ma 208 testów backendu. Bez zmian backendu, schematu i operacji na danych użytkownika. Lokalnie git diff --check i docker compose --env-file .env.example config --quiet zaliczone.
