# Weryfikacja FT-001

Windows: Git, Node 16.1.0 i npm 7.11.2. Brak Dockera i zainstalowanego Pythona. DNS GitHub i npm niedostępny z lokalnego procesu; zapis kodu przez autoryzowaną integrację GitHub.

Lokalnie: node --check scripts/smoke.mjs i git diff --check poprawne. To nie zastępuje testów aplikacji.

CI oczekuje na pierwszy przebieg: lockfile, lint/format Python, migracja i testy PostgreSQL; typy/lint/build frontendu; start Compose, restart, awaria i powrót bazy; przeglądarka i widok mobilny.

Nie wykonano uruchomienia na komputerze użytkownika. Raport zostanie uzupełniony po wynikach CI.
