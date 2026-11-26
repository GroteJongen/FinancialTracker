from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application import bonds as service
from app.domain.purchases import business_today
from app.infrastructure.models import BondAuditEvent, BondIssue, BondPurchase
from app.main import create_app


def account(client, **changes):
    result = client.post(
        "/api/bond-accounts", json={"name": "Obligacje syntetyczne", "kind": "STANDARD"} | changes
    )
    assert result.status_code in (200, 201), result.text
    return result.json()["id"]


def payload(**changes):
    return {
        "request_id": str(uuid4()),
        "series": "TOS1129",
        "trade_date": "2026-11-10",
        "quantity": 10,
        "unit_price": "99.90",
        "annual_rate": "4.40",
        "margin": None,
        "source_url": "https://www.obligacjeskarbowe.pl/synthetic-document",
    } | changes


def correction(data, **changes):
    return {key: value for key, value in data.items() if key != "request_id"} | {
        "expected_revision": 1,
        "reason": "Poprawiono dane z potwierdzenia",
    } | changes


@pytest.mark.parametrize("kind", ["STANDARD", "IKE_BONDS", "IKZE"])
def test_account_types_and_retry(ledger, kind):
    client, _, _, _ = ledger
    values = {"name": "  Obligacje  ", "kind": kind}
    first = client.post("/api/bond-accounts", json=values)
    assert first.status_code == 201
    assert first.json()["currency"] == "PLN"
    again = client.post("/api/bond-accounts", json=values)
    assert again.status_code == 200
    assert again.json() == first.json()
    assert client.post("/api/bond-accounts", json=values | {"name": " "}).status_code == 422
    assert client.post("/api/bond-accounts", json=values | {"owner_id": str(uuid4())}).status_code == 422


@pytest.mark.parametrize(("series", "years", "margin"), [("TOS1129", 3, None), ("COI1130", 4, "1.5"), ("EDO1136", 10, "2")])
def test_purchase_cost_correction_immutable_terms_and_reopen(ledger, series, years, margin):
    client, engine, settings, _ = ledger
    account_id = account(client)
    path = f"/api/accounts/{account_id}/bonds"
    data = payload(series=series, margin=margin)
    created = client.post(path, json=data)
    assert created.status_code == 201, created.text
    first = created.json()
    assert first["cost"] == "999.00"
    assert first["term_years"] == years
    assert first["terms_status"] == "MANUAL_UNVERIFIED"
    assert first["currency"] == "PLN"
    assert "gain" not in first and "accrued_interest" not in first
    changed = client.put(path + "/" + first["id"], json=correction(data, annual_rate="4.5", quantity=11))
    assert changed.status_code == 200, changed.text
    assert changed.json()["issue_id"] != first["issue_id"]
    assert changed.json()["cost"] == "1098.90"
    history = client.get(path + "/" + first["id"] + "/audit").json()
    assert [item["kind"] for item in history] == ["CREATE", "CORRECT"]
    assert history[1]["before"] == history[0]["after"]
    assert history[1]["after"]["quantity"] == "11"
    assert history[1]["reason"] == "Poprawiono dane z potwierdzenia"
    with Session(engine) as session:
        assert session.get(BondIssue, first["issue_id"]).annual_rate == Decimal("4.40")
    with TestClient(create_app(settings, engine)) as reopened:
        assert reopened.get(path).json()[0]["revision"] == 2
    assert client.put(path + "/" + first["id"], json=correction(data)).status_code == 409
    assert client.put(path + "/" + first["id"], json=correction(data, reason=" ")).status_code == 422


def test_retry_after_correction_and_conflicting_payload(ledger):
    client, _, _, _ = ledger
    path = f"/api/accounts/{account(client)}/bonds"
    data = payload()
    first = client.post(path, json=data).json()
    again = client.post(path, json=data | {"unit_price": "99.9", "annual_rate": "4.400"})
    assert again.status_code == 200
    assert again.json()["id"] == first["id"]
    client.put(path + "/" + first["id"], json=correction(data, quantity=12))
    assert client.post(path, json=data).json()["revision"] == 2
    assert client.post(path, json=data | {"quantity": 2}).status_code == 409
    assert len(client.get(path).json()) == 1


