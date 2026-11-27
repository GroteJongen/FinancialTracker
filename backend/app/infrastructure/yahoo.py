"""Small, replaceable adapter to Yahoo's unofficial public chart endpoint.

No cookies, authentication, scraping, adjusted prices or alternate exchanges.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

MARKETS = {
    "XETR": ({"GER"}, "Europe/Berlin"),
    "XNAS": ({"NMS", "NGM", "NCM"}, "America/New_York"),
    "XNYS": ({"NYQ"}, "America/New_York"),
    "XWAR": ({"WSE", "WAR"}, "Europe/Warsaw"),
}
LIMIT = 128 * 1024


class YahooUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Quote:
    price: Decimal
    quoted_at: datetime
    currency: str
    symbol: str
    mic: str


def symbol_text(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,29}", value):
        raise ValueError("Podaj symbol Yahoo (do 30 znakow), np. IUSQ.DE lub AAPL.")
    return value


def parse(payload: bytes, symbol: str, mic: str, currency: str, kind: str, *, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        if len(payload) > LIMIT or mic not in MARKETS:
            raise ValueError("response/market")
        data = json.loads(payload, parse_float=Decimal, parse_constant=lambda _: None)
        chart = data["chart"]
        if chart.get("error") or len(chart["result"]) != 1:
            raise ValueError("result")
        meta = chart["result"][0]["meta"]
        exchanges, zone = MARKETS[mic]
        if (
            meta["symbol"] != symbol
            or meta["currency"] != currency
            or meta["exchangeName"] not in exchanges
            or meta["exchangeTimezoneName"] != zone
            or meta["instrumentType"] != ("ETF" if kind == "ETF" else "EQUITY")
        ):
            raise ValueError("identity")
        number = meta["regularMarketPrice"]
        if type(number) not in (int, Decimal):
            raise ValueError("price")
        price = Decimal(number)
        if not price.is_finite() or not 0 < price < Decimal("10000000000"):
            raise ValueError("price range")
        with localcontext(prec=40):
            price = price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        if price <= 0:
            raise ValueError("price precision")
        stamp = meta["regularMarketTime"]
        if type(stamp) is not int:
            raise ValueError("time")
        instant = datetime.fromtimestamp(stamp, timezone.utc)
        if instant < datetime(2000, 1, 1, tzinfo=timezone.utc) or instant > now + timedelta(seconds=60):
            raise ValueError("time range")
        return Quote(price, instant, currency, symbol, mic)
    except (KeyError, TypeError, ValueError, IndexError, InvalidOperation, OverflowError) as exc:
        raise YahooUnavailable("Yahoo zwrocilo niezgodne lub niepelne dane notowania.") from exc


def lookup(symbol: str, mic: str, currency: str, kind: str) -> Quote:
    symbol_text(symbol)
    if mic not in MARKETS:
        raise YahooUnavailable("Ta gielda nie jest jeszcze obslugiwana.")
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + quote(symbol, safe="")
    request = Request(
        url + "?interval=1d&range=5d&includePrePost=false",
        headers={"User-Agent": "FinancialTracker/0.1 (personal portfolio)", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=4) as response:
            # Do not follow an upstream redirect to a different host or protocol.
            if response.geturl() != request.full_url:
                raise YahooUnavailable("Nieoczekiwane przekierowanie Yahoo.")
            payload = response.read(LIMIT + 1)
    except (URLError, TimeoutError, OSError) as exc:
        raise YahooUnavailable("Yahoo jest niedostepne lub ogranicza liczbe zapytan.") from exc
    return parse(payload, symbol, mic, currency, kind)


def market_day(instant: datetime, mic: str):
    return instant.astimezone(ZoneInfo(MARKETS[mic][1])).date()
