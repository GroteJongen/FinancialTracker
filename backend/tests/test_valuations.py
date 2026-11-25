from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, text
from sqlalchemy.schema import CreateSchema

from app.domain.purchases import business_today
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import Account, Operation, Owner, PurchaseDetails
from app.main import create_app


def price_body(**values):
    return {
        "request_id": str(uuid4()), "listing_id": str(IUSQ_LISTING_ID),
        "price": "110", "observed_on": "2026-01-20", "currency": "EUR",
    } | values


def buy(client, account_id, **values):
    body = {
        "request_id": str(uuid4()), "listing_id": str(IUSQ_LISTING_ID),
        "quantity": "10", "unit_price": "100", "commission": "2",
        "trade_date": "2026-01-10", "currency": "EUR",
    } | values
    result = client.post(f"/api/accounts/{account_id}/purchases", json=body)
    assert result.status_code == 201
    return result.json(), body


def summary(client, account_id):
    response = client.get(f"/api/accounts/{account_id}/valuation")
    assert response.status_code == 200
    return response.json()


def test_unpriced_and_priced_example(ledger):
    client, _, _, account = ledger
    buy(client, account)
    unpriced = summary(client, account)
    assert unpriced["status"] == "unpriced"
    assert unpriced["display"]["cost"] == "1002.00"
    assert unpriced["market_value"] is None and unpriced["gain"] is None
    saved = client.post(f"/api/accounts/{account}/prices", json=price_body())
    assert saved.status_code == 201
    assert saved.json()["source"] == "MANUAL"
    result = summary(client, account)
    assert result["status"] == "priced"
    assert result["quantity"] == "10.00000000"
    assert result["display"] == {
        "cost": "1002.00", "average_cost": "100.20", "market_value": "1100.00",
        "gain": "98.00", "gain_percent": "9.78",
    }


def test_multiple_buys_and_correction_recalculate_cost(ledger):
    client, _, _, account = ledger
    purchase, data = buy(client, account)
    buy(client, account, quantity="5", unit_price="120", commission="1")
    assert client.post(f"/api/accounts/{account}/prices", json=price_body()).status_code == 201
    assert summary(client, account)["display"]["gain"] == "47.00"
    body = {key: value for key, value in data.items() if key != "request_id"}
    body |= {"quantity": "9", "expected_revision": 1, "reason": "Korekta ilości"}
    assert client.put(
        f"/api/accounts/{account}/purchases/{purchase['id']}", json=body
    ).status_code == 200
    assert summary(client, account)["display"]["gain"] == "37.00"


def test_price_before_last_purchase_is_rejected_and_same_date_allowed(ledger):
    client, _, _, account = ledger
    buy(client, account)
    assert client.post(
        f"/api/accounts/{account}/prices", json=price_body(observed_on="2026-01-09")
    ).status_code == 422
    assert summary(client, account)["history"] == []
    assert client.post(
        f"/api/accounts/{account}/prices", json=price_body(observed_on="2026-01-10")
    ).status_code == 201


def test_new_purchase_invalidates_old_quote_and_new_quote_restores_valuation(ledger):
    client, _, _, account = ledger
    buy(client, account)
    assert client.post(f"/api/accounts/{account}/prices", json=price_body()).status_code == 201
    buy(client, account, trade_date="2026-01-21")
    result = summary(client, account)
    assert result["status"] == "outdated"
    assert result["latest_trade_date"] == "2026-01-21"
    assert result["price"]["observed_on"] == "2026-01-20"
    assert result["gain"] is None and result["market_value"] is None
    assert result["display"]["cost"] == "2004.00"
    assert client.post(f"/api/accounts/{account}/prices", json=price_body(
        observed_on="2026-01-21", price="120"
    )).status_code == 201
    assert summary(client, account)["display"]["gain"] == "396.00"


def test_corrected_date_invalidates_quote(ledger):
    client, _, _, account = ledger
    purchase, data = buy(client, account)
    assert client.post(f"/api/accounts/{account}/prices", json=price_body()).status_code == 201
    body = {key: value for key, value in data.items() if key != "request_id"}
    body |= {"trade_date": "2026-01-21", "expected_revision": 1, "reason": "Data z potwierdzenia"}
    assert client.put(
        f"/api/accounts/{account}/purchases/{purchase['id']}", json=body
    ).status_code == 200
    assert summary(client, account)["status"] == "outdated"


@pytest.mark.parametrize(("field", "value"), [
    ("price", "0"), ("price", "-1"), ("price", "NaN"), ("price", "1e2"),
    ("price", 110.5), ("price", "0.123456789"), ("price", "10000000000"),
    ("currency", "USD"), ("observed_on", "2026-02-30"),
])
def test_invalid_price_does_not_write(ledger, field, value):
    client, _, _, account = ledger
    assert client.post(
        f"/api/accounts/{account}/prices", json=price_body(**{field: value})
    ).status_code == 422
    assert summary(client, account)["history"] == []