@pytest.mark.parametrize(("field", "value"), [
    ("quantity", 0), ("quantity", -1), ("quantity", 1.5), ("quantity", True), ("quantity", "10"),
    ("quantity", 1000000000), ("unit_price", "0"), ("unit_price", "99.999"),
    ("unit_price", 100), ("unit_price", "NaN"), ("unit_price", "1e2"),
    ("annual_rate", "101"), ("annual_rate", "-1"), ("annual_rate", "0.123456789"),
    ("series", "TOS1329"), ("series", "ABC1129"), ("source_url", "javascript:alert(1)"),
    ("margin", "2"), ("trade_date", "2026-02-30"), ("owner_id", str(uuid4())),
])
def test_invalid_input_never_writes(ledger, field, value):
    client, _, _, _ = ledger
    path = f"/api/accounts/{account(client)}/bonds"
    assert client.post(path, json=payload(**{field: value})).status_code == 422
    assert client.get(path).json() == []


def test_future_date_and_missing_optional_terms(ledger):
    client, _, _, _ = ledger
    path = f"/api/accounts/{account(client)}/bonds"
    future = (business_today() + timedelta(days=1)).isoformat()
    assert client.post(path, json=payload(trade_date=future)).status_code == 422
    data = payload(series=" edo1136 ", annual_rate=None, source_url=None)
    created = client.post(path, json=data)
    assert created.status_code == 201
    assert created.json()["series"] == "EDO1136"
    assert created.json()["annual_rate"] is None


def test_account_and_owner_isolation(ledger):
    client, engine, settings, euro_account = ledger
    account_id = account(client)
    other_account = account(client, name="Drugi rachunek", kind="IKZE")
    path = f"/api/accounts/{account_id}/bonds"
    data = payload()
    purchase_id = client.post(path, json=data).json()["id"]
    assert client.get(f"/api/accounts/{other_account}/bonds").json() == []
    assert client.get(f"/api/accounts/{other_account}/bonds/{purchase_id}/audit").status_code == 404
    assert client.post(f"/api/accounts/{euro_account}/bonds", json=data).status_code == 422
    stranger_settings = settings.model_copy(update={"local_owner_id": uuid4()})
    with TestClient(create_app(stranger_settings, engine)) as stranger:
        assert stranger.get(path).status_code == 404
        assert stranger.post(path, json=data).status_code == 404
        assert stranger.put(path + "/" + purchase_id, json=correction(data)).status_code == 404
        assert stranger.get(path + "/" + purchase_id + "/audit").status_code == 404


def test_concurrent_retry_and_correction(ledger):
    client, engine, settings, _ = ledger
    account_id = account(client)
    path = f"/api/accounts/{account_id}/bonds"
    data = payload()

    def post(_):
        with TestClient(create_app(settings, engine)) as other:
            return other.post(path, json=data)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(post, range(2)))
    assert sorted(item.status_code for item in results) == [200, 201]
    first = results[0].json()

    def put(quantity):
        with TestClient(create_app(settings, engine)) as other:
            return other.put(path + "/" + first["id"], json=correction(data, quantity=quantity))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(put, [11, 12]))
    assert sorted(item.status_code for item in results) == [200, 409]
    assert len(client.get(path).json()) == 1


def test_audit_failure_rolls_back_purchase_and_issue(ledger, monkeypatch):
    client, engine, settings, _ = ledger
    path = f"/api/accounts/{account(client)}/bonds"

    def fail(*args, **kwargs):
        raise SQLAlchemyError("synthetic audit failure")

    monkeypatch.setattr(service, "audit", fail)
    assert client.post(path, json=payload()).status_code == 503
    assert client.get(path).json() == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(BondIssue).where(BondIssue.owner_id == settings.local_owner_id)) == 0
        assert session.scalar(select(func.count()).select_from(BondAuditEvent).where(BondAuditEvent.owner_id == settings.local_owner_id)) == 0
        assert session.scalar(select(func.count()).select_from(BondPurchase).where(BondPurchase.account_id == path.split('/')[3])) == 0
