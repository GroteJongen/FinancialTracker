import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.infrastructure.config import Settings
from app.infrastructure.database import make_engine


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
    saved = {key: os.environ.get(key) for key in (
        "DATABASE_HOST", "DATABASE_PORT", "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME"
    )}
    os.environ.update({
        "DATABASE_HOST": settings.database_host,
        "DATABASE_PORT": str(settings.database_port),
        "DATABASE_USER": settings.database_user,
        "DATABASE_PASSWORD": settings.database_password.get_secret_value(),
        "DATABASE_NAME": settings.database_name,
    })
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

