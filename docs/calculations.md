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

Gdy brak zakupów, ilość i koszt to zero, a średni koszt i procent to wartości niedostępne. Bez ceny V, G i R są niedostępne. Uwzględnij tylko operacje nie późniejsze niż data wyceny lub zastosuj ograniczenie pierwszej wersji opisane w product.md.

## Precyzja

Używaj Decimal z tekstu. Robocza precyzja obliczeń: 38 cyfr; kolumny NUMERIC dobierz i opisz w implementacji, z uwzględnieniem jednostek ułamkowych. Nie zaokrąglaj pośrednio średniego kosztu przed liczeniem wyniku. Do prezentacji EUR zaokrąglaj do dwóch miejsc przez ROUND_HALF_UP; procent również do dwóch miejsc. Kwota i procent są liczone z wartości niezaokrąglonych. To reguła prezentacji, nie uniwersalna reguła podatkowa ani obligacyjna.

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
