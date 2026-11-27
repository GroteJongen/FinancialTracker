from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure import yahoo
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import PriceObservation, YahooListing
from app.main import create_app


def buy(client, account, listing=IUSQ_LISTING_ID, currency="EUR"):
    result = client.post(
        f"/api/accounts/{account}/purchases",
        json=dict(
            listing_id=str(listing),
            request_id=str(uuid4()),
            quantity="10",
            unit_price="100",
            commission="2",
            currency=currency,
            trade_date="2026-11-01",
        ),
    )
    assert result.status_code == 201, result.text


def quote(symbol="IUSQ.DE", mic="XETR", currency="EUR", *, at=None):
    return yahoo.Quote(
        Decimal("110.12"), at or datetime.now(UTC) - timedelta(minutes=16), currency, symbol, mic
    )


def expire(engine):
    with Session(engine) as session, session.begin():
        row = session.get(YahooListing, IUSQ_LISTING_ID)
        row.attempted_at = datetime.now(UTC) - timedelta(minutes=6)


def test_automatic_quote_updates_valuation_and_portfolio_with_cache(ledger, monkeypatch):
    client, engine, _, account = ledger
    buy(client, account)
    calls = []

    def lookup(*args):
        calls.append(args)
        return quote()

    monkeypatch.setattr(yahoo, "lookup", lookup)
    assert client.post("/api/market-prices/refresh").json()["updated"] == 1
    price = client.get(
        f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
    ).json()
    assert price["price"]["source"] == "YAHOO"
    assert price["display"]["market_value"] == "1101.20"
    assert price["display"]["gain"] == "99.20"
    assert price["history"] == []
    position = client.get("/api/portfolio").json()["positions"][0]
    assert position["native_value"] == "1101.20"
    assert isinstance(position["unit_price"], str)
    assert Decimal(position["unit_price"]) == Decimal("110.12")
    assert position["quoted_at"] and position["fetched_at"]
    assert client.post("/api/market-prices/refresh").json()["updated"] == 0
    assert len(calls) == 1
    with Session(engine) as session:
        assert list(session.scalars(select(PriceObservation))) == []


def test_failed_refresh_preserves_quote_and_cools_down(ledger, monkeypatch):
    client, engine, _, account = ledger
    buy(client, account)
    monkeypatch.setattr(yahoo, "lookup", lambda *args: quote())
    client.post("/api/market-prices/refresh")
    expire(engine)
    calls = []

    def fail(*args):
        calls.append(1)
        raise yahoo.YahooUnavailable("synthetic")

    monkeypatch.setattr(yahoo, "lookup", fail)
    assert client.post("/api/market-prices/refresh").json()["failed"] == 1
    assert client.post("/api/market-prices/refresh").json()["failed"] == 0
    result = client.get(
        f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
    ).json()
    assert result["display"]["market_value"] == "1101.20"
    assert client.get("/api/portfolio").json()["positions"][0]["yahoo"]["failed"]
    assert len(calls) == 1


def test_newer_manual_wins_until_later_market_quote_and_disable_is_explicit(ledger, monkeypatch):
    client, engine, _, account = ledger
    buy(client, account)
    monkeypatch.setattr(yahoo, "lookup", lambda *args: quote())
    client.post("/api/market-prices/refresh")
    day = datetime.now(UTC).astimezone(ZoneInfo("Europe/Warsaw")).date().isoformat()
    saved = client.post(
        f"/api/accounts/{account}/prices",
        json=dict(
            request_id=str(uuid4()),
            listing_id=str(IUSQ_LISTING_ID),
            price="120",
            currency="EUR",
            observed_on=day,
        ),
    )
    assert saved.status_code == 201
    assert (
        client.get(
            f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
        ).json()["price"]["source"]
        == "MANUAL"
    )
    with Session(engine) as session, session.begin():
        row = session.get(YahooListing, IUSQ_LISTING_ID)
        row.quoted_at = datetime.now(UTC) + timedelta(seconds=1)
    assert (
        client.get(
            f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
        ).json()["price"]["source"]
        == "YAHOO"
    )
    assert client.delete(f"/api/listings/{IUSQ_LISTING_ID}/yahoo").status_code == 200
    assert (
        client.get(
            f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
        ).json()["price"]["source"]
        == "MANUAL"
    )


