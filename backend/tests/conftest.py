import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings
from app.infrastructure.database import make_engine
from app.infrastructure.models import (
    Account,
    AuditEvent,
    BondAuditEvent,
    BondIssue,
    BondPurchase,
    BondValuation,
    FxRate,
    Instrument,
    Listing,
    Operation,
    Owner,
    PriceObservation,
    PurchaseDetails,
    PortfolioGroup,
    PortfolioAccount,
    YahooListing,
)
from app.main import create_app


@pytest.fixture(scope="session")
def test_database():
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.fail("TEST_DATABASE_URL musi wskazywać osobną bazę PostgreSQL z końcówką _test.")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        pytest.fail("Odmowa migracji: wymagany PostgreSQL oraz nazwa bazy z końcówką _test.")
    settings = Settings(
        _env_file=None,
        database_host=url.host,
        database_port=url.port or 5432,
        database_user=url.username,
        database_password=url.password,
        database_name=url.database,
    )
    saved = {
        key: os.environ.get(key)
        for key in (
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_NAME",
        )
    }
    os.environ.update(
        {
            "DATABASE_HOST": settings.database_host,
            "DATABASE_PORT": str(settings.database_port),
            "DATABASE_USER": settings.database_user,
            "DATABASE_PASSWORD": settings.database_password.get_secret_value(),
            "DATABASE_NAME": settings.database_name,
        }
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = make_engine(settings.database_url)
    yield engine, settings, config
    engine.dispose()
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def ledger(test_database):
    engine, settings, _ = test_database
    owner_id, account_id = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(Owner(id=owner_id, name="Właściciel zakupów — test"))
        session.flush()
        session.add(
            Account(
                id=account_id, owner_id=owner_id, name="IKE testowe", kind="IKE", currency="EUR"
            )
        )
    settings = settings.model_copy(update={"local_owner_id": owner_id})
    with TestClient(create_app(settings, engine)) as client:
        yield client, engine, settings, account_id
    with Session(engine) as session, session.begin():
        session.execute(delete(PortfolioAccount).where(PortfolioAccount.portfolio_id.in_(select(PortfolioGroup.id).where(PortfolioGroup.owner_id == owner_id))))
        session.execute(delete(PortfolioGroup).where(PortfolioGroup.owner_id == owner_id))
        account_ids = select(Account.id).where(Account.owner_id == owner_id)
        ids = select(Operation.id).where(Operation.account_id.in_(account_ids))
        bond_ids = select(BondPurchase.id).where(BondPurchase.account_id.in_(account_ids))
        session.execute(delete(BondValuation).where(BondValuation.purchase_id.in_(bond_ids)))
        session.execute(delete(FxRate))
        session.execute(delete(BondAuditEvent).where(BondAuditEvent.owner_id == owner_id))
        session.execute(delete(BondPurchase).where(BondPurchase.account_id.in_(account_ids)))
        session.execute(delete(BondIssue).where(BondIssue.owner_id == owner_id))
        session.execute(
            delete(PriceObservation).where(PriceObservation.account_id.in_(account_ids))
        )
        session.execute(delete(AuditEvent).where(AuditEvent.owner_id == owner_id))
        session.execute(delete(PurchaseDetails).where(PurchaseDetails.operation_id.in_(ids)))
        session.execute(delete(Operation).where(Operation.account_id.in_(account_ids)))
        instrument_ids = select(Instrument.id).where(Instrument.owner_id == owner_id)
        session.execute(
            delete(YahooListing).where(
                YahooListing.listing_id.in_(
                    select(Listing.id).where(Listing.instrument_id.in_(instrument_ids))
                )
            )
        )
        session.execute(
            delete(YahooListing).where(
                YahooListing.listing_id == "00000000-0000-4000-8000-000000000004"
            )
        )
        session.add(
            YahooListing(listing_id=UUID("00000000-0000-4000-8000-000000000004"), symbol="IUSQ.DE")
        )
        session.execute(delete(Listing).where(Listing.instrument_id.in_(instrument_ids)))
        session.execute(delete(Instrument).where(Instrument.owner_id == owner_id))
        session.execute(delete(Account).where(Account.owner_id == owner_id))
        session.execute(delete(Owner).where(Owner.id == owner_id))
