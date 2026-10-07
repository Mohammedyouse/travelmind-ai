from __future__ import annotations

import os
from pathlib import Path

from .models import Base

try:
    from sqlalchemy import create_engine, event
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import sessionmaker
except ImportError:  # pragma: no cover - stdlib SQLite fallback is used in minimal environments.
    create_engine = None
    event = None
    Engine = None
    sessionmaker = None


DEFAULT_DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'travelmind.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL.split(":", 1)[0]:
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgresql://")

SQLALCHEMY_AVAILABLE = create_engine is not None
engine = None
SessionLocal = None

if SQLALCHEMY_AVAILABLE:
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    if DATABASE_URL.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def initialize_schema() -> None:
    if not SQLALCHEMY_AVAILABLE or engine is None:
        raise RuntimeError("SQLAlchemy is not installed; use the SQLite fallback initializer")
    Base.metadata.create_all(engine)