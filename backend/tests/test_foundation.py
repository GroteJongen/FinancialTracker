from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.infrastructure.models import Account, Base, Owner
from app.main import create_app
from app.seed import DEMO_ACCOUNT_ID, seed_demo


def test_migration_matches_models(test_database):
    engine, _, _ = test_database
    with engine.connect() as connection:
        assert {"owners", "accounts", "alembic_version"} <= set(inspect(connection).get_table_names())
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_readiness_and_liveness(test_database):
    engine, settings, _ = test_database
    with TestClient(create_app(settings, engine)) as client:
        assert client.get("/api/health/live").json() == {"status": "ok"}
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}


def test_database_failure_is_sanitized(test_database):
    _, settings, _ = test_database

    class BrokenEngine:
        def connect(self):
            raise OperationalError("secret host password", {}, Exception("secret connection"))

    with TestClient(create_app(settings, BrokenEngine())) as client:
        assert client.get("/api/health/live").status_code == 200
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert "secret" not in response.text


def test_seed_is_idempotent_and_accounts_are_isolated(test_database):
    engine, settings, _ = test_database
    seed_demo(engine, settings.local_owner_id)
    seed_demo(engine, settings.local_owner_id)
    stranger = uuid4()
    hidden_account = uuid4()
    with Session(engine) as session, session.begin():
        session.add(Owner(id=stranger, name="Inny użytkownik testowy"))
        session.flush()
        session.add(Account(
            id=hidden_account, owner_id=stranger, name="Ukryty rachunek",
            kind="STANDARD", currency="PLN",
        ))
    try:
        with TestClient(create_app(settings, engine)) as client:
            response = client.get(f"/api/accounts?owner_id={stranger}")
            assert response.status_code == 200
            accounts = response.json()
            assert [item["id"] for item in accounts] == [str(DEMO_ACCOUNT_ID)]
            assert accounts[0]["kind"] == "IKE"
        with Session(engine) as session:
            assert session.scalar(
                select(func.count()).select_from(Account).where(
                    Account.owner_id == settings.local_owner_id
                )
            ) == 1
    finally:
        with Session(engine) as session, session.begin():
            session.query(Account).filter(Account.owner_id == stranger).delete()
            session.query(Owner).filter(Owner.id == stranger).delete()

