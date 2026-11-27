from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import Instrument, Listing, Owner
from app.main import create_app


def company(**changes):
    return {"name": "Spółka syntetyczna", "symbol": "SYN", "mic": "XWAR", "currency": "PLN", "isin": "PL0000000001"} | changes


def stock(client, **changes):
    result = client.post("/api/stocks", json=company(**changes))
    assert result.status_code in (200, 201), result.text
    return result.json()


def trade(listing, **changes):
    return {"request_id": str(uuid4()), "listing_id": listing["id"], "trade_date": "2026-10-05", "quantity": "10", "unit_price": "100", "commission": "2", "currency": listing["currency"]} | changes


@pytest.mark.parametrize("currency", ["PLN", "EUR", "USD"])
def test_native_currency_purchase_view_correction_and_price(ledger, currency):
    client, _, _, account_id = ledger
    listing = stock(client, currency=currency)
    root = f"/api/accounts/{account_id}"
    empty = client.get(root + "/valuation", params={"listing_id": listing["id"]}).json()
    assert empty["status"] == "empty" and empty["gain"] is None
    data = trade(listing)
    first = client.post(root + "/purchases", json=data)
    assert first.status_code == 201
    assert client.post(root + "/purchases", json=data).status_code == 200
    unpriced = client.get(root + "/valuation", params={"listing_id": listing["id"]}).json()
    assert unpriced["status"] == "unpriced" and unpriced["display"]["cost"] == "1002.00"
    quote = {"request_id": str(uuid4()), "listing_id": listing["id"], "price": "110", "observed_on": "2026-10-06", "currency": currency}
    assert client.post(root + "/prices", json=quote).status_code == 201
    assert client.post(root + "/prices", json=quote).status_code == 200
    result = client.get(root + "/valuation", params={"listing_id": listing["id"]}).json()
    assert result["display"]["gain"] == "98.00"
    assert result["display"]["gain_percent"] == "9.78"
    assert result["currency"] == currency
    correction = {key: value for key, value in data.items() if key != "request_id"} | {"quantity": "9", "expected_revision": 1, "reason": "Syntetyczna korekta ilości"}
    assert client.put(root + "/purchases/" + first.json()["id"], json=correction).status_code == 200
    changed = client.get(root + "/valuation", params={"listing_id": listing["id"]}).json()
    assert changed["display"]["gain"] == "88.00"
    audit = client.get(root + "/purchases/" + first.json()["id"] + "/audit").json()
    assert audit[1]["before"]["currency"] == currency
    assert audit[1]["after"]["quantity"] == "9.00000000"
    assert client.put(root + "/purchases/" + first.json()["id"], json=correction).status_code == 409
    later = client.post(root + "/purchases", json=trade(listing, trade_date="2026-10-07"))
    assert later.status_code == 201
    assert client.get(root + "/valuation", params={"listing_id": listing["id"]}).json()["status"] == "outdated"


def test_catalogue_retry_conflicts_and_market_identity(ledger):
    client, _, _, _ = ledger
    assert client.get("/api/listings?kind=STOCK").json() == []
    first = stock(client)
    again = stock(client, symbol=" syn ", mic=" xwar ", isin=" pl0000000001 ")
    assert again["id"] == first["id"]
    assert client.post("/api/stocks", json=company(name="Inna nazwa")).status_code == 409
    other = stock(client, mic="XETR", currency="EUR")
    assert other["id"] != first["id"]
    assert len(client.get("/api/listings?kind=STOCK").json()) == 2
    assert [item["id"] for item in client.get("/api/listings").json()] == [str(IUSQ_LISTING_ID)]
    assert client.post("/api/stocks", json=company(symbol="OTHER")).status_code == 409


@pytest.mark.parametrize(("field", "value"), [
    ("name", " "), ("name", "a" * 201), ("symbol", "A B"), ("symbol", ""),
    ("symbol", "A" * 31), ("mic", "GPW"), ("mic", "X W "), ("currency", "GBP"),
    ("isin", "bad"), ("isin", "PL000000000A"), ("owner_id", str(uuid4())),
    ("kind", "ETF"),
])
def test_invalid_catalogue_fields_do_not_write(ledger, field, value):
    client, _, _, _ = ledger
    assert client.post("/api/stocks", json=company(**{field: value})).status_code == 422
    assert client.get("/api/listings?kind=STOCK").json() == []


