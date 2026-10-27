"""Database connection (SQLite in development, PostgreSQL in production)."""

from datetime import datetime, timezone

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    # A hosted PostgreSQL closes idle connections: test each one before using it
    pool_pre_ping=not is_sqlite,
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        # SQLite ignores foreign keys unless asked
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    # Named constraints, so that migrations can alter them later (needed on SQLite)
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


def utcnow():
    """Current time in UTC, stored without time zone (same behaviour on SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as session:
        yield session
