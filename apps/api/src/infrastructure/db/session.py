from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings

settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # psycopg3 auto-prepares repeated statements server-side by default. When DATABASE_URL goes
    # through a transaction-mode pooler (e.g. Supabase's pooled connection string), the pooler can
    # hand different requests different underlying Postgres connections mid-session, so a
    # statement prepared on one physical connection collides with or is missing from another —
    # surfacing as DuplicatePreparedStatement/InvalidSqlStatementName. Disabling autoprepare is
    # psycopg's own documented fix for pooled deployments.
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
