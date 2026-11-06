"""Préférences de recherche et banque de réponses réutilisables."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, col, select

from tailor.llm.models import utcnow
from tailor.profile.models import AnswerBankEntry, Preference
from tailor.profile.service import ProfileError

ContractType = Literal["cdi", "cdd", "alternance", "stage", "freelance", "interim"]
WorkMode = Literal["sur_site", "hybride", "teletravail_complet"]


class SalaryExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)
    currency: str = "EUR"
    period: Literal["annuel", "mensuel", "journalier"] = "annuel"


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_types: list[ContractType] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    # Modes de travail acceptés : « Bordeaux ou télétravail complet » = deux modes.
    work_modes: list[WorkMode] = Field(default_factory=list)
    salary: SalaryExpectation | None = None
    available_from: date | None = None
    work_languages: list[str] = Field(default_factory=list)
    work_authorization: str | None = None
    notice_period: str | None = None
    excluded_companies: list[str] = Field(default_factory=list)


def get_preferences(session: Session) -> Preferences:
    row = session.get(Preference, 1)
    return Preferences.model_validate(row.content) if row else Preferences()


def save_preferences(session: Session, preferences: Preferences) -> Preferences:
    row = session.get(Preference, 1) or Preference(id=1, content={})
    row.content = preferences.model_dump(mode="json")
    row.updated_at = utcnow()
    session.add(row)
    session.flush()
    return preferences


def question_key(question: str) -> str:
    """Clé de réutilisation « à l'identique » : on ignore casse, accents et ponctuation."""
    text = unicodedata.normalize("NFKD", question.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def list_answers(session: Session) -> list[AnswerBankEntry]:
    return list(session.exec(select(AnswerBankEntry).order_by(col(AnswerBankEntry.question))).all())


def find_answer(session: Session, question: str) -> AnswerBankEntry | None:
    key = question_key(question)
    return session.exec(select(AnswerBankEntry).where(AnswerBankEntry.question_key == key)).first()


def save_answer(
    session: Session, question: str, answer: str, entry_id: int | None = None
) -> AnswerBankEntry:
    question, answer = question.strip(), answer.strip()
    if not question or not answer:
        raise ProfileError("La question et la réponse sont obligatoires.")
    key = question_key(question)
    duplicate = find_answer(session, question)
    if duplicate is not None and duplicate.id != entry_id:
        raise ProfileError("Une réponse existe déjà pour cette question.", 409)
    if entry_id is None:
        entry = AnswerBankEntry(question=question, question_key=key, answer=answer)
    else:
        entry = _get_answer(session, entry_id)
        entry.question, entry.question_key, entry.answer = question, key, answer
        entry.updated_at = utcnow()
    session.add(entry)
    session.flush()
    return entry


def delete_answer(session: Session, entry_id: int) -> None:
    session.delete(_get_answer(session, entry_id))
    session.flush()


def _get_answer(session: Session, entry_id: int) -> AnswerBankEntry:
    entry = session.get(AnswerBankEntry, entry_id)
    if entry is None:
        raise ProfileError(f"Réponse introuvable : {entry_id}.", 404)
    return entry
