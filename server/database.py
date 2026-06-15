"""Central database for the synchronisation server.

Reuses the same ORM models as the field app (identical schema) but binds them to
a *separate* central SQLite database. The path can be overridden with the
``SAFECHECK_CENTRAL_DB`` environment variable (used by the tests).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from safecheck.config import BASE_DIR
from safecheck.core import models  # noqa: F401 — register tables on Base.metadata
from safecheck.core.database import Base

# Central DB lives next to the field DB by default; tests point it elsewhere.
_default_path = BASE_DIR / "data" / "central.db"
CENTRAL_DB_PATH = os.environ.get("SAFECHECK_CENTRAL_DB", str(_default_path))
Path(CENTRAL_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
CENTRAL_DATABASE_URL = f"sqlite:///{CENTRAL_DB_PATH}"

# Server storage for uploaded photographs.
SERVER_PHOTOS_DIR = BASE_DIR / "data" / "server_photos"
SERVER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    CENTRAL_DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


ServerSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_central_db() -> None:
    """Create the central schema if needed."""
    Base.metadata.create_all(engine)