def test_foreign_holdings_and_empty_portfolio_do_not_make_requests(ledger, monkeypatch):
    client, engine, settings, account = ledger
    monkeypatch.setattr(yahoo, "lookup", lambda *args: pytest.fail("unowned HTTP"))
    assert client.post("/api/market-prices/refresh").json()["updated"] == 0
    buy(client, account)
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert other.post("/api/market-prices/refresh").json()["updated"] == 0
        assert other.get("/api/portfolio").json()["positions"] == []


def test_stock_mapping_is_private_idempotent_and_invalidates_old_quote(ledger, monkeypatch):
    client, engine, settings, account = ledger
    listing = client.post(
        "/api/stocks",
        json=dict(name="Synthetic Yahoo test", symbol="SYN", mic="XNAS", currency="USD"),
    ).json()["id"]
    path = f"/api/listings/{listing}/yahoo"
    buy(client, account, listing, "USD")
    assert client.put(path, json=dict(symbol="aapl")).status_code == 200
    monkeypatch.setattr(yahoo, "lookup", lambda *args: quote("AAPL", "XNAS", "USD"))
    assert client.post("/api/market-prices/refresh").json()["updated"] == 1
    assert client.put(path, json=dict(symbol="AAPL")).status_code == 200
    assert (
        client.get(f"/api/accounts/{account}/valuation?listing_id={listing}").json()["status"]
        == "priced"
    )
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert other.put(path, json=dict(symbol="MSFT")).status_code == 404
        assert other.delete(path).status_code == 404
    assert client.put(path, json=dict(symbol="MSFT")).status_code == 200
    assert (
        client.get(f"/api/accounts/{account}/valuation?listing_id={listing}").json()["status"]
        == "unpriced"
    )
    assert client.put(path, json=dict(symbol="https://localhost")).status_code == 422
    assert client.put(path, json=dict(symbol="MSFT", owner_id=str(uuid4()))).status_code == 422
    assert (
        client.put(f"/api/listings/{IUSQ_LISTING_ID}/yahoo", json=dict(symbol="SSAC.L")).status_code
        == 422
    )


def test_parallel_refresh_has_one_http_call_and_does_not_hold_transaction(ledger, monkeypatch):
    client, engine, settings, account = ledger
    buy(client, account)
    started, release = Event(), Event()
    calls = []

    def lookup(*args):
        calls.append(1)
        started.set()
        assert release.wait(4)
        return quote()

    monkeypatch.setattr(yahoo, "lookup", lookup)

    def refresh():
        with TestClient(create_app(settings, engine)) as parallel:
            return parallel.post("/api/market-prices/refresh")

    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(refresh)
        assert started.wait(4)
        try:
            assert client.post("/api/market-prices/refresh").json()["updated"] == 0
            # Changing the mapping is not blocked by the provider's slow network.
            assert client.delete(f"/api/listings/{IUSQ_LISTING_ID}/yahoo").status_code == 200
        finally:
            release.set()
        assert task.result().json()["updated"] == 0
    assert len(calls) == 1


def test_old_replica_cannot_replace_newer_quote_and_pre_purchase_is_unpriced(ledger, monkeypatch):
    client, engine, _, account = ledger
    buy(client, account)
    good = quote()
    monkeypatch.setattr(yahoo, "lookup", lambda *args: good)
    client.post("/api/market-prices/refresh")
    expire(engine)
    monkeypatch.setattr(yahoo, "lookup", lambda *args: quote(at=datetime(2026, 10, 1, tzinfo=UTC)))
    assert client.post("/api/market-prices/refresh").json()["updated"] == 0
    assert client.get(
        f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
    ).json()["price"]["quoted_at"] == good.quoted_at.isoformat().replace("+00:00", "Z")
    with Session(engine) as session, session.begin():
        row = session.get(YahooListing, IUSQ_LISTING_ID)
        row.quoted_at = datetime(2026, 10, 1, tzinfo=UTC)
    assert (
        client.get(
            f"/api/accounts/{account}/valuation?listing_id=00000000-0000-4000-8000-000000000004"
        ).json()["status"]
        == "outdated"
    )
    assert client.get("/api/portfolio").json()["positions"][0]["native_value"] is None
