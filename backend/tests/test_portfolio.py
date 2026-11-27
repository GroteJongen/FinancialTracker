from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.purchases import business_today
from app.application import portfolio as portfolio_service
from app.application import purchases as purchase_service
from app.infrastructure import nbp
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import BondValuation, FxRate
from app.main import create_app


def account(client, name, kind):
    path = "/api/bond-accounts" if kind == "IKE_BONDS" else "/api/investment-accounts"
    body = dict(name=name, kind=kind)
    if kind != "IKE_BONDS":
        body["currency"] = "PLN"
    result = client.post(path, json=body)
    assert result.status_code == 201, result.text
    return result.json()["id"]


def buy(client, account_id, listing_id, currency, quantity, price):
    body = dict(request_id=str(uuid4()), listing_id=str(listing_id), currency=currency, quantity=quantity, unit_price=price, commission="0", trade_date="2026-11-10")
    result = client.post(f"/api/accounts/{account_id}/purchases", json=body)
    assert result.status_code == 201, result.text
    result = client.post(f"/api/accounts/{account_id}/prices", json=dict(request_id=str(uuid4()), listing_id=str(listing_id), currency=currency, price=price, observed_on="2026-11-20"))
    assert result.status_code == 201


def bond(client, account_id):
    body = dict(request_id=str(uuid4()), series="TOS1129", trade_date="2026-11-10", quantity=1000, unit_price="100")
    result = client.post(f"/api/accounts/{account_id}/bonds", json=body)
    assert result.status_code == 201
    return result.json(), body


def mark(client, account_id, purchase, **changes):
    values = dict(request_id=str(uuid4()), purchase_revision=purchase["revision"], value="110000", paid_interest="0", observed_on="2026-11-20") | changes
    path = f"/api/accounts/{account_id}/bonds/{purchase['id']}/valuations"
    return client.post(path, json=values), values, path


@pytest.fixture
def portfolio_data(ledger):
    client, engine, settings, _ = ledger
    standard = account(client, "Obligacje zwykłe", "STANDARD")
    ike = account(client, "ETF IKE", "IKE")
    ikze = account(client, "Akcje IKZE", "IKZE")
    purchase, original = bond(client, standard)
    assert mark(client, standard, purchase)[0].status_code == 201
    buy(client, ike, IUSQ_LISTING_ID, "EUR", "100", "100")
    listing = client.post("/api/stocks", json=dict(name="Syntetyczna spółka portfela", symbol="PORT", mic="XWAR", currency="PLN")).json()
    buy(client, ikze, listing["id"], "PLN", "10", "2500")
    with Session(engine) as session, session.begin():
        for day in {date(2026, 11, 10), business_today()}:
            session.add(FxRate(currency="EUR", requested_on=day, effective_on=day, rate=Decimal("5"), table_number="SYNTHETIC/TEST"))
    return client, engine, settings, standard, ike, ikze, purchase, original


def test_user_example_filters_and_privacy(portfolio_data):
    client, engine, settings, _, _, _, _, _ = portfolio_data
    result = client.get("/api/portfolio").json()
    assert result["totals"]["cost"] == "175000.00"
    assert result["totals"]["value"] == "185000.00"
    assert result["totals"]["gain"] == "10000.00"
    assert result["totals"]["gain_percent"] == "5.71"
    assert result["totals"]["complete"] is True
    assert result["position_count"] == 3
    for scope, expected in [("STANDARD", "110000.00"), ("IKE", "50000.00"), ("IKZE", "25000.00"), ("RETIREMENT", "75000.00")]:
        filtered = client.get("/api/portfolio", params={"scope": scope}).json()
        assert filtered["totals"]["value"] == expected
    stranger = settings.model_copy(update={"local_owner_id": uuid4()})
    with TestClient(create_app(stranger, engine)) as other:
        data = other.get("/api/portfolio").json()
        assert data["positions"] == [] and data["fx_rates"] == []
        assert data["totals"]["value"] == "0.00"
    assert client.get("/api/portfolio?scope=PRIVATE").status_code == 422


def test_ike_includes_ike_bonds(ledger):
    client, _, _, _ = ledger
    account_id = account(client, "IKE Obligacje", "IKE_BONDS")
    purchase, _ = bond(client, account_id)
    mark(client, account_id, purchase)
    assert client.get("/api/portfolio?scope=IKE").json()["totals"]["value"] == "110000.00"
    assert client.get("/api/portfolio?scope=STANDARD").json()["positions"] == []


