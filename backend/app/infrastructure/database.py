from sqlalchemy import Engine, create_engine


def make_engine(url) -> Engine:
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
    )