def test_currency_and_position_isolation(ledger):
    client, _, _, account_id = ledger
    first, second = stock(client), stock(client, symbol="SECOND", isin=None, currency="USD")
    root = f"/api/accounts/{account_id}"
    assert client.post(root + "/purchases", json=trade(first, currency="USD")).status_code == 422
    assert client.post(root + "/purchases", json=trade(first)).status_code == 201
    assert client.post(root + "/purchases", json=trade(second, quantity="0.125")).status_code == 201
    quote = {"request_id": str(uuid4()), "listing_id": first["id"], "price": "110", "observed_on": "2026-10-06", "currency": "USD"}
    assert client.post(root + "/prices", json=quote).status_code == 422
    first_view = client.get(root + "/valuation", params={"listing_id": first["id"]}).json()
    second_view = client.get(root + "/valuation", params={"listing_id": second["id"]}).json()
    assert first_view["quantity"] == "10.00000000"
    assert second_view["quantity"] == "0.12500000"
    assert first_view["currency"] == "PLN" and second_view["currency"] == "USD"
    assert client.get(root + "/valuation").json()["status"] == "empty"
    assert len(client.get(root + "/purchases").json()) == 2


def test_private_catalogue_and_foreign_listing_are_not_accessible(ledger):
    client, engine, settings, account_id = ledger
    first = stock(client)
    stranger_id = uuid4()
    stranger_settings = settings.model_copy(update={"local_owner_id": stranger_id})
    try:
        with TestClient(create_app(stranger_settings, engine)) as stranger:
            assert stranger.get("/api/listings?kind=STOCK").json() == []
            other = stock(stranger)
            assert other["id"] != first["id"]
            assert client.post(f"/api/accounts/{account_id}/purchases", json=trade(other)).status_code == 404
            assert client.get(f"/api/accounts/{account_id}/valuation", params={"listing_id": other["id"]}).status_code == 404
            quote = {"request_id": str(uuid4()), "listing_id": other["id"], "price": "110", "observed_on": "2026-10-06", "currency": "PLN"}
            assert client.post(f"/api/accounts/{account_id}/prices", json=quote).status_code == 404
    finally:
        with Session(engine) as session, session.begin():
            ids = select(Instrument.id).where(Instrument.owner_id == stranger_id)
            session.execute(delete(Listing).where(Listing.instrument_id.in_(ids)))
            session.execute(delete(Instrument).where(Instrument.owner_id == stranger_id))
            session.execute(delete(Owner).where(Owner.id == stranger_id))


@pytest.mark.parametrize("kind", ["STANDARD", "IKE", "IKZE"])
def test_investment_accounts_and_treasury_only_account(ledger, kind):
    client, _, _, _ = ledger
    body = {"name": "Rachunek akcji test", "kind": kind, "currency": "PLN"}
    first = client.post("/api/investment-accounts", json=body)
    assert first.status_code == 201
    assert client.post("/api/investment-accounts", json=body).json()["id"] == first.json()["id"]
    assert client.post("/api/investment-accounts", json=body | {"currency": "USD"}).status_code == 409
    assert client.post("/api/investment-accounts", json=body | {"owner_id": str(uuid4())}).status_code == 422
    listing = stock(client)
    assert client.post(f"/api/accounts/{first.json()['id']}/purchases", json=trade(listing)).status_code == 201
    bonds = client.post("/api/bond-accounts", json={"name": "Tylko obligacje IKE", "kind": "IKE_BONDS"}).json()
    assert client.post(f"/api/accounts/{bonds['id']}/purchases", json=trade(listing)).status_code == 422


def test_concurrent_catalogue_retry_creates_one_listing(ledger):
    client, engine, settings, _ = ledger

    def create(_):
        with TestClient(create_app(settings, engine)) as other:
            return other.post("/api/stocks", json=company()).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert sorted(results) == [200, 201]
    assert len(client.get("/api/listings?kind=STOCK").json()) == 1
