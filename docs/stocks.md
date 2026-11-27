# Akcje — FT-010

Sekcja „Akcje” ma początkowo pusty katalog. Użytkownik sam dodaje spółkę: nazwę, ticker, giełdę (czteroznakowy MIC), walutę PLN/EUR/USD i opcjonalny ISIN. Nazwy, identyfikatory i ceny są wpisywane ręcznie; aplikacja nie sprawdza istnienia spółki ani notowania u dostawcy danych i nie pobiera kursów automatycznie. Sprawdzany jest format identyfikatorów, bez sumy kontrolnej ISIN. Seed nie dopisuje przykładowych spółek, zakupów ani cen.

## Podgląd i operacje

Po wybraniu spółki widoczne są jej identyfikatory i waluta. Użytkownik wybiera lub tworzy rachunek inwestycyjny zwykły, IKE lub IKZE i dodaje zakupy z datą, ilością (także ułamkową), ceną i prowizją. Podgląd pokazuje liczbę akcji, koszt wraz z prowizjami, średni koszt, wartość, wynik kwotowy i procentowy. Bieżąca wycena wymaga ręcznej ceny z datą co najmniej ostatniego zakupu i nie późniejszą niż dziś (Europe/Warsaw). Brak ceny lub jej nieaktualność oznaczają niedostępny wynik, nie zero.

Wszystkie kwoty pozycji są w walucie notowania. Waluta bazowa rachunku nie przelicza kosztów ani wyceny; rachunek może zawierać akcje notowane w różnych walutach. Nie sumujemy PLN, EUR i USD i nie stosujemy dzisiejszego FX do historycznego kosztu. Zasady obliczeń Decimal i dokładność NUMERIC(18,8) są wspólne z ETF. Nie ma obsługi sprzedaży, splitów, dywidend, podatku ani limitów IKE/IKZE. Rachunek IKE_BONDS jest przeznaczony dla obligacji i nie przyjmuje akcji.

Korekta zakupu wymaga powodu i aktualnej rewizji. Nie zmienia tożsamości notowania ani waluty istniejącego zakupu. Audyt przechowuje poprzednie i nowe wartości w jednej transakcji. Zapis i cena używają request_id dla ochrony przed duplikatami po utracie odpowiedzi. Poprawki parametrów katalogu i usuwanie spółek nie są objęte tym zadaniem.

## Prywatność i tożsamość

Dodane akcje są prywatne dla właściciela z konfiguracji backendu. Instrument rozdziela spółkę od notowań; jeden ISIN może mieć różne notowania na różnych giełdach. Unikalność ISIN jest liczona osobno dla właściciela oraz osobno dla publicznego katalogu ETF. Rejestracja jest serializowana blokadą właściciela: identyczny ticker + MIC + waluta z tymi samymi danymi daje istniejący wpis (200); inne dane spółki dla tej tożsamości dają 409. Ta sama para MIC/waluta dla jednego instrumentu nie otrzymuje drugiego tickera bez jawnego przyszłego mechanizmu zmiany metadanych. Ponowienie rejestracji nie tworzy pozycji ani transakcji.

Wspólne endpointy zakupów i cen sprawdzają właściciela rachunku, dostępność notowania dla tego właściciela i zgodność waluty operacji z notowaniem. Ceny są nadal prywatne dla rachunku/notowania. Widok IUSQ filtruje własne notowanie, więc nie miesza zakupów akcji z ETF. Typ rachunku jest metadanymi, nie silnikiem podatkowym.

## API

| Metoda | Ścieżka | Znaczenie |
|---|---|---|
| GET | /api/listings | Publiczny katalog ETF, zgodny z dotychczasowym IUSQ |
| GET | /api/listings?kind=STOCK | Własne notowania akcji |
| POST | /api/stocks | name, symbol, mic, currency, opcjonalny isin; 201 lub 200 przy ponowieniu |
| POST | /api/investment-accounts | name, kind STANDARD/IKE/IKZE, currency PLN/EUR/USD |
| GET/POST | /api/accounts/{id}/purchases | Wspólna ewidencja zakupów akcji i ETF |
| PUT | /api/accounts/{id}/purchases/{purchase_id} | Korekta z reason i expected_revision |
| GET | /api/accounts/{id}/purchases/{purchase_id}/audit | Historia zmian |
| POST | /api/accounts/{id}/prices | Cena ręczna w walucie notowania |
| GET | /api/accounts/{id}/valuation?listing_id=... | Podsumowanie wybranego notowania |

## Migracja i aktualizacja

Migracja 0005 dodaje opcjonalnego właściciela instrumentu i rozszerza waluty zakupów/cen. Publiczne IUSQ oraz dotychczasowe zakupy, ceny i obligacje pozostają zachowane. Nie wprowadzamy danych inwestycyjnych na starcie. Downgrade jest blokowany, jeśli istnieją prywatne akcje lub dane w walucie innej niż EUR, aby nie usuwać ich automatycznie.

Po pobraniu zmian uruchom `docker compose up --build -d --wait --wait-timeout 300` i odśwież aplikację. Stan testów jest w verification.md. Wszystkie scenariusze CI używają syntetycznych danych; nie wykonujemy operacji na portfelu użytkownika.
