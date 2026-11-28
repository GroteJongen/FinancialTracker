from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import bond_pricing, portfolio
from app.infrastructure import bond_sources, nbp
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import BondSeriesCache, InflationRate
from app.main import create_app
from tests.test_bonds import account, payload
from tests.test_portfolio import buy


def freeze(monkeypatch, day):
    monkeypatch.setattr(portfolio, "business_today", lambda: day)
    monkeypatch.setattr(bond_pricing, "business_today", lambda: day)


def test_new_tos_value_is_in_portfolio_without_any_nbp_or_manual_mark(ledger, monkeypatch):
    client, _, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 28))
    own = account(client)
    result = client.post(f"/api/accounts/{own}/bonds", json=payload(interest_mode="CAPITALIZE"))
    assert result.status_code == 201
    assert result.json()["interest_mode"] == "CAPITALIZE"
    initial = client.get("/api/portfolio").json()
    assert initial["missing_fx"] == []
    assert initial["bond_requirements"] == []
    assert initial["totals"]["cost"] == "999.00"
    assert initial["totals"]["value"] == "1002.20"
    assert initial["totals"]["gain"] == "3.20"
    assert initial["totals"]["paid_income"] == "0.00"
    assert initial["totals"]["earned_interest"] == "2.20"
    assert initial["positions"][0]["earned_interest"] == "2.20"
    assert initial["totals"]["complete"] is True
    assert initial["positions"][0]["bond_calculation"] == "ACCRUED"
    assert client.post("/api/portfolio/fx/refresh").json()["updated"] == 0


def test_gus_and_specific_margin_complete_indexed_value_outside_transaction(ledger, monkeypatch):
    client, engine, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 11))
    own = account(client)
    result = client.post(
        f"/api/accounts/{own}/bonds",
        json=payload(
            series="COI1128",
            trade_date="2024-11-10",
            annual_rate="5",
            margin=None,
            interest_mode="PAYOUT",
        ),
    )
    assert result.status_code == 201
    initial = client.get("/api/portfolio").json()
    assert initial["totals"]["value"] is None
    assert initial["positions"][0]["bond_missing_data"] == "missing_bond_margin"
    assert initial["missing_fx"] == []
    calls = []

    def terms(series):
        assert engine.pool.checkedout() == 0
        calls.append(series)
        return bond_sources.SeriesTerms(
            series, Decimal("5"), Decimal("1.5"), bond_sources.series_url(series)
        )

    def inflation():
        assert engine.pool.checkedout() == 0
        calls.append("GUS")
        return {(2025, 9): Decimal("2.9"), (2026, 9): Decimal("4.1")}

    monkeypatch.setattr(bond_sources, "terms", terms)
    monkeypatch.setattr(bond_sources, "inflation", inflation)
    response = client.post("/api/bonds/refresh")
    assert response.json() == dict(updated=3, failed=0, remaining=0)
    final = client.get("/api/portfolio").json()
    assert final["totals"]["value"] == "1000.20"
    assert final["totals"]["paid_income"] == "94.00"
    assert final["totals"]["earned_interest"] == "94.20"
    assert final["totals"]["gain"] == "95.20"
    assert final["totals"]["complete"] is True
    assert client.post("/api/bonds/refresh").json()["updated"] == 0
    assert sorted(calls) == ["COI1128", "GUS"]
    with Session(engine) as session:
        assert session.scalar(select(BondSeriesCache)).margin == Decimal("1.5")
        assert len(session.scalars(select(InflationRate)).all()) == 2


def test_manual_bond_mark_remains_authoritative(ledger, monkeypatch):
    client, _, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 28))
    own = account(client)
    saved = client.post(f"/api/accounts/{own}/bonds", json=payload()).json()
    response = client.post(
        f"/api/accounts/{own}/bonds/{saved['id']}/valuations",
        json=dict(
            request_id=str(uuid4()),
            purchase_revision=1,
            value="1050",
            paid_interest="0",
            observed_on="2026-11-28",
        ),
    )
    assert response.status_code == 201
    result = client.get("/api/portfolio").json()
    assert result["totals"]["value"] == "1050.00"
    assert result["totals"]["earned_interest"] == "50.00"
    assert result["positions"][0]["bond_calculation"] == "MANUAL"


def test_adding_a_pln_bond_does_not_invalidate_existing_eur_fx(ledger, monkeypatch):
    client, _, _, investment = ledger
    freeze(monkeypatch, date(2026, 11, 28))
    buy(client, investment, IUSQ_LISTING_ID, "EUR", "10", "100")
    monkeypatch.setattr(
        nbp,
        "lookup",
        lambda currency, day: nbp.FxQuote(currency, day, day, Decimal("4"), "SYNTHETIC"),
    )
    assert client.post("/api/portfolio/fx/refresh").json()["failed"] == 0
    own = account(client)
    assert client.post(f"/api/accounts/{own}/bonds", json=payload()).status_code == 201
    result = client.get("/api/portfolio").json()
    assert result["missing_fx"] == []
    assert result["totals"]["value"] == "5002.20"
    assert result["totals"]["complete"] is True


