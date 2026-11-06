"""Préférences de recherche, banque de réponses, export et suppression des données."""

import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from tailor.data import build_export, wipe_all
from tailor.db import SessionDep
from tailor.profile.models import AnswerBankEntry
from tailor.profile.preferences import (
    Preferences,
    delete_answer,
    find_answer,
    get_preferences,
    list_answers,
    save_answer,
    save_preferences,
)

router = APIRouter(tags=["réglages"])

DELETE_CONFIRMATION = "SUPPRIMER"


class AnswerIn(BaseModel):
    question: str
    answer: str


class AnswerOut(BaseModel):
    id: int
    question: str
    answer: str
    updated_at: datetime


class DeleteAll(BaseModel):
    confirmation: Literal["SUPPRIMER"]


def _answer_out(entry: AnswerBankEntry) -> AnswerOut:
    return AnswerOut.model_validate(entry, from_attributes=True)


@router.get("/preferences")
def read_preferences(session: SessionDep) -> Preferences:
    return get_preferences(session)


@router.put("/preferences")
def write_preferences(body: Preferences, session: SessionDep) -> Preferences:
    save_preferences(session, body)
    session.commit()
    return body


@router.get("/answers")
def read_answers(session: SessionDep) -> list[AnswerOut]:
    return [_answer_out(entry) for entry in list_answers(session)]


@router.get("/answers/lookup")
def lookup_answer(question: str, session: SessionDep) -> AnswerOut | None:
    entry = find_answer(session, question)
    return _answer_out(entry) if entry else None


@router.post("/answers", status_code=201)
def create_answer(body: AnswerIn, session: SessionDep) -> AnswerOut:
    entry = save_answer(session, body.question, body.answer)
    session.commit()
    return _answer_out(entry)


@router.put("/answers/{entry_id}")
def update_answer(entry_id: int, body: AnswerIn, session: SessionDep) -> AnswerOut:
    entry = save_answer(session, body.question, body.answer, entry_id)
    session.commit()
    return _answer_out(entry)


@router.delete("/answers/{entry_id}", status_code=204)
def remove_answer(entry_id: int, session: SessionDep) -> Response:
    delete_answer(session, entry_id)
    session.commit()
    return Response(status_code=204)


@router.get("/data/export")
def export_data(session: SessionDep) -> Response:
    payload = json.dumps(build_export(session), ensure_ascii=False, indent=2)
    return Response(
        payload,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="tailor-export.json"'},
    )


@router.post("/data/delete", status_code=204)
def delete_all(_body: DeleteAll, request: Request) -> Response:
    settings = request.app.state.settings
    wipe_all(request.app.state.engine, settings.files_dir)
    return Response(status_code=204)
