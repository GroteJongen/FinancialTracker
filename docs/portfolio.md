# Dashboard portfela — FT-011

„Mój portfel” zbiera zakupione obligacje, ETF-y i akcje z własnych rachunków. Katalog bez zakupów nie jest pozycją portfela. Filtry: wszystkie rachunki, zwykłe, IKE (także IKE_BONDS), IKZE oraz IKE + IKZE. Nie dodajemy demonstracyjnych aktywów do danych użytkownika.

## Kwoty i wynik

- Koszt zakupów: suma kosztów partii, z prowizjami dla papierów giełdowych. Nie jest to suma wpłat zewnętrznych ani przepływów netto.
- Wartość aktywów: suma aktualnych zapisanych wycen pozycji pozostających w portfelu, w PLN.
- Wypłacone odsetki: skumulowane kwoty brutto wypłacone z posiadanych partii obligacji. Nie są dopisywane do aktywów ani udziałów, ponieważ gotówka i jej reinwestowanie nie są ewidencjonowane.
- Łączny wynik = wartość aktywów + wypłacone odsetki − koszt zakupów. Procent = wynik / koszt × 100, bez annualizacji.

Przykład syntetyczny: koszt obligacji 100000 PLN, ETF 50000 PLN i akcji 25000 PLN to koszt 175000 PLN. Jeśli obligacje mają wartość 110000 PLN, a pozostałe pozycje nie zmieniły wartości, aktywa wynoszą 185000 PLN, wynik 10000 PLN (5,71%). Jeśli te same 10000 PLN odsetek zostało już wypłacone, a obligacje mają wartość 100000 PLN, aktywa wynoszą 175000 PLN i wynik nadal 10000 PLN. Nie doliczamy tych samych odsetek dwa razy.

Wynik jest brutto, bez podatków, kosztu przyszłej sprzedaży/wykupu, dywidend akcji, sprzedaży, splitów i zamkniętych pozycji. Nie jest stopą zwrotu ważoną czasem lub przepływami. Podsumowanie odnosi się do operacji obsługiwanych w aplikacji.

## Wyceny i brak danych

ETF/akcje korzystają z cen Yahoo Finance lub ręcznych cen rachunku/notowania; wspólne zasady wyboru ceny opisuje yahoo.md. Cena starsza niż ostatni zakup nie daje wyceny. Każda partia obligacji może otrzymać ręczną wycenę brutto z datą oraz łączną kwotę wypłaconych odsetek brutto od zakupu. Wartość ma obejmować kapitał i odsetki nadal pozostające w obligacjach, z pominięciem już wypłaconych kwot. To zapis rzeczywistych danych rachunku, bez automatycznego naliczania według listu emisyjnego.

Wyceny obligacji są dopisywane, nie nadpisywane. Wybieramy najnowszą datę, następnie czas zapisu, dla aktualnej rewizji zakupu. Korekta zakupu unieważnia użycie wcześniejszej wyceny; historia pozostaje. Powtórzenie tego samego request_id nie tworzy nowego wpisu. Inne dane z tym identyfikatorem dają 409. Wycena nie może poprzedzać zakupu ani dotyczyć przyszłości.

Brak ceny, wyceny obligacji lub kursu walutowego nie jest zerem. Niekompletna pełna wartość lub koszt/wynik są null; interfejs pokazuje przyczyny oraz osobno wartość znanych pozycji. Pełny wykres bieżącej wartości wymaga kompletu wartości wszystkich pozycji. Można wybrać wykres według kosztu, jeśli wszystkie koszty są znane. Portfel pusty ma zerowe kwoty i nie ma wykresu ani procentu wyniku.

## Waluty i NBP

PLN nie wymaga przeliczenia. EUR i USD używają publicznego API NBP, tabela A, przez HTTPS. Dane historyczne i bieżące pobieramy osobno: koszt każdej transakcji według ostatniej tabeli opublikowanej w dniu zakupu lub wcześniej; wartość pozycji według ostatniej dostępnej tabeli dla dnia podsumowania. Szukamy w oknie 14 dni, z zachowaniem rzeczywistej daty publikacji. Brak danych pozostaje brakiem. Źródło: https://api.nbp.pl/ (sprawdzone 2026-11-27).

Koszt walutowy jest szacunkiem NBP, a nie rzeczywistym kosztem przewalutowania u brokera ani regułą podatkową. Wynik obejmuje różnicę kursową względem tak oszacowanego kosztu. Nie przeliczamy dawnych kosztów dzisiejszym kursem. Kurs NBP nie jest kursem wykonania transakcji.

GET dashboardu nie wysyła zapytań sieciowych. Przycisk „Pobierz kursy NBP” pobiera brakujące kursy historyczne i odświeża kursy dla dzisiejszego dnia; maksymalnie 8 zapytań, 4 równocześnie, timeout klienta dostawcy 4 s. Kolejne partie można pobrać ponownie. Cache zachowuje poprzednie dane po awarii. Brak klucza API lub płatnego dostępu. Do NBP przekazujemy tylko walutę i daty, nie rachunki, wartości ani ilości aktywów.

## Technika i testy

Migracja 0006 dodaje append-only bond_valuations i publiczny cache fx_rates. Odczyt blokuje własne rachunki w stałym porządku. Blokada właściciela FOR NO KEY UPDATE serializuje operacje bez blokowania kontroli FK przy jednoczesnym zapisie audytu. Pure domain/portfolio.py liczy Decimal z precyzją co najmniej 80, zaokrągla wyłącznie prezentację. Udziały wykresu są wyliczane metodą największych reszt do 0,01%, sumują się do 100%. Frontend nie wykonuje rachunków finansowych.

API: GET /api/portfolio?scope=ALL|STANDARD|IKE|IKZE|RETIREMENT; POST /api/portfolio/fx/refresh z tym samym filtrem; POST /api/accounts/{id}/bonds/{purchase_id}/valuations z request_id, purchase_revision, value, paid_interest i observed_on. Kwoty wejściowe są tekstem, do 20 cyfr całkowitych i 2 miejsc po kropce. Dostęp do wyceny wymaga własnego rachunku i zakupu. Cache FX nie przechowuje identyfikatora właściciela.

Dashboard odświeża się po udanych zapisach w aplikacji i przyciskiem. Inna karta przeglądarki wymaga odświeżenia. Filtry i wykres mają etykiety dostępności, legenda zawiera kwoty i procenty, widok działa mobilnie. Testy używają syntetycznej partii TOS1129 z ręcznie podaną wartością; nie stanowią weryfikacji odsetek tej emisji. Adapter NBP testujemy atrapami; rzeczywisty odczyt publicznej sieci jest osobnym krokiem CI. Rzeczywiste wyniki kontroli są w verification.md.

## FT-013 - Kurs jednej jednostki

Tabela aktywow pokazuje osobno kurs jednej jednostki papieru w walucie notowania, np. IUSQ / XETR w EUR. Pole unit_price jest tekstem Decimal z tej samej wybranej ceny, ktora sluzy do wyliczenia wartosci pozycji; nie wyliczamy go przez dzielenie zaokraglonych kwot. Nie jest srednim kosztem zakupu. Wycena IUSQ ma osobny kafelek kursu jednostki. Brak ceny pozostaje niedostepny, a starszy zapis zachowuje oznaczenia daty i nieaktualnosci. Dla obligacji detalicznych nie tworzymy fikcyjnego kursu gieldowego. Bez nowych zapytan Yahoo, zmiany priorytetu cen lub migracji bazy.
