# Zakres produktu

## Cel i użytkownik

Użytkownik zapisuje aktywa i operacje, sprawdza wartość portfela i źródła wyniku. Pierwsza wersja jest lokalna, prywatna i w języku polskim. Nie zawiera abonamentu ani publicznego wdrożenia.

## Pierwszy pionowy wycinek

1. Użytkownik otwiera aplikację z rachunkiem demonstracyjnym typu IKE.
2. Wybiera skonfigurowany instrument IUSQ, Xetra, EUR.
3. Dodaje datę zakupu, liczbę jednostek, cenę w EUR i prowizję w EUR.
4. Widzi historię zakupów; może poprawić błędny wpis z zachowaniem śladu zmiany.
5. Wpisuje ręczną cenę wyceny i jej datę.
6. Widzi liczbę jednostek, koszt łączny, średni koszt jednostki z prowizją, wartość i niezrealizowany wynik w EUR oraz procentach.
7. Po restarcie dane pozostają zapisane.

Brak ceny oznacza „Brak wyceny”, nie zero. Ręczna cena jest jawnie oznaczona. W pierwszym wydaniu data wyceny musi mieścić się pomiędzy ostatnim zakupem IUSQ na danym rachunku a dniem bieżącym według Europe/Warsaw. Nie wyliczamy historycznej pozycji z pominięciem późniejszych zakupów. Jeśli późniejszy zakup albo korekta daty zakupu wyprzedzi zapisany kurs, cena pozostaje w historii, ale wartość pozycji i wynik są niedostępne do podania odpowiednio datowanej ceny.

Podsumowanie obejmuje wszystkie aktualnie zapisane zakupy IUSQ na wybranym rachunku. Do wyceny wybieramy cenę z najnowszą datą, a przy tej samej dacie — najpóźniej zapisaną obserwację. Starsza obserwacja dodana później nie zastępuje ceny z nowszą datą. Cena ręczna jest prywatna dla rachunku i notowania.

## Ekrany

- Portfel: podsumowanie, tabela pozycji, data i źródło wyceny.
- Operacje: lista zakupów i formularz dodania lub korekty.
- Wycena: formularz ceny ręcznej i historia wpisów.

Walidacja: liczba jednostek i cena dodatnie, prowizja nieujemna; daty zakupów nie późniejsze niż dzisiaj. Komunikaty po polsku. Nadmierna precyzja powoduje czytelny błąd, nie ciche obcięcie.

## Następne wydania

- Dzienne ceny automatyczne i widoczny wiek danych; źródło ręczne zachowane jako awaryjne.
- Wycena w PLN, rzeczywisty koszt transakcji w PLN i jawne źródło kursu walutowego.
- TOS, COI i EDO przypisane do rachunku i konkretnych emisji.
- Eksport, import raportów, sprzedaż i kolejne aktywa.

## Poza pierwszym zakresem

Sprzedaż i sposób rozliczania partii, wynik podatkowy, automatyczne rozliczenia IKE, dywidendy innych instrumentów, logowanie internetowe, prognozy, płatności oraz importy. Typ rachunku IKE jest metadanymi i nie oznacza wdrożenia obsługi wszystkich zasad podatkowych.

## Odbiór

Przykłady w calculations.md przechodzą; zapis przetrwa restart; interfejs rozróżnia brak wyceny i wynik zerowy. Test przeglądarkowy przechodzi od formularza zakupu do wyniku. Nie pokazujemy fikcyjnych danych jako danych użytkownika.

## Dodany zakres FT-009

Użytkownik może ewidencjonować zakupy COI/TOS/EDO na rachunkach PLN typu zwykły, IKE lub IKZE, poprawiać je z historią i zapisywać ręcznie parametry konkretnej emisji. Bieżąca wartość i odsetki obligacji pozostają poza tą zmianą. Patrz bonds.md.

## Dodany zakres FT-010

Użytkownik ma możliwość samodzielnego dodawania akcji do pustego katalogu i ich podglądu. Nie dodajemy wybranych za użytkownika spółek. Podgląd z zakupami i ceną ręczną pokazuje pozycję, koszt i wynik w walucie notowania, z korektami i audytem. Patrz stocks.md.

## Dodany zakres FT-011

Dashboard wszystkich zakupionych aktywów z filtrami zwykłe/IKE/IKZE/razem, sumą PLN, wynikiem i diagramem kołowym. Nie dopisuje aktywów demonstracyjnych. Pokazuje dane niepełne wprost, zapisuje ręczne wyceny obligacji i sumuje wypłacone odsetki; zapewnia referencyjne przeliczenie NBP. Szczegóły: portfolio.md.
