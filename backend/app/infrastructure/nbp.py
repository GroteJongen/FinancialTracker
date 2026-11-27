"""Public NBP table A; never sends quantities, accounts or portfolio values."""
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from urllib.request import Request, urlopen


class FxUnavailable(Exception):
    pass


@dataclass(frozen=True)
class FxQuote:
    currency: str
    requested_on: date
    effective_on: date
    rate: Decimal
    table_number: str


def lookup(currency: str, requested_on: date) -> FxQuote:
    if currency not in {"EUR", "USD"}:
        raise FxUnavailable("Nieobsługiwana waluta.")
    if requested_on < date(2002, 1, 2):
        raise FxUnavailable("Brak danych NBP dla tego dnia.")
    start = max(date(2002, 1, 2), requested_on - timedelta(days=14))
    url = (
        "https://api.nbp.pl/api/exchangerates/rates/a/"
        f"{currency.lower()}/{start.isoformat()}/{requested_on.isoformat()}/?format=json"
    )
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=4) as response:
            payload = response.read(65537)
        if len(payload) > 65536:
            raise ValueError("Response too large")
        data = json.loads(payload, parse_float=Decimal)
        if data["code"] != currency or data["table"] != "A":
            raise ValueError("Wrong currency or table")
        values = [item for item in data["rates"] if start <= date.fromisoformat(item["effectiveDate"]) <= requested_on]
        chosen = max(values, key=lambda item: item["effectiveDate"])
        rate = chosen["mid"]
        if isinstance(rate, int) and not isinstance(rate, bool):
            rate = Decimal(rate)
        if not isinstance(rate, Decimal) or not rate.is_finite() or not Decimal("0") < rate < Decimal("10000000000") or rate.as_tuple().exponent < -8:
            raise ValueError("Invalid rate")
        number = chosen["no"]
        if not isinstance(number, str) or not 1 <= len(number) <= 40:
            raise ValueError("Invalid table number")
        return FxQuote(currency, requested_on, date.fromisoformat(chosen["effectiveDate"]), rate, number)
    except Exception as exc:
        raise FxUnavailable("Nie udało się pobrać kursu NBP.") from exc
