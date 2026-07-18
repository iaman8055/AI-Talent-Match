import os
from collections.abc import Iterator

import pytest
import src.infrastructure.db.models  # noqa: F401 registers tables on Base.metadata
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from src.core.config import get_settings
from src.infrastructure.db.base import Base


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", get_settings().database_url)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = _database_url()
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip(f"Postgres not reachable at {url!r} — integration tests unverified locally")

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
