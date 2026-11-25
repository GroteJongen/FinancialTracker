from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from app.application import purchases as service
from app.domain.purchases import business_today
from app.infrastructure.catalog import IUSQ_INSTRUMENT_ID, IUSQ_LISTING_ID
from app.infrastructure.models import (
    Account,
    Instrument,
    Listing,
    Owner,
)
from app.main import create_app


def payload(**changes):
    values = {
        "listing_id": str(IUSQ_LISTING_ID),
        "request_id": str(uuid4()),
        "trade_date": "2026-01-10",
        "quantity": "0.125",
        "unit_price": "100.12345678",
        "commission": "0.10",
        "currency": "EUR",
    }
    return values | changes


def correction(data, **changes):
    return (
        {key: value for key, value in data.items() if key != "request_id"}
        | {
            "expected_revision": 1,
            "reason": "Poprawiono liczbę jednostek",
        }
        | changes
    )


def url(account_id):
    return f"/api/accounts/{account_id}/purchases"


def test_fractional_purchase_correction_audit_and_reopen(ledger):
    client, engine, settings, account_id = ledger
    data = payload()
    created = client.post(url(account_id), json=data)
    assert created.status_code == 201
    first = created.json()
    assert first["quantity"] == "0.12500000"
    assert first["unit_price"] == "100.12345678"
    assert first["commission"] == "0.10000000"
    assert first["revision"] == 1
    path = url(account_id) + "/" + first["id"]
    changed = client.put(path, json=correction(data, quantity="0.25", commission="0"))
    assert changed.status_code == 200
    assert changed.json()["revision"] == 2
    assert changed.json()["quantity"] == "0.25000000"
    events = client.get(path + "/audit").json()
    assert [event["kind"] for event in events] == ["CREATE", "CORRECT"]
    assert events[0]["before"] is None
    assert events[0]["after"]["quantity"] == "0.12500000"
    assert events[1]["before"] == events[0]["after"]
    assert events[1]["after"]["quantity"] == "0.25000000"
    assert events[1]["reason"] == "Poprawiono liczbę jednostek"
    assert events[1]["created_at"].endswith(("Z", "+00:00"))
    with TestClient(create_app(settings, engine)) as reopened:
        assert reopened.get(url(account_id)).json()[0]["revision"] == 2


def test_many_purchases_and_order(ledger):
    client, _, _, account_id = ledger
    for day in ("2026-01-01", "2026-01-20", "2026-01-05"):
        assert client.post(url(account_id), json=payload(trade_date=day)).status_code == 201
    assert [item["trade_date"] for item in client.get(url(account_id)).json()] == [
        "2026-01-20",
        "2026-01-05",
        "2026-01-01",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"),
        ("quantity", "-1"),
        ("quantity", "NaN"),
        ("quantity", "Infinity"),
        ("quantity", "1e2"),
        ("quantity", "0.123456789"),
        ("quantity", "10000000000"),
        ("quantity", 0.125),
        ("quantity", True),
        ("quantity", None),
        ("quantity", "0,125"),
        ("unit_price", "0"),
        ("unit_price", "-2"),
        ("unit_price", "9.123456789"),
        ("commission", "-0.01"),
        ("commission", "0.000000001"),
        ("currency", "USD"),
        ("trade_date", "2026-02-30"),
        ("trade_date", "2026-1-1"),
        ("trade_date", 123),
    ],
)
def test_invalid_data_is_rejected_without_writes(ledger, field, value):
    client, _, _, account_id = ledger
    result = client.post(url(account_id), json=payload(**{field: value}))
    assert result.status_code == 422
    assert result.json()["detail"] == "Sprawdź dane formularza."
    assert client.get(url(account_id)).json() == []


def test_future_unknown_listing_and_extra_owner_are_rejected(ledger):
    client, _, _, account_id = ledger
    tomorrow = (business_today() + timedelta(days=1)).isoformat()
    assert client.post(url(account_id), json=payload(trade_date=tomorrow)).status_code == 422
    assert client.post(url(account_id), json=payload(listing_id=str(uuid4()))).status_code == 422
    assert client.post(url(account_id), json=payload(owner_id=str(uuid4()))).status_code == 422
    assert client.get(url(account_id)).json() == []


def test_smallest_and_largest_exact_amounts(ledger):
    client, _, _, account_id = ledger
    result = client.post(
        url(account_id),
        json=payload(
            quantity="0.00000001",
            unit_price="9999999999.99999999",
            commission="0",
        ),
    )
    assert result.status_code == 201
    assert result.json()["quantity"] == "0.00000001"
    assert result.json()["unit_price"] == "9999999999.99999999"


def test_idempotent_retry_and_different_payload_conflict(ledger):
    client, _, _, account_id = ledger
    data = payload()
    first = client.post(url(account_id), json=data)
    second = client.post(url(account_id), json=data | {"quantity": "0.12500000"})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert client.post(url(account_id), json=data | {"quantity": "1"}).status_code == 409
    assert len(client.get(url(account_id)).json()) == 1
    path = url(account_id) + "/" + first.json()["id"]
    assert len(client.get(path + "/audit").json()) == 1


