"""Jawne utworzenie syntetycznego właściciela i rachunku. Nie uruchamia migracji."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.config import get_settings
from app.infrastructure.database import make_engine
from app.infrastructure.models import Account, Owner

DEMO_ACCOUNT_ID = UUID("00000000-0000-4000-8000-000000000002")


def seed_demo(engine, owner_id: UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            insert(Owner)
            .values(id=owner_id, name="Użytkownik demonstracyjny")
            .on_conflict_do_nothing(index_elements=["id"])
        )
        connection.execute(
            insert(Account)
            .values(
                id=DEMO_ACCOUNT_ID,
                owner_id=owner_id,
                name="IKE — demonstracja",
                kind="IKE",
                currency="EUR",
            )
            .on_conflict_do_nothing()
        )


def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    try:
        seed_demo(engine, settings.local_owner_id)
    finally:
        engine.dispose()
    print("Dane demonstracyjne są gotowe. Nie dodano aktywów ani transakcji.")


if __name__ == "__main__":
    main()
