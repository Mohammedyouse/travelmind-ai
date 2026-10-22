from __future__ import annotations

import os
from pathlib import Path

from .models import Base

try:
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool, QueuePool
except ImportError:  # pragma: no cover - stdlib SQLite fallback is used in minimal environments.
    create_engine = None
    event = None
    Engine = None
    sessionmaker = None
    NullPool = None
    QueuePool = None
    text = None


DEFAULT_DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'travelmind.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# Normalise provider prefixes (Neon / Heroku ship `postgres://` or plain `postgresql://`)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL.split(":", 1)[0]:
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgresql://")

_IS_SQLITE = DATABASE_URL.startswith("sqlite")
_IS_POSTGRES = DATABASE_URL.startswith("postgresql")

SQLALCHEMY_AVAILABLE = create_engine is not None
engine = None
SessionLocal = None

if SQLALCHEMY_AVAILABLE:
    if _IS_SQLITE:
        # SQLite: single-file, no pooling concerns.
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # PostgreSQL (Neon free tier):
        #   - NullPool avoids idle-connection exhaustion on serverless/free instances.
        #   - sslmode=require is mandatory for Neon; inject it if not already present.
        _url = DATABASE_URL
        if "sslmode=" not in _url:
            _sep = "&" if "?" in _url else "?"
            _url = f"{_url}{_sep}sslmode=require"

        engine = create_engine(
            _url,
            poolclass=NullPool,        # no persistent idle connections — safe on free tier
            pool_pre_ping=True,        # discard stale connections after sleep
            connect_args={
                "connect_timeout": 10,
            },
        )

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_schema() -> None:
    """Create all tables (idempotent).  Called at startup before alembic."""
    if not SQLALCHEMY_AVAILABLE or engine is None:
        raise RuntimeError("SQLAlchemy is not installed; use the SQLite fallback initializer")
    Base.metadata.create_all(engine)


def verify_connection() -> bool:
    """Return True if the database is reachable; False otherwise (safe for health checks)."""
    if not SQLALCHEMY_AVAILABLE or engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False