def test_stale_revision_and_missing_reason_do_not_change_audit(ledger):
    client, _, _, account_id = ledger
    data = payload()
    purchase = client.post(url(account_id), json=data).json()
    path = url(account_id) + "/" + purchase["id"]
    assert client.put(path, json=correction(data, reason="   ")).status_code == 422
    assert client.put(path, json=correction(data, quantity="2")).status_code == 200
    assert client.put(path, json=correction(data, quantity="3")).status_code == 409
    assert client.get(url(account_id)).json()[0]["quantity"] == "2.00000000"
    assert len(client.get(path + "/audit").json()) == 2


def test_foreign_account_and_purchase_access_is_denied(ledger):
    client, _, _, account_id = ledger
    data = payload()
    purchase = client.post(url(account_id), json=data).json()
    foreign_id = uuid4()
    foreign_path = url(foreign_id)
    assert client.get(foreign_path).status_code == 404
    assert client.post(foreign_path, json=payload()).status_code == 404
    assert client.put(foreign_path + "/" + purchase["id"], json=correction(data)).status_code == 404
    assert client.get(foreign_path + "/" + purchase["id"] + "/audit").status_code == 404
    assert (
        client.get(url(account_id) + "?owner_id=" + str(uuid4())).json()[0]["id"]
        == (purchase["id"])
    )
    assert client.get(url(account_id) + "/" + str(uuid4()) + "/audit").status_code == 404


def test_actual_other_owner_cannot_read_or_correct_purchase(ledger):
    client, engine, settings, account_id = ledger
    data = payload()
    purchase = client.post(url(account_id), json=data).json()
    other_settings = settings.model_copy(update={"local_owner_id": uuid4()})
    with TestClient(create_app(other_settings, engine)) as stranger:
        assert stranger.get(url(account_id)).status_code == 404
        assert stranger.post(url(account_id), json=payload()).status_code == 404
        path = url(account_id) + "/" + purchase["id"]
        assert stranger.put(path, json=correction(data)).status_code == 404
        assert stranger.get(path + "/audit").status_code == 404


def test_audit_failure_rolls_back_purchase(ledger, monkeypatch):
    client, _, _, account_id = ledger

    def fail(*args, **kwargs):
        raise SQLAlchemyError("synthetic failure")

    monkeypatch.setattr(service, "add_audit_event", fail)
    assert client.post(url(account_id), json=payload()).status_code == 503
    assert client.get(url(account_id)).json() == []


def test_audit_failure_rolls_back_correction(ledger, monkeypatch):
    client, _, _, account_id = ledger
    data = payload()
    purchase = client.post(url(account_id), json=data).json()

    def fail(*args, **kwargs):
        raise SQLAlchemyError("synthetic failure")

    monkeypatch.setattr(service, "add_audit_event", fail)
    path = url(account_id) + "/" + purchase["id"]
    assert client.put(path, json=correction(data, quantity="2")).status_code == 503
    assert client.get(url(account_id)).json()[0]["revision"] == 1
    assert len(client.get(path + "/audit").json()) == 1


def test_concurrent_corrections_have_one_winner(ledger):
    client, engine, settings, account_id = ledger
    data = payload()
    purchase = client.post(url(account_id), json=data).json()
    path = url(account_id) + "/" + purchase["id"]

    def edit(quantity):
        with TestClient(create_app(settings, engine)) as concurrent:
            return concurrent.put(path, json=correction(data, quantity=quantity)).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["2", "3"]))
    assert sorted(results) == [200, 409]
    assert len(client.get(path + "/audit").json()) == 2


def test_concurrent_creation_retry_does_not_duplicate(ledger):
    client, engine, settings, account_id = ledger
    data = payload()

    def create(_):
        with TestClient(create_app(settings, engine)) as concurrent:
            return concurrent.post(url(account_id), json=data).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert sorted(results) == [200, 201]
    assert len(client.get(url(account_id)).json()) == 1


def test_catalog_is_unique_and_seed_contains_no_purchases(ledger):
    client, engine, _, _ = ledger
    listing = client.get("/api/listings").json()
    assert len(listing) == 1
    assert listing[0]["id"] == str(IUSQ_LISTING_ID)
    assert listing[0]["currency"] == "EUR"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Instrument)) == 1
        assert session.scalar(select(func.count()).select_from(Listing)) == 1


def test_upgrade_preserves_existing_accounts_and_can_be_reversed(test_database):
    engine, _, original_config = test_database
    schema = "migration_probe_" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(CreateSchema(schema))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            config = Config(original_config.config_file_name)
            config.attributes["connection"] = connection
            config.attributes["version_table_schema"] = schema
            command.upgrade(config, "0001")
            owner_id, account_id = uuid4(), uuid4()
            connection.execute(insert(Owner).values(id=owner_id, name="Istniejący właściciel"))
            connection.execute(
                insert(Account).values(
                    id=account_id,
                    owner_id=owner_id,
                    name="Istniejące IKE",
                    kind="IKE",
                    currency="EUR",
                )
            )
            command.upgrade(config, "head")
            assert connection.scalar(select(Account.name).where(Account.id == account_id)) == (
                "Istniejące IKE"
            )
            assert (
                connection.scalar(
                    select(Instrument.isin).where(Instrument.id == IUSQ_INSTRUMENT_ID)
                )
                == "IE00B6R52259"
            )
            command.downgrade(config, "0001")
            assert connection.scalar(select(Account.name).where(Account.id == account_id)) == (
                "Istniejące IKE"
            )
            command.upgrade(config, "head")
        finally:
            transaction.rollback()
