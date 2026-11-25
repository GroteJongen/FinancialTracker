from decimal import Decimal, localcontext

import pytest

from app.domain.valuation import Lot, calculate, money

D = Decimal


@pytest.mark.parametrize(("lots", "price", "cost", "value", "gain", "percent"), [
    ([Lot(D("10"), D("100"), D("2"))], D("110"), "1002.00", "1100.00", "98.00", "9.78"),
    ([Lot(D("10"), D("100"), D("2")), Lot(D("5"), D("120"), D("1"))],
     D("110"), "1603.00", "1650.00", "47.00", "2.93"),
    ([Lot(D("10"), D("100"), D("2"))], D("90"), "1002.00", "900.00", "-102.00", "-10.18"),
    ([Lot(D("0.125"), D("100"), D("0.10"))], D("104"), "12.60", "13.00", "0.40", "3.17"),
    ([Lot(D("10"), D("100"), D("2"))], None, "1002.00", None, None, None),
])
def test_specification_examples(lots, price, cost, value, gain, percent):
    result = calculate(lots, price)
    assert money(result.cost) == cost
    assert money(result.market_value) == value
    assert money(result.gain) == gain
    assert money(result.gain_percent) == percent


def test_empty_and_unpriced_positions():
    empty = calculate([])
    assert empty.quantity == 0 and empty.cost == 0
    assert empty.average_cost is None and empty.gain_percent is None
    assert empty.market_value is None and empty.gain is None
    priced = calculate([], D("100"))
    assert priced.market_value == 0 and priced.gain == 0 and priced.gain_percent is None


def test_half_up_rounding_and_negative_zero():
    assert money(D("1.005")) == "1.01"
    assert money(D("-1.005")) == "-1.01"
    assert money(D("-0.00001")) == "0.00"


def test_calculations_do_not_use_rounded_average_or_money():
    result = calculate([Lot(D("3"), D("0.33333333"), D("0"))], D("0.33333334"))
    assert result.cost == D("0.99999999")
    assert result.market_value == D("1.00000002")
    assert result.gain == D("0.00000003")


def test_independent_of_ambient_precision_and_large_totals():
    lots = [Lot(D("9999999999.99999999"), D("9999999999.99999999"), D("0"))] * 1000
    with localcontext(prec=3):
        result = calculate(lots, D("9999999999.99999999"))
        assert result.cost == D("99999999999999999800000.0000000000001000")
        assert result.gain == 0


@pytest.mark.parametrize("price", [D("0"), D("-1"), D("NaN"), D("Infinity"), 1.5])
def test_invalid_prices_are_rejected(price):
    with pytest.raises(ValueError):
        calculate([], price)
