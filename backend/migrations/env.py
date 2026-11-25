from alembic import context

from app.infrastructure.config import get_settings
from app.infrastructure.database import make_engine
from app.infrastructure.models import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    provided = context.config.attributes.get("connection")
    if provided is not None:
        context.configure(
            connection=provided,
            target_metadata=target_metadata,
            compare_type=True,
            version_table_schema=context.config.attributes.get("version_table_schema"),
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = make_engine(get_settings().database_url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
