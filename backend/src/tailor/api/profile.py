from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlmodel import col, select

from tailor.api.llm import GatewayDep
from tailor.db import SessionDep
from tailor.profile.cv_import import Draft, DraftItem, extract_cv, normalize_for_match
from tailor.profile.models import CvImport
from tailor.profile.schemas import FactKind
from tailor.profile.service import FactView, NewFact, ProfileError, ProfileService
from tailor.profile.text_extraction import MAX_BYTES, CvTextError, extract_text

router = APIRouter(prefix="/profile", tags=["profil"])


class FactOut(BaseModel):
    id: str
    kind: FactKind
    parent_id: str | None
    position: int
    rev: int
    content: dict[str, Any]
    source_excerpt: str | None
    created_at: datetime
    updated_at: datetime
    # Compétences uniquement : « supported » (étayée) ou « declarative ».
    skill_status: Literal["supported", "declarative"] | None


class ProfileOut(BaseModel):
    version: int
    facts: list[FactOut]


class FactCreate(BaseModel):
    kind: FactKind
    parent_id: str | None = None
    content: dict[str, Any]


class FactUpdate(BaseModel):
    content: dict[str, Any]


class RevisionOut(BaseModel):
    rev: int
    content: dict[str, Any]
    source_excerpt: str | None
    profile_version: int
    created_at: datetime


class RetireOut(BaseModel):
    retired: list[str]


class ImportOut(BaseModel):
    id: str
    filename: str
    created_at: datetime
    status: str
    draft: Draft


class ImportValidation(BaseModel):
    items: list[DraftItem]


def _fact_out(view: FactView, active_ids: set[str], service: ProfileService) -> FactOut:
    fact, revision = view.fact, view.revision
    status = None
    if fact.kind == FactKind.SKILL:
        supported = service.skill_supported(revision.content, active_ids)
        status = "supported" if supported else "declarative"
    return FactOut(
        id=fact.id,
        kind=FactKind(fact.kind),
        parent_id=fact.parent_id,
        position=fact.position,
        rev=revision.rev,
        content=revision.content,
        source_excerpt=revision.source_excerpt,
        created_at=fact.created_at,
        updated_at=revision.created_at,
        skill_status=status,
    )


def _profile_out(service: ProfileService) -> ProfileOut:
    active_ids = service.active_ids()
    return ProfileOut(
        version=service.current_version(),
        facts=[_fact_out(view, active_ids, service) for view in service.active_facts()],
    )


def _single_fact(service: ProfileService, fact_id: str) -> FactOut:
    fact = service.get_fact(fact_id)
    view = FactView(fact, service.revision(fact.id, fact.current_rev))
    return _fact_out(view, service.active_ids(), service)


@router.get("")
def get_profile(session: SessionDep) -> ProfileOut:
    return _profile_out(ProfileService(session))


@router.post("/facts", status_code=201)
def create_fact(body: FactCreate, session: SessionDep) -> FactOut:
    service = ProfileService(session)
    fact = service.create_fact(body.kind, body.content, parent_id=body.parent_id)
    session.commit()
    return _single_fact(service, fact.id)


@router.put("/facts/{fact_id}")
def update_fact(fact_id: str, body: FactUpdate, session: SessionDep) -> FactOut:
    service = ProfileService(session)
    service.update_fact(fact_id, body.content)
    session.commit()
    return _single_fact(service, fact_id)


@router.delete("/facts/{fact_id}")
def retire_fact(fact_id: str, session: SessionDep) -> RetireOut:
    retired = ProfileService(session).retire_fact(fact_id)
    session.commit()
    return RetireOut(retired=retired)


@router.get("/facts/{fact_id}/revisions")
def fact_revisions(fact_id: str, session: SessionDep) -> list[RevisionOut]:
    return [
        RevisionOut.model_validate(revision, from_attributes=True)
        for revision in ProfileService(session).revisions(fact_id)
    ]


@router.post("/imports", status_code=201)
async def import_cv(
    file: Annotated[UploadFile, File()], session: SessionDep, gateway: GatewayDep
) -> ImportOut:
    data = await file.read(MAX_BYTES + 1)
    filename = file.filename or "cv"
    try:
        text = extract_text(filename, data)
    except CvTextError as error:
        raise HTTPException(422, str(error)) from None
    draft = await extract_cv(gateway, text)
    cv_import = CvImport(filename=filename, text=text, draft=draft.model_dump(mode="json"))
    session.add(cv_import)
    session.commit()
    return _import_out(cv_import)


@router.get("/imports/pending")
def pending_import(session: SessionDep) -> ImportOut | None:
    """Brouillon en attente de revue (le plus récent), pour reprendre après un rechargement."""
    cv_import = session.exec(
        select(CvImport).where(CvImport.status == "draft").order_by(col(CvImport.created_at).desc())
    ).first()
    return _import_out(cv_import) if cv_import else None


@router.get("/imports/{import_id}")
def get_import(import_id: str, session: SessionDep) -> ImportOut:
    return _import_out(_get_import(session, import_id))


@router.post("/imports/{import_id}/validate")
def validate_import(import_id: str, body: ImportValidation, session: SessionDep) -> ProfileOut:
    cv_import = _get_import(session, import_id)
    if cv_import.status != "draft":
        raise HTTPException(409, "Cet import a déjà été validé ou abandonné.")
    normalized_text = normalize_for_match(cv_import.text)
    kept = [item for item in body.items if item.keep]
    for item in kept:
        # Le passage source n'est pas modifiable : il doit toujours venir du CV importé.
        if normalize_for_match(item.source_excerpt) not in normalized_text:
            raise HTTPException(422, f"Élément « {item.ref} » : passage absent du CV importé.")

    service = ProfileService(session)
    service.create_batch(
        [
            NewFact(
                ref=item.ref,
                kind=item.kind,
                content=item.content,
                parent_ref=item.parent_ref,
                source_excerpt=item.source_excerpt,
                evidence_refs=tuple(item.evidence_refs),
            )
            for item in kept
        ],
        reason=f"Import du CV « {cv_import.filename} »",
    )
    cv_import.status = "validated"
    session.add(cv_import)
    session.commit()
    return _profile_out(service)


@router.delete("/imports/{import_id}", status_code=204)
def discard_import(import_id: str, session: SessionDep) -> Response:
    cv_import = _get_import(session, import_id)
    if cv_import.status == "draft":
        cv_import.status = "discarded"
        session.add(cv_import)
        session.commit()
    return Response(status_code=204)


def _get_import(session: SessionDep, import_id: str) -> CvImport:
    cv_import = session.get(CvImport, import_id)
    if cv_import is None:
        raise ProfileError(f"Import introuvable : {import_id}.", 404)
    return cv_import


def _import_out(cv_import: CvImport) -> ImportOut:
    return ImportOut(
        id=cv_import.id,
        filename=cv_import.filename,
        created_at=cv_import.created_at,
        status=cv_import.status,
        draft=Draft.model_validate(cv_import.draft),
    )
