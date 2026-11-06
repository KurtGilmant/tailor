"""Export complet et suppression totale des données de l'utilisateur.

Le format d'export est documenté dans `docs/export.md`. Chaque jalon qui ajoute des
données (offres, dossiers, candidatures) ajoute sa section ici et dans la doc.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, delete
from sqlmodel import Session, SQLModel, col, select

import tailor.models  # noqa: F401  (toutes les tables doivent être enregistrées)
from tailor import __version__
from tailor.llm.models import LlmCall, LlmConsent, utcnow
from tailor.profile.models import (
    AnswerBankEntry,
    CvImport,
    Fact,
    FactRevision,
    ProfileVersion,
)
from tailor.profile.preferences import get_preferences

EXPORT_FORMAT = "tailor-export"
EXPORT_FORMAT_VERSION = 1


def build_export(session: Session) -> dict[str, Any]:
    revisions: dict[str, list[dict[str, Any]]] = {}
    for revision in session.exec(select(FactRevision).order_by(col(FactRevision.rev))).all():
        revisions.setdefault(revision.fact_id, []).append(
            revision.model_dump(mode="json", exclude={"fact_id"})
        )
    facts = [
        {**fact.model_dump(mode="json"), "revisions": revisions.get(fact.id, [])}
        for fact in session.exec(select(Fact).order_by(col(Fact.created_at))).all()
    ]
    return {
        "format": EXPORT_FORMAT,
        "format_version": EXPORT_FORMAT_VERSION,
        "app_version": __version__,
        "exported_at": utcnow().isoformat(),
        "profile": {
            "versions": _dump_all(session, ProfileVersion, ProfileVersion.id),
            "facts": facts,
        },
        "preferences": get_preferences(session).model_dump(mode="json"),
        "answers": _dump_all(session, AnswerBankEntry, AnswerBankEntry.id),
        "cv_imports": _dump_all(session, CvImport, CvImport.created_at),
        "llm": {
            "consents": _dump_all(session, LlmConsent, LlmConsent.provider),
            "calls": _dump_all(session, LlmCall, LlmCall.id),
        },
    }


def _dump_all(session: Session, model: type[SQLModel], order: Any) -> list[dict[str, Any]]:
    return [
        row.model_dump(mode="json") for row in session.exec(select(model).order_by(order)).all()
    ]


def wipe_all(engine: Engine, files_dir: Path) -> None:
    """Efface toutes les données (la configuration tailor.toml est conservée)."""
    with Session(engine) as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.exec(delete(table))  # type: ignore[call-overload]
        session.commit()
    # VACUUM réécrit le fichier : les pages libérées ne gardent pas d'anciennes données.
    # En mode WAL, le checkpoint TRUNCATE vide aussi le journal (-wal) qui en garde copie.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql("VACUUM")
        connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    if files_dir.exists():
        shutil.rmtree(files_dir)
    files_dir.mkdir(mode=0o700)
