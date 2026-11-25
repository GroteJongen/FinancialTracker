"""Validation shared by purchase commands; no HTTP, ORM or market data dependencies."""

import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

DECIMAL_PATTERN = re.compile(r"^[0-9]{1,10}(?:\.[0-9]{1,8})?$")


def business_today() -> date:
    return datetime.now(ZoneInfo("Europe/Warsaw")).date()


def parse_amount(value: object, *, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, str) or not DECIMAL_PATTERN.fullmatch(value):
        raise ValueError("Podaj liczbę: do 10 cyfr przed i 8 po kropce.")
    result = Decimal(value)
    if result < 0 or (result == 0 and not allow_zero):
        raise ValueError("Wartość musi być większa od zera.")
    return result


def parse_trade_date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Podaj datę w formacie RRRR-MM-DD.")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Podaj poprawną datę zakupu.") from exc
    if result > business_today():
        raise ValueError("Data zakupu nie może być późniejsza niż dzisiaj.")
    return result