def test_paid_interest_retry_revisions_and_append_only(portfolio_data):
    client, engine, _, account_id, _, _, purchase, original = portfolio_data
    saved, body, path = mark(client, account_id, purchase, value="100000", paid_interest="10000")
    assert saved.status_code == 201
    assert client.post(path, json=body).status_code == 200
    result = client.get("/api/portfolio").json()["totals"]
    assert result["value"] == "175000.00" and result["gain"] == "10000.00"
    assert result["paid_income"] == "10000.00"
    assert client.post(path, json=body | {"paid_interest": "20000"}).status_code == 409
    correction = {key: value for key, value in original.items() if key != "request_id"} | dict(expected_revision=1, reason="Korekta partii", quantity=999)
    assert client.put(f"/api/accounts/{account_id}/bonds/{purchase['id']}", json=correction).status_code == 200
    result = client.get("/api/portfolio").json()
    assert result["totals"]["value"] is None and result["totals"]["gain"] is None
    assert result["totals"]["allocation_value"] == []
    assert result["totals"]["allocation_cost"]
    assert client.post(path, json=body | {"request_id": str(uuid4())}).status_code == 409
    with Session(engine) as session:
        assert len(list(session.scalars(select(BondValuation).where(BondValuation.purchase_id == purchase["id"])))) == 2


@pytest.mark.parametrize(("field", "value"), [("value", "-1"), ("value", "0.001"), ("paid_interest", 100), ("value", "NaN"), ("owner_id", str(uuid4())), ("purchase_revision", True), ("observed_on", "2026-01-01")])
def test_invalid_bond_marks_do_not_write(ledger, field, value):
    client, _, _, _ = ledger
    account_id = account(client, "Obligacje", "STANDARD")
    purchase, _ = bond(client, account_id)
    result, _, _ = mark(client, account_id, purchase, **{field: value})
    assert result.status_code == 422
    assert client.get("/api/portfolio").json()["totals"]["value"] is None


def test_foreign_bond_mark_is_rejected(ledger):
    client, engine, settings, _ = ledger
    account_id = account(client, "Obligacje", "STANDARD")
    purchase, _ = bond(client, account_id)
    with TestClient(create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)) as other:
        assert mark(other, account_id, purchase)[0].status_code == 404


def test_fx_historical_cost_and_outage_cache(ledger, monkeypatch):
    client, _, _, account_id = ledger
    buy(client, account_id, IUSQ_LISTING_ID, "EUR", "10", "100")
    assert client.get("/api/portfolio").json()["totals"]["value"] is None

    def lookup(currency, day):
        return nbp.FxQuote(currency, day, day - timedelta(days=1), Decimal("5") if day == business_today() else Decimal("4"), "SYNTHETIC/TEST")

    monkeypatch.setattr(nbp, "lookup", lookup)
    result = client.post("/api/portfolio/fx/refresh")
    assert result.status_code == 200 and result.json()["remaining"] == 0
    data = client.get("/api/portfolio").json()
    assert data["totals"]["cost"] == "4000.00"
    assert data["totals"]["value"] == "5000.00"
    assert data["totals"]["gain"] == "1000.00"
    assert data["estimated_fx"] is True

    def unavailable(*args):
        raise nbp.FxUnavailable("synthetic outage")

    monkeypatch.setattr(nbp, "lookup", unavailable)
    assert client.post("/api/portfolio/fx/refresh").json()["failed"] == 1
    assert client.get("/api/portfolio").json()["totals"]["value"] == "5000.00"


def test_empty_scope_never_fetches_external_data(ledger, monkeypatch):
    client, _, _, _ = ledger

    def unexpected(*args):
        raise AssertionError("No currencies require an HTTP request")

    monkeypatch.setattr(nbp, "lookup", unexpected)
    assert client.post("/api/portfolio/fx/refresh").json() == dict(updated=0, failed=0, remaining=0)
    assert client.get("/api/portfolio").json()["totals"]["complete"] is True


def test_portfolio_read_and_purchase_audit_do_not_deadlock(ledger, monkeypatch):
    _, engine, settings, account_id = ledger
    account_locked, owner_locked = Event(), Event()
    original_account = purchase_service.owned_account
    original_owner = portfolio_service.lock_owner

    def lock_account(*args, **kwargs):
        result = original_account(*args, **kwargs)
        account_locked.set()
        assert owner_locked.wait(3)
        return result

    def lock_portfolio_owner(*args, **kwargs):
        result = original_owner(*args, **kwargs)
        owner_locked.set()
        return result

    monkeypatch.setattr(purchase_service, "owned_account", lock_account)
    monkeypatch.setattr(portfolio_service, "lock_owner", lock_portfolio_owner)

    def write():
        with TestClient(create_app(settings, engine)) as client:
            return client.post(f"/api/accounts/{account_id}/purchases", json=dict(request_id=str(uuid4()), listing_id=str(IUSQ_LISTING_ID), currency="EUR", quantity="1", unit_price="100", commission="0", trade_date="2026-11-10"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(write)
        assert account_locked.wait(3)
        with TestClient(create_app(settings, engine)) as reader:
            result = reader.get("/api/portfolio")
        assert writer.result().status_code == 201
        assert result.status_code == 200
        assert result.json()["position_count"] == 1
