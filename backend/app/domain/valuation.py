"""Pure valuation of an open position consisting only of purchases."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext


@dataclass(frozen=True)
class Lot:
    quantity: Decimal
    unit_price: Decimal
    commission: Decimal


@dataclass(frozen=True)
class Position:
    quantity: Decimal
    cost: Decimal
    average_cost: Decimal | None
    market_value: Decimal | None
    gain: Decimal | None
    gain_percent: Decimal | None


def money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    with localcontext(prec=max(38, value.adjusted() + 3), rounding=ROUND_HALF_UP):
        rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "0.00" if rounded == 0 else format(rounded, "f")


def calculate(lots: Iterable[Lot], price: Decimal | None = None) -> Position:
    rows = list(lots)
    for row in rows:
        for amount in (row.quantity, row.unit_price, row.commission):
            if not isinstance(amount, Decimal) or not amount.is_finite():
                raise ValueError("Wartości muszą być skończonymi liczbami Decimal.")
        if row.quantity <= 0 or row.unit_price <= 0 or row.commission < 0:
            raise ValueError("Nieprawidłowe wartości zakupu.")
    if price is not None and (
        not isinstance(price, Decimal) or not price.is_finite() or price <= 0
    ):
        raise ValueError("Cena wyceny musi być dodatnią liczbą Decimal.")
    # NUMERIC(18,8) products need 36 digits; allow the carry from a large number of lots.
    precision = max(38, 36 + len(str(max(1, len(rows)))))
    with localcontext(prec=precision, rounding=ROUND_HALF_UP):
        quantity = sum((row.quantity for row in rows), Decimal("0"))
        cost = sum((row.quantity * row.unit_price + row.commission for row in rows), Decimal("0"))
        average_cost = cost / quantity if quantity else None
        market_value = quantity * price if price is not None else None
        gain = market_value - cost if market_value is not None else None
        gain_percent = gain / cost * Decimal("100") if gain is not None and cost else None
        return Position(quantity, cost, average_cost, market_value, gain, gain_percent)
