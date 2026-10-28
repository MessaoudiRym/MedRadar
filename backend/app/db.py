"""Database connection (SQLite in development, PostgreSQL in production)."""

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

logger = logging.getLogger("medradar")

is_sqlite = DATABASE_URL.startswith("sqlite")
CONNECT_ATTEMPTS = 4  # a sleeping Neon database answers in a few seconds

if is_sqlite:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Neon (free plan) suspends the database after 5 minutes without queries and
    # closes its connections: few connections, each tested before use and renewed
    # before Neon drops it. sslmode=require stays in the URL and is used as is.
    engine = create_engine(
        DATABASE_URL,
        pool_size=3,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=240,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10,
            # The Neon pooler (PgBouncer) shares server connections between clients:
            # no prepared statements kept on the server
            "prepare_threshold": None,
        },
    )

    @event.listens_for(engine, "do_connect")
    def _connect_with_retry(dialect, conn_rec, cargs, cparams):
        """The first connection can fail while Neon wakes up: try again a few times."""
        for attempt in range(1, CONNECT_ATTEMPTS + 1):
            try:
                return dialect.connect(*cargs, **cparams)
            except Exception as error:
                if attempt == CONNECT_ATTEMPTS:
                    raise
                logger.warning("Database connection failed (attempt %s/%s, %s), retrying",
                               attempt, CONNECT_ATTEMPTS, type(error).__name__)
                time.sleep(2 * attempt)

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
