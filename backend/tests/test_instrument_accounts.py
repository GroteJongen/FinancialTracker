from uuid import uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import AccountListing
from app.main import create_app
from tests.test_portfolio import buy


def payload(account_id, kind="ETF"):
    return dict(
        account_id=str(account_id),
        kind=kind,
        name="Synthetic account instrument",
        symbol="REGISTER",
        mic="XETR",
        currency="EUR",
    )


@pytest.mark.parametrize("kind", ["STOCK", "ETF", "REIT"])
def test_registration_is_persistent_idempotent_and_private_without_fake_purchase(ledger, kind):
    client, engine, settings, account_id = ledger
    body = payload(account_id, kind)
    created = client.post("/api/securities", json=body)
    assert created.status_code == 201
    listing = created.json()
    assert listing["account_ids"] == [str(account_id)]
    assert client.post("/api/securities", json=body).status_code == 200
    second = client.post(
        "/api/investment-accounts",
        json=dict(name="Second registration account", kind="IKZE", currency="PLN"),
    ).json()["id"]
    repeated = client.post("/api/securities", json=body | dict(account_id=second))
    assert repeated.status_code == 200
    assert set(repeated.json()["account_ids"]) == {str(account_id), second}
    saved = next(
        row for row in client.get("/api/listings?kind=ALL").json() if row["id"] == listing["id"]
    )
    assert set(saved["account_ids"]) == {str(account_id), second}
    assert client.get("/api/portfolio").json()["position_count"] == 0
    with Session(engine) as session:
        assert (
            len(
                session.scalars(
                    select(AccountListing).where(AccountListing.listing_id == listing["id"])
                ).all()
            )
            == 2
        )
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert other.post("/api/securities", json=body).status_code == 404
        assert not any(
            row["id"] == listing["id"] for row in other.get("/api/listings?kind=ALL").json()
        )


def test_missing_or_invalid_account_never_creates_a_security(ledger):
    client, _, _, account_id = ledger
    before = client.get("/api/listings?kind=ALL").json()
    body = payload(account_id)
    body.pop("account_id")
    assert client.post("/api/securities", json=body).status_code == 422
    response = client.post("/api/securities", json=payload(uuid4()))
    assert response.status_code == 404
    assert "rachunek" in response.json()["detail"]
    bond_account = client.post(
        "/api/bond-accounts", json=dict(name="Synthetic IKE bonds", kind="IKE_BONDS")
    ).json()["id"]
    assert client.post("/api/securities", json=payload(bond_account)).status_code == 422
    assert client.get("/api/listings?kind=ALL").json() == before


def test_migration_from_previous_schema_preserves_existing_account_purchases(ledger, test_database):
    client, _, _, account_id = ledger
    _, _, config = test_database
    created = client.post(
        "/api/stocks",
        json=dict(name="Synthetic migration stock", symbol="MIGRATE", mic="XETR", currency="EUR"),
    ).json()
    buy(client, account_id, created["id"], "EUR", "2", "100")
    before = client.get(f"/api/accounts/{account_id}/purchases").json()
    command.downgrade(config, "0008")
    command.upgrade(config, "head")
    assert client.get(f"/api/accounts/{account_id}/purchases").json() == before
    saved = next(
        row for row in client.get("/api/listings?kind=ALL").json() if row["id"] == created["id"]
    )
    assert saved["account_ids"] == [str(account_id)]
