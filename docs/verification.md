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

FT-001 nie zawiera jeszcze dodawania inwestycji, obliczeń finansowych, uwierzytelniania internetowego ani publicznego wdrożenia. Program działa lokalnie i nie powinien być wystawiany do internetu w obecnym trybie.
