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
