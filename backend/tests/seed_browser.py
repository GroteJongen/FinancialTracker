"""Create empty synthetic browser-test accounts explicitly; never runs on app startup."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.config import get_settings
from app.infrastructure.database import make_engine
from app.infrastructure.models import Account


def main():
    settings = get_settings()
    engine = make_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            for suffix, name in [
                (10, "TEST — wycena"), (11, "TEST — daty"), (12, "TEST — ponowienie"),
            ]:
                connection.execute(insert(Account).values(
                    id=UUID(f"00000000-0000-4000-8000-{suffix:012d}"),
                    owner_id=settings.local_owner_id, name=name, kind="IKE", currency="EUR",
                ).on_conflict_do_nothing(index_elements=["id"]))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
