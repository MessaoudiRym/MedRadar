"""Database migrations, applied when the API starts.

The free plan of Render has no pre-deploy command: the API applies the Alembic
migrations itself before answering. A PostgreSQL lock makes it safe when two
instances start at the same time (a deploy while the old one still runs); when
the database is already up to date, it does nothing.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from .db import engine, is_sqlite

logger = logging.getLogger("medradar")

BACKEND = Path(__file__).resolve().parents[1]
LOCK_ID = 7_243_051  # any fixed number: the same for every MedRadar instance


class MigrationFailed(RuntimeError):
    pass


def _config():
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["configure_logger"] = False  # keep the API's logging
    return config


def _current_and_head(connection, config):
    current = MigrationContext.configure(connection).get_current_revision()
    return current, ScriptDirectory.from_config(config).get_current_head()


def migrate():
    """Bring the database to the latest migration. Raises MigrationFailed."""
    config = _config()
    try:
        with engine.connect() as connection:
            if not is_sqlite:
                # Waits while another instance migrates; released below or on disconnect
                connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": LOCK_ID})
                connection.commit()
            try:
                current, head = _current_and_head(connection, config)
                connection.commit()
                if current == head:
                    logger.info("Database is up to date (migration %s)", head)
                    return
                logger.info("Migrating the database from %s to %s", current or "empty", head)
                command.upgrade(config, "head")
                logger.info("Database migrated to %s", head)
            finally:
                if not is_sqlite:
                    connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                    connection.commit()
    except Exception as error:
        logger.exception("DATABASE MIGRATION FAILED: the API cannot start. Check DATABASE_URL "
                         "and the database (see docs/deployment.md).")
        raise MigrationFailed(str(error)) from error
