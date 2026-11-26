# Weryfikacja FT-001

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
