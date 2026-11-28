from decimal import Decimal as D

import pytest

from app.domain.portfolio import Holding, summarize


def test_example_and_exact_allocation():
    result = summarize(
        [
            Holding("BOND", D("100000"), D("110000")),
            Holding("ETF", D("50000"), D("50000")),
            Holding("STOCK", D("25000"), D("25000")),
        ]
    )
    assert result["cost"] == "175000.00"
    assert result["value"] == "185000.00"
    assert result["gain"] == "10000.00"
    assert result["gain_percent"] == "5.71"
    assert sum(D(row["percent"]) for row in result["allocation_value"]) == D("100")
    assert result["allocation_value"][-1]["end"] == "100.00"
    assert [row["percent"] for row in result["allocation_cost"]] == ["57.14", "28.57", "14.29"]


def test_paid_interest_counts_once_and_is_not_a_holding():
    result = summarize([Holding("BOND", D("100000"), D("100000"), D("10000"))])
    assert result["value"] == "100000.00"
    assert result["gain"] == "10000.00"
    assert result["paid_income"] == "10000.00"
    assert result["allocation_value"][0]["amount"] == "100000.00"


def test_earned_interest_is_information_not_an_extra_gain_or_asset():
    result = summarize(
        [
            Holding("BOND", D("999"), D("1100"), D("0"), D("100")),
            Holding("BOND", D("1000"), D("1002"), D("50"), D("52")),
            Holding("ETF", D("500"), D("600")),
        ]
    )
    assert result["earned_interest"] == "152.00"
    assert result["value"] == "2702.00"
    assert result["gain"] == "253.00"
    assert result["paid_income"] == "50.00"
    unknown = summarize([Holding("BOND", D("100"), None, None, None)])
    assert unknown["earned_interest"] is None
    assert unknown["known_earned_interest"] == "0.00"


@pytest.mark.parametrize("missing", ["cost", "value", "paid_income"])
def test_missing_values_never_become_zero(missing):
    values = dict(cost=D("10"), value=D("15"), paid_income=D("0"))
    values[missing] = None
    result = summarize([Holding("BOND", **values)])
    assert result["complete"] is False
    assert result[missing] is None
    assert result["gain"] is None


def test_round_only_after_aggregation_empty_zero_and_loss():
    result = summarize([Holding("ETF", D("0.005"), D("0.004"))] * 2)
    assert result["cost"] == "0.01"
    assert result["value"] == "0.01"
    assert result["gain"] == "0.00"
    assert result["gain_percent"] == "-20.00"
    assert summarize([])["gain_percent"] is None
    assert summarize([])["allocation_value"] == []
    assert summarize([Holding("STOCK", D("100"), D("0"))])["gain"] == "-100.00"


@pytest.mark.parametrize("value", [D("NaN"), D("Infinity"), D("-1"), 1.5])
def test_invalid_amounts(value):
    with pytest.raises(ValueError):
        summarize([Holding("ETF", value, D("1"))])
