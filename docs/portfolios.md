# Wlasne portfele i wspolna lista aktywow - FT-014

Portfel jest wlasna grupa rachunkow, a nie pojedynczym ETF-em. Uzytkownik tworzy
nazwe i wybiera rachunki. Jeden rachunek moze nalezec do kilku portfeli, ale widok
wszystkich rachunkow liczy go tylko raz. Nie tworzymy automatycznie portfeli,
transakcji ani nowych aktywow z istniejacych danych. Filtry zwykly/IKE/IKZE/razem
dzialaja wewnatrz wybranego portfela; IKE obejmuje takze IKE_BONDS.

Na gorze pozostaja laczne kwoty wybranego portfela w PLN. Glowna tabela ma kolumny:
liczba jednostek, nazwa, cena jednostki, wartosc, zysk/strata i wynik procentowy.
Nazwie towarzyszy rachunek, ticker/MIC oraz informacje o wycenie. Pozycje tego samego
instrumentu na roznych rachunkach pozostaja rozdzielone, poniewaz moga miec rozne
koszty i prywatne ceny reczne. Wartosc/wynik/procent sa w PLN wedlug istniejacych
zasad NBP; cena jednostki pozostaje w walucie notowania. Brak danych pozostaje
brakiem, nigdy zerem. Wynik procentowy = wynik / koszt x 100, bez annualizacji.

Obligacje pozostaja oddzielnymi partiami z reczna wycena i wyplaconymi odsetkami.
Cena jednej sztuki to wartosc partii / liczba sztuk; nie jest notowaniem gieldowym
ani nominalem. Odsetki wyplacone wchodza do wyniku, ale nie sa dopisywane do aktywow.
Nie rozszerzamy silnika regul emisji ani przepisow podatkowych.

Katalog obsluguje akcje, rozne ETF-y i gieldowe REIT-y w PLN/EUR/USD. Wpis wymaga
symbolu, MIC i waluty; ISIN jest opcjonalny. Katalog prywatny jest izolowany przez
wlasciciela, a dotychczasowy publiczny IUSQ jest zachowany. Nowy typ nie zgaduje
symbolu Yahoo: mapowanie jest jawne, odpowiedz potwierdza typ/gielde/walute.
REIT gieldowy uzywa ceny papieru wartosciowego; nie obejmuje prywatnych inwestycji
w nieruchomosci ani automatycznej ewidencji dywidend. Kazda przyszla klasa aktywow
otrzyma swoj sposob wyceny, bez zmiany znaczenia portfela.

Glowny ekran nie jest przypisany do IUSQ. Szczegoly otwierasz nazwa instrumentu;
zakupy, korekty, wyceny i katalog znajduja sie w rozwijanej sekcji operacji.
Zachowany formularz operacji ETF w EUR wyswietla wycene wybranego instrumentu,
a katalog ogolny obsluguje takze inne waluty. Rozliczenia i historia pozostaja
przypisane do rachunku i notowania, nie do grupy prezentacyjnej.

API: GET/POST /api/portfolios, PUT /api/portfolios/{id} z expected_revision;
GET /api/portfolio i POST /api/portfolio/fx/refresh z opcjonalnym portfolio_id
i istniejacym scope. POST /api/securities tworzy STOCK/ETF/REIT;
GET /api/listings?kind=ALL obejmuje wlasne instrumenty i publiczny IUSQ.
Stare endpointy zakupow/cen/akcji zachowuja zgodnosc. Kazdy zapis grupy sprawdza
wlasciciela wszystkich rachunkow; nie mozna dolaczyc obcego rachunku ani odczytac
obcego portfela. Nazwa jest unikalna u wlasciciela, ponowiony identyczny POST nie
duplikuje grupy, a zmiany wymagaja aktualnej rewizji. Blokada wlasciciela serializuje
zmiany skladu i odczyt, a kwoty sa Decimal/NUMERIC i tekstem w JSON.

Migracja 0008 dodaje grupy i czlonkostwa oraz rozszerza prywatnosc REIT. Nie zmienia
zakupow, cen ani ich historii. Downgrade odmawia usuniecia zapisanych grup.
