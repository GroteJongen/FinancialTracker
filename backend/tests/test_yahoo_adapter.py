import json
from datetime import UTC, datetime
from decimal import Decimal
from urllib.error import HTTPError

import pytest

from app.infrastructure import yahoo

NOW = datetime(2026, 11, 27, 14, tzinfo=UTC)
STAMP = int(NOW.timestamp())


def body(**changes):
    meta = dict(
        symbol="IUSQ.DE",
        currency="EUR",
        exchangeName="GER",
        exchangeTimezoneName="Europe/Berlin",
        instrumentType="ETF",
        regularMarketPrice=106,
        regularMarketTime=STAMP,
    )
    return json.dumps(dict(chart=dict(error=None, result=[dict(meta=meta | changes)]))).encode()


def test_decimal_unadjusted_metadata_and_market_day():
    payload = body().replace(b'"regularMarketPrice": 106', b'"regularMarketPrice": 106.123456789')
    result = yahoo.parse(payload, "IUSQ.DE", "XETR", "EUR", "ETF", now=NOW)
    assert result.price == Decimal("106.12345679")
    assert result.quoted_at == NOW
    assert yahoo.market_day(NOW, "XETR").isoformat() == "2026-11-27"


@pytest.mark.parametrize(
    "changes",
    [
        dict(symbol="SSAC.L"),
        dict(currency="USD"),
        dict(exchangeName="FRA"),
        dict(exchangeTimezoneName="UTC"),
        dict(instrumentType="EQUITY"),
        dict(regularMarketPrice=None),
        dict(regularMarketPrice=True),
        dict(regularMarketPrice="100"),
        dict(regularMarketPrice=0),
        dict(regularMarketPrice=-1),
        dict(regularMarketPrice=10000000000),
        dict(regularMarketTime=None),
        dict(regularMarketTime=True),
        dict(regularMarketTime=STAMP + 600),
        dict(regularMarketTime=1),
    ],
)
def test_invalid_or_mismatched_quote_is_rejected(changes):
    with pytest.raises(yahoo.YahooUnavailable):
        yahoo.parse(body(**changes), "IUSQ.DE", "XETR", "EUR", "ETF", now=NOW)


@pytest.mark.parametrize(
    "payload",
    [b"not json", b"{}", b'{"chart":{"error":{},"result":null}}', b"x" * (yahoo.LIMIT + 1)],
)
def test_malformed_response(payload):
    with pytest.raises(yahoo.YahooUnavailable):
        yahoo.parse(payload, "IUSQ.DE", "XETR", "EUR", "ETF", now=NOW)


@pytest.mark.parametrize(
    "symbol", ["https://localhost", "AAPL?x=1", "../AAPL", "", "aapl", "A" * 31]
)
def test_symbols_cannot_be_urls_or_query_parameters(symbol):
    with pytest.raises(ValueError):
        yahoo.symbol_text(symbol)


def test_rate_limit_becomes_provider_failure(monkeypatch):
    def reject(*args, **kwargs):
        raise HTTPError("https://query1.finance.yahoo.com", 429, "limit", {}, None)

    monkeypatch.setattr(yahoo, "urlopen", reject)
    with pytest.raises(yahoo.YahooUnavailable, match="niedostepne"):
        yahoo.lookup("IUSQ.DE", "XETR", "EUR", "ETF")


def test_redirect_is_rejected_before_contacting_destination():
    with pytest.raises(yahoo.YahooUnavailable, match="przekierowanie"):
        yahoo.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "http://localhost")
