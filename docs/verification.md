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

Ograniczenia lokalnego środowiska i profilu testowego Compose pozostają takie jak w FT-001. W tej zmianie nie wdrożono aktualnych cen, wyceny portfela, wyniku inwestycji ani sprzedaży. Cena zapisana przy zakupie jest ceną transakcyjną.
