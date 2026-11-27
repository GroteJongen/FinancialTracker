# Obrazy GHCR i reczna aktualizacja lokalna

Po merge do main workflow CI publikuje obrazy dopiero po zaliczeniu backendu,
frontendu i Compose. PR-y sprawdzaja testy/budowanie/konfiguracje, ale nie publikuja
obrazow ani nie otrzymuja uprawnienia packages:write. Publikacja odbywa sie przez
GITHUB_TOKEN kroku GitHub Actions; nie wymaga dodania PAT do sekretow repozytorium.

Obrazy dla tego repozytorium:

- ghcr.io/grotejongen/financialtracker-backend:sha-<pelny-commit>
- ghcr.io/grotejongen/financialtracker-frontend:sha-<pelny-commit>

Backend i migracje korzystaja z tego samego obrazu. Wydanie wybieramy wspolnym
tagiem SHA, nie dwoma niezaleznie przesuwanymi tagami latest/main. Pierwsze obrazy
pojawią sie dopiero po scaleniu tego PR i udanym zadaniu publish-images. Przerwana
publikacja jednego obrazu nie jest uznawana przez aktualizator za gotowe wydanie.
Publikowane sa obrazy Linux amd64 dla Docker Desktop z silnikiem Linux.

## Pierwsze pobranie

1. Pobierz zmiany z main zawierajace ten plik, skrypt i compose.ghcr.yaml.
2. Zachowaj istniejacy .env (szczegolnie haslo i nazwe dotychczasowej bazy).
   Przy calkiem nowej instalacji skopiuj .env.example do .env i ustaw wlasne haslo.
3. Poczekaj na zielone CI na main, w tym zadanie publish-images.
4. Nowe pakiety GHCR sa domyslnie prywatne, niezaleznie od publicznego repozytorium.
   Dla prywatnych obrazow zaloguj Docker poleceniem ponizej. Jako haslo wpisz PAT
   classic z read:packages, utworzony na swoim koncie GitHub. Nie zapisuj tokenu
   w .env, repozytorium, historii polecen ani rozmowie. Alternatywnie mozesz swiadomie
   ustawic oba pakiety jako publiczne w GitHub Packages i pobierac bez logowania.

```powershell
docker login ghcr.io -u GroteJongen
```

Docker Desktop musi dzialac. Porty pozostaja lokalne: 127.0.0.1:5173 i :8000.
Kod aplikacji oraz zaleznosci sa w obrazach; plik .env i portfel pozostaja lokalnie.

## Tylko pobranie obrazow, bez uruchamiania

```powershell
.\scripts\update.ps1 -PullOnly
```

Skrypt wybiera najnowszy udany CI typu push na main z zakonczonym sukcesem
publish-images (sprawdza do 20 ostatnich udanych CI). Pobiera obrazy, weryfikuje
etykiety commita obu aplikacji i zapisuje wybrane APP_VERSION/IMAGE_PREFIX w
ignorowanym przez Git pliku .env.ghcr. Nie uruchamia ani nie zatrzymuje kontenerow.

Wydanie mozesz wybrac sam: `-Version sha-<pelne-40-znakowe-SHA>` z podsumowania CI.
Opcja ta nie wymaga API GitHub; nieopublikowana wersja zatrzyma sie na pobieraniu.
Przy prywatnym repozytorium zapytania o CI moga wymagac GH_TOKEN z odczytem Actions;
logowanie Docker do GHCR jest odrebne. Publiczny FinancialTracker nie wymaga GH_TOKEN.

Po wybraniu wydania mozesz uzywac bezposrednio Compose:

```powershell
docker compose --env-file .env --env-file .env.ghcr -f compose.ghcr.yaml pull
docker compose --env-file .env --env-file .env.ghcr -f compose.ghcr.yaml up --no-build --pull never -d --wait --wait-timeout 300
```

Obie komendy dotycza przypietego wydania. Aby wybrac nowsze, ponownie uruchom
update.ps1 -PullOnly lub zmien APP_VERSION na SHA udanej publikacji. Przy recznych
komendach usun ewentualne APP_VERSION/IMAGE_PREFIX ze zmiennych sesji PowerShell,
jezeli nadpisuja plik .env.ghcr. Sam skrypt odklada i przywraca te zmienne.

## Pobranie i uruchomienie jednym recznym poleceniem

```powershell
.\scripts\update.ps1
```

Skrypt pobiera komplet obrazow przed zmiana uslug, czeka na baze, uruchamia migracje
nowego backendu i dopiero po sukcesie uruchamia frontend/backend z kontrola gotowosci.
Blad pobierania, rewizji obrazu lub migracji zatrzymuje kolejne kroki i nie nadpisuje
poprzedniego .env.ghcr. Baza mogla juz otrzymac migracje, jezeli blad wystapil przy
uruchamianiu aplikacji; nie wykonujemy automatycznego downgrade ani pozornego rollbacku.
Nie tworzymy harmonogramu ani zadania dzialajacego w tle.

Zachowany jest projekt Compose financialtracker i wolumen financialtracker_postgres-data,
tak jak w dotychczasowym compose.yaml. Jezeli wczesniej uzywales innej nazwy projektu
(COMPOSE_PROJECT_NAME lub -p), zachowaj te sama nazwe przez COMPOSE_PROJECT_NAME w .env.
Nie uruchamiaj dwoch projektow z ta sama baza lub zajetymi portami. Nie dodawaj -v
do down. Przed zmiana schematu zachowaj kopie waznej bazy; cofniecie samego obrazu
nie cofa migracji. Brak automatycznej kopii lub odtworzenia bazy w tym zadaniu.

Tryb programistyczny nadal korzysta z compose.yaml i lokalnego --build. Tryb GHCR
uruchamiaj tylko z -f compose.ghcr.yaml, bez laczenia obu plikow - inaczej pozostanie build.
Polecenia exec/down w trybie GHCR takze wymagaja tych samych plikow konfiguracji.
Nie trzeba pobierac z Git calego kodu przy kazdym wydaniu, ale nowsza wersja skryptu
lub Compose moze wymagac pobrania odpowiednich zmian z repozytorium.

## Kontrole

- `node scripts/check-ghcr.mjs`: statyczna konfiguracja Compose, brak build,
  identyczna wersja backend/migrate, lokalne porty i ta sama nazwa wolumenu.
- `powershell -NoProfile -File scripts/tests/update.tests.ps1`: izolowane testy
  PowerShell 5.1 bez Dockera, rejestru i rzeczywistych danych. CI uruchamia tez pwsh.
- CI sprawdza przelaczenie z lokalnych obrazow na prebuilt bez utraty syntetycznych danych.
- Zadanie publish-images buduje i uruchamia dokladnie te obrazy, ktore wysyla do GHCR.

Zrodla sprawdzone 2026-11-27:

- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- https://docs.github.com/en/rest/actions/workflow-runs
- https://docs.docker.com/reference/cli/docker/compose/pull/
- https://docs.docker.com/reference/cli/docker/compose/up/
