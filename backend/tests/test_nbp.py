import io
from datetime import date
from decimal import Decimal
from urllib.error import URLError

import pytest

from app.infrastructure import nbp


def payload(mid="4.123456", code="EUR", table="A", day="2026-11-20"):
    return (
        '{"code":"'
        + code
        + '","table":"'
        + table
        + '","rates":[{"no":"TEST/2026","effectiveDate":"'
        + day
        + '","mid":'
        + mid
        + "}]}"
    ).encode()


def test_decimal_and_last_available_table(monkeypatch):
    requests = []

    def open_url(request, timeout):
        requests.append((request.full_url, timeout))
        return io.BytesIO(payload())

    monkeypatch.setattr(nbp, "urlopen", open_url)
    quote = nbp.lookup("EUR", date(2026, 11, 22))
    assert quote.rate == Decimal("4.123456")
    assert quote.effective_on == date(2026, 11, 20)
    assert quote.requested_on == date(2026, 11, 22)
    assert requests[0][0].startswith("https://api.nbp.pl/api/exchangerates/rates/a/eur/")
    assert requests[0][1] == 4


@pytest.mark.parametrize(
    "data",
    [
        payload(mid="-1"),
        payload(mid="0"),
        payload(mid="NaN"),
        payload(code="USD"),
        payload(table="B"),
        payload(day="2099-01-01"),
        b'{"code":"EUR","table":"A","rates":[]}',
        b"x" * 65537,
    ],
)
def test_invalid_provider_payload(data, monkeypatch):
    monkeypatch.setattr(nbp, "urlopen", lambda *args, **kwargs: io.BytesIO(data))
    with pytest.raises(nbp.FxUnavailable):
        nbp.lookup("EUR", date(2026, 11, 22))


def test_network_failure_and_unsupported_dates(monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("synthetic failure")

    monkeypatch.setattr(nbp, "urlopen", unavailable)
    for currency, day in [
        ("EUR", date(2026, 11, 22)),
        ("EUR", date(1900, 1, 1)),
        ("GBP", date(2026, 11, 22)),
    ]:
        with pytest.raises(nbp.FxUnavailable):
            nbp.lookup(currency, day)
