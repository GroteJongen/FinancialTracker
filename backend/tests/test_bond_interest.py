from datetime import date
from decimal import Decimal

import pytest

from app.domain.bond_interest import MissingBondData, accrue, earned_interest, inflation_month

D = Decimal


def test_earned_interest_includes_retained_and_due_amounts_but_not_purchase_discount():
    assert earned_interest(D("1002.20"), D("0"), 10) == D("2.20")
    assert earned_interest(D("1112.10"), D("0"), 10) == D("112.10")
    assert earned_interest(D("1000.20"), D("94"), 10) == D("94.20")
    assert earned_interest(None, D("0"), 10) is None
    assert earned_interest(D("1000"), None, 10) is None
    assert earned_interest(D("900"), D("0"), 10) is None


def test_tos_official_maturity_example_and_cap():
    # TOS0829 official list: 100 * 1.044**3 = 113.79 per bond.
    result = accrue("TOS", date(2026, 8, 1), 2, D("4.4"), None, "CAPITALIZE", date(2029, 8, 1), {})
    assert result.value == D("227.58")
    assert result.due_interest == 0
    assert result.capitalized_interest == D("27.58")
    assert (
        accrue("TOS", date(2026, 8, 1), 2, D("4.4"), None, "CAPITALIZE", date(2040, 1, 1), {}).value
        == result.value
    )


def test_tos_capitalizes_instead_of_paying_coupons():
    result = accrue("TOS", date(2026, 1, 1), 10, D("10"), None, "CAPITALIZE", date(2027, 7, 2), {})
    assert result.value == D("1154.80")
    assert result.capitalized_interest == D("100.00")
    assert result.accrued_interest == D("54.80")
    assert result.due_interest == 0


def test_coi_uses_real_period_cpi_and_does_not_double_count_paid_interest():
    cpi = {(2025, 9): D("2.9"), (2026, 9): D("4.1")}
    result = accrue(
        "COI", date(2024, 11, 10), 10, D("5"), D("1.5"), "PAYOUT", date(2026, 11, 11), cpi
    )
    assert result.current_rate == D("5.6")
    assert result.due_interest == D("94.00")  # first 5%, then 2.9% + 1.5%
    assert result.value == D("1000.20")
    assert result.capitalized_interest == 0


def test_edo_compounds_each_historical_rate_without_payout():
    result = accrue(
        "EDO",
        date(2024, 11, 10),
        10,
        D("6"),
        D("2"),
        "CAPITALIZE",
        date(2026, 11, 11),
        {(2025, 9): D("2.9"), (2026, 9): D("4.1")},
    )
    assert result.current_rate == D("6.1")
    assert result.value == D("1112.10")
    assert result.capitalized_interest == D("111.90")
    assert result.due_interest == 0


def test_actual_period_length_includes_leap_day():
    result = accrue("TOS", date(2023, 3, 1), 1, D("10"), None, "CAPITALIZE", date(2024, 2, 29), {})
    assert result.value == D("109.97")


def test_missing_cpi_is_not_replaced_with_initial_rate():
    with pytest.raises(MissingBondData, match="inflation"):
        accrue("EDO", date(2024, 11, 10), 1, D("6"), D("2"), "CAPITALIZE", date(2026, 1, 1), {})
    with pytest.raises(MissingBondData, match="margin"):
        accrue("COI", date(2024, 11, 10), 1, D("5"), None, "PAYOUT", date(2026, 1, 1), {})


def test_deflation_floor_and_announcement_month():
    assert inflation_month(date(2026, 1, 15)) == (2025, 11)
    result = accrue(
        "COI",
        date(2024, 11, 10),
        1,
        D("5"),
        D("1.5"),
        "PAYOUT",
        date(2025, 11, 11),
        {(2025, 9): D("-0.5")},
    )
    assert result.current_rate == D("1.5")
    assert result.due_interest == D("5.00")


@pytest.mark.parametrize("kind,mode", [("COI", "CAPITALIZE"), ("EDO", "PAYOUT"), ("TOS", "PAYOUT")])
def test_mode_must_follow_actual_product_rules(kind, mode):
    with pytest.raises(ValueError, match="mode"):
        accrue(kind, date(2026, 1, 1), 1, D("5"), D("1"), mode, date(2026, 2, 1), {})
