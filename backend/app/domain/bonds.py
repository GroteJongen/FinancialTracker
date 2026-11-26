"""Retail bond entry validation, without interest or tax assumptions."""

import re
from decimal import Decimal

from app.domain.purchases import parse_amount

BOND_TERMS = {"TOS": 3, "COI": 4, "EDO": 10}


def parse_series(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Podaj serię obligacji, np. TOS1129.")
    value = value.strip().upper()
    if not re.fullmatch(r"(?:TOS|COI|EDO)(?:0[1-9]|1[0-2])[0-9]{2}", value):
        raise ValueError("Podaj serię TOS, COI lub EDO z miesiącem i rokiem, np. TOS1129.")
    return value


def parse_rate(value: object) -> Decimal | None:
    if value is None:
        return None
    amount = parse_amount(value, allow_zero=True)
    if amount > Decimal("100"):
        raise ValueError("Procent musi mieścić się w zakresie od 0 do 100.")
    return amount


def purchase_cost(quantity: int, unit_price: Decimal) -> Decimal:
    # quantity <= 999999999, unit_price NUMERIC(12,2): product fits Decimal's 28 digits.
    return quantity * unit_price
