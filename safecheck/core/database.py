"""SQLAlchemy engine and session management for the local SQLite store."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from safecheck.config import DATABASE_URL


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""


# ``check_same_thread=False`` lets the Flet UI thread and background sync
# workers share the engine. SQLite remains safe for our single-user field use.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001
    """SQLite disables foreign-key enforcement by default; turn it on."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ``expire_on_commit=False`` keeps attribute access working after commit, which
# is convenient for the UI layer that reads objects right after saving them.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    # Import models so they register on ``Base.metadata`` before create_all.
    from safecheck.core import models  # noqa: F401  (import for side effects)

    Base.metadata.create_all(engine)
