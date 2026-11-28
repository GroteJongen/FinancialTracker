"""Gross accrued retail-bond value: annual ACT/ACT, nominal 100 PLN.

COI uses annual coupons; TOS/EDO capitalize. No tax, early-exit fee or
assumption that a due coupon has actually reached a bank account.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext

from app.domain.bonds import BOND_TERMS


class MissingBondData(ValueError):
    pass


def anniversary(start: date, years: int) -> date:
    year = start.year + years
    return date(year, start.month, min(start.day, monthrange(year, start.month)[1]))


def inflation_month(start: date) -> tuple[int, int]:
    # A period uses CPI announced in the preceding calendar month, i.e. the
    # year-on-year index referring to two calendar months before the period.
    months = start.year * 12 + start.month - 1 - 2
    return months // 12, months % 12 + 1


def cents(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BondAccrual:
    value: Decimal
    due_interest: Decimal
    accrued_interest: Decimal
    current_rate: Decimal
    capitalized_interest: Decimal
    maturity: date


def accrue(
    kind: str,
    bought: date,
    quantity: int,
    annual_rate: Decimal | None,
    margin: Decimal | None,
    mode: str,
    as_of: date,
    inflation: dict[tuple[int, int], Decimal],
) -> BondAccrual:
    if (
        kind not in BOND_TERMS
        or bought > as_of
        or not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        raise ValueError("Invalid bond position")
    expected = "PAYOUT" if kind == "COI" else "CAPITALIZE"
    if mode != expected:
        raise ValueError("Interest mode conflicts with the retail-bond type")
    if annual_rate is None:
        raise MissingBondData("missing_bond_rate")
    if not annual_rate.is_finite() or not Decimal("0") <= annual_rate <= Decimal("100"):
        raise ValueError("Invalid rate")
    if margin is not None and (
        not margin.is_finite() or not Decimal("0") <= margin <= Decimal("100")
    ):
        raise ValueError("Invalid margin")
    years = BOND_TERMS[kind]
    maturity = anniversary(bought, years)
    effective = min(as_of, maturity)
    with localcontext(prec=80, rounding=ROUND_HALF_UP):
        nominal = Decimal("100")
        principal = nominal
        due = Decimal("0")
        current_rate = annual_rate
        for period in range(years):
            start = anniversary(bought, period)
            stop = anniversary(bought, period + 1)
            if period:
                if effective <= start:
                    break
                if kind != "TOS":
                    key = inflation_month(start)
                    if margin is None:
                        raise MissingBondData("missing_bond_margin")
                    if key not in inflation:
                        raise MissingBondData("missing_bond_inflation")
                    if not inflation[key].is_finite() or not Decimal("-100") < inflation[
                        key
                    ] < Decimal("900"):
                        raise ValueError("Invalid inflation")
                    current_rate = max(Decimal("0"), inflation[key]) + margin
            rate = current_rate / Decimal("100")
            if effective < stop:
                base = (
                    cents(principal)
                    if kind == "TOS"
                    else principal
                    if mode == "CAPITALIZE"
                    else nominal
                )
                unit_value = cents(
                    base
                    * (1 + rate * Decimal((effective - start).days) / Decimal((stop - start).days))
                )
                accrued = unit_value - cents(principal)
                return BondAccrual(
                    unit_value * quantity,
                    due * quantity,
                    accrued * quantity,
                    current_rate,
                    (cents(principal) - nominal) * quantity,
                    maturity,
                )
            if mode == "PAYOUT":
                due += cents(nominal * rate)
            else:
                principal *= Decimal("1") + rate
        value = cents(principal) if mode == "CAPITALIZE" else nominal
        return BondAccrual(
            value * quantity,
            due * quantity,
            Decimal("0"),
            current_rate,
            (value - nominal) * quantity,
            maturity,
        )
