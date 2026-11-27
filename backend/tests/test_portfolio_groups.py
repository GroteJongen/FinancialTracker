from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.main import create_app
from tests.test_portfolio import account, buy


def test_groups_scope_overlap_retry_revision_and_privacy(ledger):
    client, engine, settings, _ = ledger
    standard = account(client, "Standard portfolio", "STANDARD")
    ike = account(client, "IKE portfolio", "IKE")
    security = client.post(
        "/api/securities",
        json=dict(
            kind="ETF", name="Synthetic diversified ETF", symbol="FUND", mic="XETR", currency="PLN"
        ),
    ).json()
    buy(client, standard, security["id"], "PLN", "10", "100")
    buy(client, ike, security["id"], "PLN", "2", "100")
    body = dict(name="Long term", account_ids=[standard, ike])
    created = client.post("/api/portfolios", json=body)
    assert created.status_code == 201
    group = created.json()
    assert client.post("/api/portfolios", json=body).status_code == 200
    assert client.post("/api/portfolios", json=body | {"account_ids": []}).status_code == 409
    second = client.post(
        "/api/portfolios", json=dict(name="Overlapping", account_ids=[standard])
    ).json()
    result = client.get("/api/portfolio", params={"portfolio_id": group["id"]}).json()
    assert result["totals"]["value"] == "1200.00"
    assert result["positions"][0]["label"] == "Synthetic diversified ETF"
    assert result["positions"][0]["gain_percent"] == "0.00"
    assert (
        client.get("/api/portfolio", params={"portfolio_id": group["id"], "scope": "IKE"}).json()[
            "totals"
        ]["value"]
        == "200.00"
    )
    assert client.get("/api/portfolio").json()["totals"]["value"] == "1200.00"
    assert (
        client.get("/api/portfolio", params={"portfolio_id": second["id"]}).json()["totals"][
            "value"
        ]
        == "1000.00"
    )
    updated = body | dict(expected_revision=1, account_ids=[ike])
    assert client.put(f"/api/portfolios/{group['id']}", json=updated).status_code == 200
    assert client.put(f"/api/portfolios/{group['id']}", json=updated).status_code == 409
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert other.get("/api/portfolios").json() == []
        assert other.get("/api/portfolio", params={"portfolio_id": group["id"]}).status_code == 404
        assert (
            other.post(
                "/api/portfolio/fx/refresh", params={"portfolio_id": group["id"]}
            ).status_code
            == 404
        )
        assert other.put(f"/api/portfolios/{group['id']}", json=updated).status_code == 404
        assert other.post("/api/portfolios", json=body).status_code == 404


@pytest.mark.parametrize("kind", ["ETF", "REIT"])
def test_private_securities_multiple_etfs_and_reit_allocation(ledger, kind):
    client, engine, settings, account_id = ledger
    payload = dict(kind=kind, name="Synthetic " + kind, symbol="SYN", mic="XNYS", currency="USD")
    result = client.post("/api/securities", json=payload)
    assert result.status_code == 201
    listing = result.json()
    assert listing["kind"] == kind
    assert client.post("/api/securities", json=payload).status_code == 200
    buy(client, account_id, listing["id"], "USD", "1.25", "100")
    position = client.get("/api/portfolio").json()["positions"][0]
    assert Decimal(position["quantity"]) == Decimal("1.25")
    assert position["native_value"] == "125.00"
    assert position["value_pln"] is None  # Missing FX is never zero.
    assert (
        client.get(f"/api/accounts/{account_id}/valuation?listing_id={listing['id']}").status_code
        == 200
    )
    assert any(
        row["id"] == listing["id"] for row in client.get(f"/api/listings?kind={kind}").json()
    )
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert all(row["id"] != listing["id"] for row in other.get("/api/listings?kind=ALL").json())
        assert (
            other.put(f"/api/listings/{listing['id']}/yahoo", json=dict(symbol="SYN")).status_code
            == 404
        )
    public = client.get("/api/listings?kind=ALL").json()
    assert any(row["id"] == str(IUSQ_LISTING_ID) for row in public)


def test_empty_group_and_duplicate_memberships(ledger):
    client, _, _, account_id = ledger
    assert (
        client.post(
            "/api/portfolios",
            json=dict(name="Duplicate", account_ids=[str(account_id), str(account_id)]),
        ).status_code
        == 422
    )
    group = client.post("/api/portfolios", json=dict(name="Empty", account_ids=[])).json()
    result = client.get("/api/portfolio", params={"portfolio_id": group["id"]}).json()
    assert result["position_count"] == 0
    assert result["totals"]["value"] == "0.00"
