"""Accès SQLite (SQLModel) et migrations Alembic."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends, Request
from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def make_engine(db_url: str) -> Engine:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:  # pragma: no cover - trivial
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def alembic_config(db_url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def upgrade(db_url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(db_url), revision)


def downgrade(db_url: str, revision: str) -> None:
    command.downgrade(alembic_config(db_url), revision)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
