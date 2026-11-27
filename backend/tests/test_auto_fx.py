from decimal import Decimal
from uuid import uuid4

from app.domain.purchases import business_today
from app.infrastructure import nbp
from app.infrastructure.catalog import IUSQ_LISTING_ID
from tests.test_portfolio import buy


def test_native_values_exist_without_fx_and_missing_only_batches_finish(ledger, monkeypatch):
    client, _, _, account_id = ledger
    # Synthetic holding, independent of the user's quantities and prices.
    buy(client, account_id, IUSQ_LISTING_ID, "EUR", "10", "100")
    for day in range(1, 13):
        result = client.post(
            f"/api/accounts/{account_id}/purchases",
            json=dict(
                listing_id=str(IUSQ_LISTING_ID),
                request_id=str(uuid4()),
                trade_date=f"2026-10-{day:02d}",
                quantity="1",
                unit_price="100",
                commission="0",
                currency="EUR",
            ),
        )
        assert result.status_code == 201
    result = client.post(
        f"/api/accounts/{account_id}/prices",
        json=dict(
            listing_id=str(IUSQ_LISTING_ID),
            request_id=str(uuid4()),
            observed_on="2026-11-21",
            price="110",
            currency="EUR",
        ),
    )
    assert result.status_code == 201
    initial = client.get("/api/portfolio").json()
    assert initial["totals"]["value"] is None
    row = initial["positions"][0]
    assert row["native_value"] == "2420.00"
    assert row["native_gain"] == "220.00"
    assert row["native_gain_percent"] == "10.00"
    calls = []

    def lookup(currency, day):
        calls.append((currency, day))
        return nbp.FxQuote(
            currency,
            day,
            day,
            Decimal("5") if day == business_today() else Decimal("4"),
            "SYNTHETIC/TEST",
        )

    monkeypatch.setattr(nbp, "lookup", lookup)
    first = client.post("/api/portfolio/fx/refresh?only_missing=true").json()
    assert first == dict(updated=8, failed=0, remaining=6)
    second = client.post("/api/portfolio/fx/refresh?only_missing=true").json()
    assert second == dict(updated=6, failed=0, remaining=0)
    assert calls.count(("EUR", business_today())) == 1
    assert len(calls) == 14
    assert client.post("/api/portfolio/fx/refresh?only_missing=true").json()["updated"] == 0
    final = client.get("/api/portfolio").json()["totals"]
    assert final["cost"] == "8800.00"
    assert final["value"] == "12100.00"
    assert final["gain"] == "3300.00"


def test_native_result_does_not_require_nbp_and_failures_preserve_it(ledger, monkeypatch):
    client, _, _, account_id = ledger
    buy(client, account_id, IUSQ_LISTING_ID, "EUR", "10", "100")

    def unavailable(*args):
        raise nbp.FxUnavailable("synthetic outage")

    monkeypatch.setattr(nbp, "lookup", unavailable)
    response = client.post("/api/portfolio/fx/refresh?only_missing=true")
    assert response.json()["failed"] == 2
    row = client.get("/api/portfolio").json()["positions"][0]
    assert row["native_value"] == "1000.00"
    assert row["native_gain"] == "0.00"
    assert row["value_pln"] is None