def test_source_failure_never_fills_unknown_interest_with_zero(ledger, monkeypatch):
    client, _, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 28))
    own = account(client)
    assert (
        client.post(f"/api/accounts/{own}/bonds", json=payload(annual_rate=None)).status_code == 201
    )

    def unavailable(*args):
        raise bond_sources.SourceUnavailable("offline")

    monkeypatch.setattr(bond_sources, "terms", unavailable)
    assert client.post("/api/bonds/refresh").json()["failed"] == 1
    result = client.get("/api/portfolio").json()
    assert result["totals"]["value"] is None
    assert result["totals"]["earned_interest"] is None
    assert result["positions"][0]["bond_nominal_value"] == "1000.00"


def test_foreign_portfolio_cannot_trigger_provider_reads(ledger, monkeypatch):
    client, engine, settings, own = ledger
    group = client.post(
        "/api/portfolios", json=dict(name="Private bonds", account_ids=[str(own)])
    ).json()
    with TestClient(
        create_app(settings.model_copy(update={"local_owner_id": uuid4()}), engine)
    ) as other:
        assert other.post(f"/api/bonds/refresh?portfolio_id={group['id']}").status_code == 404


def test_purchase_history_cost_is_exact_and_includes_commission(ledger):
    client, _, _, account_id = ledger
    result = client.post(
        f"/api/accounts/{account_id}/purchases",
        json=dict(
            request_id=str(uuid4()),
            listing_id=str(IUSQ_LISTING_ID),
            trade_date="2026-11-10",
            quantity="0.125",
            unit_price="100.12345678",
            commission="0.10",
            currency="EUR",
        ),
    )
    assert result.status_code == 201
    assert result.json()["cost"] == "12.62"
    assert client.get(f"/api/accounts/{account_id}/purchases").json()[0]["cost"] == "12.62"


def test_interest_mode_validation_and_legacy_retry_keep_existing_purchase(ledger):
    client, _, _, _ = ledger
    own = account(client)
    original = payload()
    saved = client.post(f"/api/accounts/{own}/bonds", json=original)
    assert saved.status_code == 201
    retried = client.post(
        f"/api/accounts/{own}/bonds", json=original | {"interest_mode": "CAPITALIZE"}
    )
    assert retried.status_code == 200
    assert retried.json()["id"] == saved.json()["id"]
    for series, wrong in (("TOS1129", "PAYOUT"), ("COI1130", "CAPITALIZE"), ("EDO1136", "PAYOUT")):
        rejected = client.post(
            f"/api/accounts/{own}/bonds", json=payload(series=series, interest_mode=wrong)
        )
        assert rejected.status_code == 422
    assert len(client.get(f"/api/accounts/{own}/bonds").json()) == 1


@pytest.mark.parametrize("series", ["TOS1129", "COI1130", "EDO1136"])
def test_each_bond_type_earns_interest_before_first_payout(ledger, monkeypatch, series):
    client, _, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 28))
    own = account(client)
    result = client.post(f"/api/accounts/{own}/bonds", json=payload(series=series))
    assert result.status_code == 201
    totals = client.get("/api/portfolio").json()["totals"]
    assert totals["paid_income"] == "0.00"
    assert totals["earned_interest"] == "2.20"
    assert totals["gain"] == "3.20"


def test_earned_interest_follows_group_and_retirement_filters(ledger, monkeypatch):
    client, engine, _, _ = ledger
    freeze(monkeypatch, date(2026, 11, 11))
    with Session(engine) as session, session.begin():
        for year, rate in ((2025, "2.9"), (2026, "4.1")):
            session.add(
                InflationRate(
                    year=year, month=9, rate=Decimal(rate), source_url="https://stat.gov.pl"
                )
            )
    accounts = []
    values = [
        ("STANDARD", "TOS1129", "2026-11-10", "4.4", None),
        ("IKE_BONDS", "COI1128", "2024-11-10", "5", "1.5"),
        ("IKZE", "EDO1134", "2024-11-10", "6", "2"),
    ]
    for kind, series, day, rate, margin in values:
        own = account(client, name=kind, kind=kind)
        accounts.append(own)
        result = client.post(
            f"/api/accounts/{own}/bonds",
            json=payload(series=series, trade_date=day, annual_rate=rate, margin=margin),
        )
        assert result.status_code == 201
    for scope, expected in (
        ("ALL", "206.40"),
        ("STANDARD", "0.10"),
        ("IKE", "94.20"),
        ("IKZE", "112.10"),
        ("RETIREMENT", "206.30"),
    ):
        result = client.get(f"/api/portfolio?scope={scope}").json()
        assert result["totals"]["earned_interest"] == expected
    group = client.post(
        "/api/portfolios", json=dict(name="TOS and COI", account_ids=accounts[:2])
    ).json()
    result = client.get(f"/api/portfolio?portfolio_id={group['id']}").json()
    assert result["totals"]["earned_interest"] == "94.30"
    assert result["totals"]["gain"] == "96.30"
