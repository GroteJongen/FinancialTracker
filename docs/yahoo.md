# Automatyczne kursy Yahoo Finance (FT-005)

Po otwarciu/odswiezeniu strony oraz kliknieciu „Odswiez podsumowanie” frontend
wywoluje POST /api/market-prices/refresh. Dashboard odczytuje baze od razu,
a po zakonczeniu pobierania ponownie odczytuje wyceny. GET nie pobiera danych z sieci.
Brak platnego API, klucza, nowej zaleznosci, harmonogramu lub serwera WebSocket.

## Obsluga

Migracja 0007 ustawia IUSQ.DE dla istniejacego IUSQ / XETR / EUR. Nie dodaje
zakupow ani aktywow. Yahoo jest wywolywane tylko dla notowan z zakupami wlasciciela,
raz na 5 minut na notowanie, takze po nieudanej probie. Jedno wywolanie obejmuje
do 8 notowan (4 rownoczesne zapytania, timeout 4 s). Kolejne odswiezenie moze
pobrac nastepna partie; nie ponawia od razu zapytan ograniczonych przez dostawce.

W „Moj portfel” rozwin „Automatyczne kursy Yahoo Finance”. Dla zakupionych akcji
wpisz dokladny symbol Yahoo dla danej spolki/gieldy/waluty. Nie zgadujemy symboli.
Obslugiwane MIC: XETR, XNAS, XNYS, XWAR. Wylaczenie Yahoo usuwa mapowanie/cache
tego notowania i przywraca reczne wyceny; nie usuwa historii cen recznych.
Ponowne wlaczenie IUSQ wymaga wpisania IUSQ.DE. Mapowania nie sa ponownie tworzone
przy restarcie. Konfiguracja notowania dotyczy wszystkich rachunkow z tym notowaniem.

PUT /api/listings/{listing_id}/yahoo przyjmuje wylacznie {"symbol":"IUSQ.DE"}.
DELETE tej samej sciezki wylacza pobieranie. Zapis innego symbolu uniewaznia cache;
zapis identycznego symbolu zachowuje cache i limit. Operacje na obcych akcjach sa
odrzucane. Publiczny katalog IUSQ dotyczy lokalnej aplikacji, nie hostingu dla wielu osob.

## Cena i pierwszenstwo

Adapter czyta nieskorygowane regularMarketPrice i regularMarketTime z metadanych
publicznego, nieoficjalnego endpointu chart. Nie uzywa adjusted close ani NAV.
Weryfikuje dokladny symbol, typ ETF/EQUITY, gielde, walute i strefe czasowa.
W przypadku niezgodnosci zachowuje poprzedni cache. To nie jest automatyczna
weryfikacja ISIN; uzytkownik sprawdza, czy przypisal wlasciwa spolke, nie inna na tej samej gieldzie.

JSON jest parsowany bez float, do Decimal. Cena NUMERIC(18,8) jest zaokraglana
HALF_UP do 8 miejsc; wartosci ujemne, zerowe, niefinitywne i poza zakresem sa odrzucane.
Data automatycznej ceny wynika z czasu notowania w strefie gieldy. Nowszy dzien
wyceny ma pierwszenstwo; w tym samym dniu porownujemy czas notowania Yahoo
z czasem zapisu recznej ceny. Nowa reczna cena wygrywa do pojawienia sie pozniejszego
notowania, a wylaczenie Yahoo pozostawia stale pierwszenstwo cen recznych.
Historia /valuation.history nadal zawiera tylko reczne wpisy.

Czas notowania (UTC), czas poprawnego pobrania i ostatnia proba sa odrebne.
W interfejsie godziny sa w Europe/Warsaw. Xetra jest oznaczona jako opozniona
okolo 15 minut; nie gwarantujemy streamingu live ani konkretnego opoznienia innych rynkow.
Po zamknieciu sesji pozostaje ostatni kurs regularnej sesji. Ceny starsze niz 4 dni
sa oznaczone w dashboardzie; odswiezenie nie udaje nowego czasu notowania.
Cena sprzed ostatniego zakupu nadal blokuje pelna wycene. Waluty PLN wymagaja
osobnych kursow NBP; integracja Yahoo nie zmienia historycznych kosztow zakupow.

## Awarie i spojnosci

Cache i limit sa w PostgreSQL, zachowuja sie po restarcie oraz obsluguja wiele procesow.
Krotka transakcja rezerwuje probe, HTTP odbywa sie poza transakcja, druga zapisuje
wynik tylko dla nadal aktualnego tokenu. Zmiana/wylaczenie mapowania w trakcie HTTP
uniemozliwia zapis starej odpowiedzi. Starsza odpowiedz nie cofa poprawnego kursu.
429, timeout, brak notowania i niezgodna tozsamosc nie kasuja ostatniej ceny.
Nie obchodzimy blokad dostawcy, nie pobieramy cookies/hasel i nie logujemy portfela.

Nie dodano automatycznej wyceny detalicznych obligacji, dywidend ani splitow.

## Weryfikacja i warunki

Testy adaptera i API uzywaja atrap; testy przegladarki blokuja prawdziwe odswiezenia
Yahoo, aby nie zmieniac syntetycznych ledgerow danymi rynkowymi. Oddzielny odczyt
sieciowy: `cd backend`, `python -m tests.network_yahoo`. Jego wynik jest raportowany
osobno od testow deterministycznych i nie przesadza o dostepnosci z innego adresu IP.
Standardowy CI sprawdza migracje od pustej bazy i zgodnosc modeli; smoke sprawdza
przetrwanie syntetycznej ceny i mapowania po restarcie Compose.

Zrodla sprawdzone 2026-11-27:

- https://finance.yahoo.com/quote/IUSQ.DE/
- https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html
- https://github.com/ranaroussi/yfinance (charakter nieoficjalny i uzytek osobisty)
- https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py (format chart)

To integracja do prywatnego uzytku, bez gwarancji dostepnosci. Nie zapewnia praw
do komercyjnej redystrybucji. Przy takiej zmianie zastosowania nalezy dobrac
dostawce i odpowiednie uprawnienia. Nie uzalezniamy modelu domenowego od Yahoo.
