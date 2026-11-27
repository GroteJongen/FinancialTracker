# Zasady obliczeń — wersja 1

## Zakres

Wyłącznie otwarte pozycje utworzone zakupami, bez sprzedaży, w EUR. Wynik jest niezrealizowany i nie obejmuje podatku, przyszłej prowizji sprzedaży ani kosztów przewalutowania. Parametry IKE nie zmieniają tych wzorów.

## Wzory

Dla zakupu i: ilość q_i, cena p_i, prowizja f_i. Dla ceny wyceny P:

- Liczba jednostek Q = suma(q_i).
- Koszt C = suma(q_i × p_i + f_i).
- Średni koszt jednostki = C / Q dla Q > 0.
- Wartość V = Q × P.
- Wynik G = V − C.
- Wynik procentowy R = G / C × 100 dla C > 0.

Gdy brak zakupów, ilość i koszt to zero, a średni koszt i procent to wartości niedostępne. Bez ceny V, G i R są niedostępne. FT-003 uwzględnia wszystkie zakupy danego notowania na rachunku i wymaga ceny co najmniej z dnia ostatniego zakupu. Jeżeli zapisana cena stała się wcześniejsza niż ostatni zakup, V, G i R są niedostępne (status outdated), a Q, C i średni koszt nadal wynikają ze wszystkich zakupów. Aktualizacja ceny przywraca wycenę. Daty przyszłe są odrzucane.

## Precyzja

Używaj Decimal z tekstu. Robocza precyzja obliczeń: co najmniej 38 cyfr, zwiększana dla sumowania dużej liczby zakupów, aby nie tracić cyfr iloczynów NUMERIC(18,8). Każda liczba wejściowa ma do 10 cyfr całkowitych i 8 ułamkowych. Nie zaokrąglaj pośrednio średniego kosztu przed liczeniem wyniku. Do prezentacji EUR zaokrąglaj do dwóch miejsc przez ROUND_HALF_UP; procent również do dwóch miejsc. Kwota i procent są liczone z wartości niezaokrąglonych. Ujemne zero prezentuj jako 0,00. To reguła prezentacji, nie uniwersalna reguła podatkowa ani obligacyjna.

## Przykłady odbioru

| Przypadek | Zakupy | Cena | Koszt | Wartość | Wynik | Wynik % |
|---|---|---|---|---|---|---|
| Prowizja | 10 × 100 + 2 EUR | 110 | 1002,00 | 1100,00 | 98,00 | 9,78% |
| Wiele zakupów | 10 × 100 + 2; 5 × 120 + 1 EUR | 110 | 1603,00 | 1650,00 | 47,00 | 2,93% |
| Strata | 10 × 100 + 2 EUR | 90 | 1002,00 | 900,00 | −102,00 | −10,18% |
| Ułamek | 0,125 × 100 + 0,10 EUR | 104 | 12,60 | 13,00 | 0,40 | 3,17% |
| Bez ceny | 10 × 100 + 2 EUR | brak | 1002,00 | brak | brak | brak |

Testuj też daty, odrzucanie ilości zerowej/ujemnej, niepoprawnej waluty i ujemnej prowizji. Sprawdź zaokrąglenia 1,005 → 1,01 oraz −1,005 → −1,01.

## IUSQ i dywidendy

Fundusz akumulujący nie tworzy w aplikacji osobnej wypłaty dywidendy na rachunek. W przyszłej integracji rozróżnij surowe ceny i serie skorygowane o zdarzenia. Podziały jednostek muszą zmieniać ilość zgodnie ze zdarzeniem; historyczne ceny skorygowane nie mogą bezpośrednio zastępować rzeczywistych kosztów transakcji.

## Rozszerzenie PLN

Koszt w PLN bazuje na rzeczywistym koszcie lub jawnie oznaczonym oszacowaniu. Bieżąca wartość w PLN korzysta z kursu wyceny z datą i źródłem. Nie przeliczaj historycznego kosztu dzisiejszym EUR/PLN. Kurs księgowy/podatkowy jest osobnym zagadnieniem.

## Obligacje — warunek rozpoczęcia

Najpierw pozyskaj list emisyjny konkretnej serii i tabele odsetkowe. Odwzoruj konwencje dni, granice okresów, stopy, kapitalizację lub wypłatę, zaokrąglenia i wcześniejszy wykup. Testy mają zawierać wartości z tabel oraz daty graniczne. Rozdziel wartość naliczoną, kwotę wykupu i prognozę. Nie wyliczaj przyszłych stóp jako znanych. Zasady rachunku/podatku ustal po potwierdzeniu rodzaju rachunku obligacji.

## FT-009 — Koszt zakupów obligacji

Koszt partii w PLN = całkowita liczba sztuk × rzeczywista cena jednej sztuki w PLN. Przykład syntetyczny: 10 × 99,90 = 999,00 PLN. To koszt, nie nominał, wycena, odsetki ani wynik. Nominału i cen wykupu nie wyprowadzamy z ceny zakupu. Typowe okresy 3/4/10 lat są metadanymi typu, bez harmonogramu lub wyliczania daty wykupu. Brakujące stopy są null; brak prognozy przyszłej inflacji i podatku. Szczegóły w bonds.md.

## FT-010 — Akcje w walucie notowania

Te same wzory kosztu, średniej, wartości i wyniku stosujemy osobno dla każdego rachunku/notowania akcji w PLN, EUR i USD. Przykład 10 × 100 + 2 prowizji przy cenie 110 daje koszt 1002, wartość 1100, wynik 98 i 9,78% w każdej z tych walut osobno. Waluta bazowa rachunku nie jest kursem przewalutowania. Nie sumujemy różnych walut, nie uwzględniamy dywidend, sprzedaży, splitów ani podatków.

## FT-011 — Suma portfela

Łączny wynik PLN = suma bieżących wartości PLN + skumulowane wypłacone odsetki brutto PLN − suma historycznych kosztów PLN. Walutowy koszt liczony jest dla każdej transakcji po historycznym kursie NBP; bieżąca wartość po aktualnym dostępnym kursie. To szacunek, bez rzeczywistego FX brokera i podatków. Przykład: koszt 175000, wartość 185000, wypłaty 0 daje wynik 10000 i 5,71%. Wartość 175000 i odsetki już wypłacone 10000 daje ten sam wynik, ale inny stan aktywów. Udziały bazują wyłącznie na wartości aktywów lub na koszcie, bez dopisywania wypłaconych kwot. Reguły braków i precyzji: portfolio.md.