def test_future_date_is_rejected(ledger):
    client, _, _, account = ledger
    tomorrow = (business_today() + timedelta(days=1)).isoformat()
    assert client.post(
        f"/api/accounts/{account}/prices", json=price_body(observed_on=tomorrow)
    ).status_code == 422


def test_prices_are_private_and_isolated_between_accounts(ledger):
    client, engine, settings, account = ledger
    assert client.post(f"/api/accounts/{account}/prices", json=price_body()).status_code == 201
    stranger_settings = settings.model_copy(update={"local_owner_id": uuid4()})
    with TestClient(create_app(stranger_settings, engine)) as stranger:
        assert stranger.get(f"/api/accounts/{account}/valuation").status_code == 404
        assert stranger.post(
            f"/api/accounts/{account}/prices", json=price_body()
        ).status_code == 404
    other = uuid4()
    with engine.begin() as connection:
        connection.execute(insert(Account).values(
            id=other, owner_id=settings.local_owner_id, name="Drugie IKE",
            kind="IKE", currency="EUR"
        ))
    try:
        assert summary(client, other)["history"] == []
    finally:
        with engine.begin() as connection:
            connection.execute(Account.__table__.delete().where(Account.id == other))


def test_append_only_history_uses_date_then_latest_entry(ledger):
    client, _, _, account = ledger
    buy(client, account)
    for day, price in [("2026-01-20", "110"), ("2026-01-15", "105"), ("2026-01-20", "120")]:
        assert client.post(f"/api/accounts/{account}/prices", json=price_body(
            observed_on=day, price=price
        )).status_code == 201
    result = summary(client, account)
    assert [item["price"] for item in result["history"]] == [
        "120.00000000", "110.00000000", "105.00000000",
    ]
    assert result["display"]["market_value"] == "1200.00"


def test_idempotent_price_retry_and_conflict(ledger):
    client, _, _, account = ledger
    data = price_body(price="0.00000001")
    first = client.post(f"/api/accounts/{account}/prices", json=data)
    again = client.post(f"/api/accounts/{account}/prices", json=data)
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert first.json()["price"] == "0.00000001"
    assert client.post(
        f"/api/accounts/{account}/prices", json=data | {"price": "1"}
    ).status_code == 409
    assert len(summary(client, account)["history"]) == 1


def test_concurrent_retry_does_not_duplicate_price(ledger):
    client, engine, settings, account = ledger
    data = price_body()

    def save(_):
        with TestClient(create_app(settings, engine)) as concurrent:
            return concurrent.post(f"/api/accounts/{account}/prices", json=data).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(save, [1, 2]))
    assert sorted(statuses) == [200, 201]
    assert len(summary(client, account)["history"]) == 1


def test_price_survives_reopening_application(ledger):
    client, engine, settings, account = ledger
    buy(client, account)
    assert client.post(f"/api/accounts/{account}/prices", json=price_body()).status_code == 201
    with TestClient(create_app(settings, engine)) as reopened:
        assert summary(reopened, account)["display"]["gain"] == "98.00"


def test_upgrade_from_0002_preserves_purchase(test_database):
    engine, _, original_config = test_database
    schema = "valuation_probe_" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(CreateSchema(schema))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            config = Config(original_config.config_file_name)
            config.attributes["connection"] = connection
            config.attributes["version_table_schema"] = schema
            command.upgrade(config, "0002")
            owner, account, operation = uuid4(), uuid4(), uuid4()
            connection.execute(insert(Owner).values(id=owner, name="Istniejący właściciel"))
            connection.execute(insert(Account).values(
                id=account, owner_id=owner, name="IKE przed wycenami", kind="IKE", currency="EUR"
            ))
            connection.execute(insert(Operation).values(
                id=operation, account_id=account, listing_id=IUSQ_LISTING_ID, kind="PURCHASE",
                trade_date=date(2026, 1, 10), revision=1,
                request_id=uuid4(), request_hash="synthetic",
            ))
            connection.execute(insert(PurchaseDetails).values(
                operation_id=operation, quantity=Decimal("0.125"), unit_price=Decimal("100"),
                commission=Decimal("0"), currency="EUR",
            ))
            command.upgrade(config, "head")
            assert connection.scalar(select(PurchaseDetails.quantity).where(
                PurchaseDetails.operation_id == operation
            )) == Decimal("0.125")
            command.downgrade(config, "0002")
            assert connection.scalar(select(Operation.id).where(Operation.id == operation)) == (
                operation
            )
        finally:
            transaction.rollback()
