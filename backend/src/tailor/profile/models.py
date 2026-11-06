"""Tables du profil maître : faits révisionnés (append-only), versions, préférences,
banque de réponses et imports de CV."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from tailor.ids import new_ulid
from tailor.llm.models import utcnow


class ProfileVersion(SQLModel, table=True):
    """Chaque modification validée du profil crée une version (numéro croissant)."""

    __tablename__ = "profile_version"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    reason: str


class Fact(SQLModel, table=True):
    __tablename__ = "fact"  # type: ignore[assignment]

    id: str = Field(default_factory=new_ulid, primary_key=True)
    kind: str = Field(index=True)
    parent_id: str | None = Field(default=None, foreign_key="fact.id", index=True)
    position: int = 0
    current_rev: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    # Un fait retiré n'est plus proposé, mais ses révisions restent lisibles.
    retired_at: datetime | None = None


class FactRevision(SQLModel, table=True):
    __tablename__ = "fact_revision"  # type: ignore[assignment]

    fact_id: str = Field(foreign_key="fact.id", primary_key=True)
    rev: int = Field(primary_key=True)
    content: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    # Passage du CV dont le fait a été extrait (None pour une saisie manuelle).
    source_excerpt: str | None = None
    profile_version: int = Field(foreign_key="profile_version.id")
    created_at: datetime = Field(default_factory=utcnow)


class Preference(SQLModel, table=True):
    """Préférences de recherche : une seule ligne (id = 1)."""

    __tablename__ = "preference"  # type: ignore[assignment]

    id: int = Field(default=1, primary_key=True)
    content: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    updated_at: datetime = Field(default_factory=utcnow)


class AnswerBankEntry(SQLModel, table=True):
    __tablename__ = "answer_bank"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    question: str
    # Question normalisée (casse, accents, ponctuation) : clé de réutilisation à l'identique.
    question_key: str = Field(index=True, unique=True)
    answer: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CvImport(SQLModel, table=True):
    __tablename__ = "cv_import"  # type: ignore[assignment]

    id: str = Field(default_factory=new_ulid, primary_key=True)
    filename: str
    created_at: datetime = Field(default_factory=utcnow)
    status: str = "draft"  # draft | validated | discarded
    text: str
    draft: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
