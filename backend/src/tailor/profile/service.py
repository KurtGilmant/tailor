"""Opérations sur le profil maître.

Règles :
- un fait garde son identifiant ; chaque modification ajoute une révision (append-only) ;
- chaque modification validée crée une nouvelle version du profil ;
- retirer un fait ne l'efface pas : il n'est plus proposé, mais ses révisions restent
  lisibles (un dossier déjà envoyé peut les citer) ;
- une compétence est « étayée » si au moins un fait actif la démontre.

Le service ne valide pas la transaction : l'appelant fait `session.commit()`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, col, select

from tailor.llm.models import utcnow
from tailor.profile.models import Fact, FactRevision, ProfileVersion
from tailor.profile.schemas import (
    EVIDENCE_KINDS,
    PARENT_KINDS,
    FactKind,
    validate_content,
)


class ProfileError(Exception):
    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class FactView:
    fact: Fact
    revision: FactRevision


@dataclass(frozen=True)
class NewFact:
    """Fait à créer, éventuellement relié à d'autres faits du même lot par des
    références temporaires (utilisé par la validation d'un import de CV)."""

    ref: str
    kind: FactKind
    content: dict
    parent_ref: str | None = None
    source_excerpt: str | None = None
    evidence_refs: tuple[str, ...] = ()


# Ordre de création d'un lot : les parents et les preuves avant ceux qui les citent.
_BATCH_ORDER = [
    FactKind.IDENTITY,
    FactKind.EXPERIENCE,
    FactKind.PROJECT,
    FactKind.EDUCATION,
    FactKind.CERTIFICATION,
    FactKind.LANGUAGE,
    FactKind.ACHIEVEMENT,
    FactKind.SKILL,
]


class ProfileService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Lecture ---------------------------------------------------------------

    def current_version(self) -> int:
        return int(self.session.exec(select(func.max(ProfileVersion.id))).one() or 0)

    def get_fact(self, fact_id: str) -> Fact:
        fact = self.session.get(Fact, fact_id)
        if fact is None:
            raise ProfileError(f"Fait introuvable : {fact_id}.", 404)
        return fact

    def revisions(self, fact_id: str) -> list[FactRevision]:
        self.get_fact(fact_id)
        return list(
            self.session.exec(
                select(FactRevision)
                .where(FactRevision.fact_id == fact_id)
                .order_by(col(FactRevision.rev))
            ).all()
        )

    def revision(self, fact_id: str, rev: int) -> FactRevision:
        revision = self.session.get(FactRevision, (fact_id, rev))
        if revision is None:
            raise ProfileError(f"Révision introuvable : {fact_id}@{rev}.", 404)
        return revision

    def active_facts(self) -> list[FactView]:
        rows = self.session.exec(
            select(Fact, FactRevision)
            .join(
                FactRevision,
                (col(FactRevision.fact_id) == Fact.id)
                & (col(FactRevision.rev) == Fact.current_rev),
            )
            .where(col(Fact.retired_at).is_(None))
            .order_by(col(Fact.kind), col(Fact.position), col(Fact.created_at))
        ).all()
        return [FactView(fact, revision) for fact, revision in rows]

    def active_ids(self) -> set[str]:
        return set(self.session.exec(select(Fact.id).where(col(Fact.retired_at).is_(None))).all())

    def skill_supported(self, content: dict, active_ids: set[str]) -> bool:
        return any(fact_id in active_ids for fact_id in content.get("evidence", []))

    # --- Écriture --------------------------------------------------------------

    def new_version(self, reason: str) -> int:
        version = ProfileVersion(reason=reason)
        self.session.add(version)
        self.session.flush()
        if version.id is None:  # attribué par SQLite au flush
            raise RuntimeError("Version de profil non attribuée.")
        return version.id

    def create_fact(
        self,
        kind: FactKind | str,
        content: dict,
        *,
        parent_id: str | None = None,
        source_excerpt: str | None = None,
        version: int | None = None,
    ) -> Fact:
        kind = _kind(kind)
        normalized = self._validate(kind, content, parent_id)
        version = version or self.new_version(f"Ajout ({kind})")
        position = self.session.exec(
            select(func.count())
            .select_from(Fact)
            .where(Fact.kind == kind, Fact.parent_id == parent_id)
        ).one()
        fact = Fact(kind=kind, parent_id=parent_id, position=position)
        self.session.add(fact)
        self.session.flush()
        self.session.add(
            FactRevision(
                fact_id=fact.id,
                rev=1,
                content=normalized,
                source_excerpt=source_excerpt,
                profile_version=version,
            )
        )
        self.session.flush()
        return fact

    def update_fact(self, fact_id: str, content: dict, *, version: int | None = None) -> Fact:
        fact = self._active(fact_id)
        kind = FactKind(fact.kind)
        normalized = self._validate(kind, content, fact.parent_id, self_id=fact.id)
        current = self.revision(fact.id, fact.current_rev)
        if normalized == current.content:
            return fact  # rien de changé : pas de nouvelle version
        version = version or self.new_version(f"Modification ({kind})")
        fact.current_rev += 1
        self.session.add(fact)
        self.session.add(
            FactRevision(
                fact_id=fact.id,
                rev=fact.current_rev,
                content=normalized,
                # On garde l'origine du fait : la reformulation ne change pas sa source.
                source_excerpt=current.source_excerpt,
                profile_version=version,
            )
        )
        self.session.flush()
        return fact

    def retire_fact(self, fact_id: str) -> list[str]:
        """Retire un fait et ses réalisations rattachées ; renvoie les identifiants retirés."""
        fact = self._active(fact_id)
        self.new_version(f"Retrait ({fact.kind})")
        now = utcnow()
        retired = [fact]
        retired += self.session.exec(
            select(Fact).where(Fact.parent_id == fact.id, col(Fact.retired_at).is_(None))
        ).all()
        for item in retired:
            item.retired_at = now
            self.session.add(item)
        self.session.flush()
        return [item.id for item in retired]

    def create_batch(self, items: Iterable[NewFact], reason: str) -> dict[str, str]:
        """Crée un lot de faits dans une seule version ; renvoie ref temporaire -> id réel.

        Une réalisation dont le parent n'est pas dans le lot est ignorée, et une preuve
        de compétence qui ne pointe vers aucun fait du lot est retirée de la liste.
        """
        items = sorted(items, key=lambda item: _BATCH_ORDER.index(item.kind))
        version = self.new_version(reason)
        ids: dict[str, str] = {}
        for item in items:
            parent_id = None
            if item.kind in PARENT_KINDS:
                parent_id = ids.get(item.parent_ref or "")
                if parent_id is None:
                    continue
            content = dict(item.content)
            if item.kind == FactKind.SKILL:
                content["evidence"] = [ids[ref] for ref in item.evidence_refs if ref in ids]
            if item.kind == FactKind.IDENTITY and (existing := self._active_identity()):
                self.update_fact(existing.id, content, version=version)
                ids[item.ref] = existing.id
                continue
            fact = self.create_fact(
                item.kind,
                content,
                parent_id=parent_id,
                source_excerpt=item.source_excerpt,
                version=version,
            )
            ids[item.ref] = fact.id
        return ids

    # --- Règles ----------------------------------------------------------------

    def _active(self, fact_id: str) -> Fact:
        fact = self.get_fact(fact_id)
        if fact.retired_at is not None:
            raise ProfileError("Ce fait a été retiré du profil ; il n'est plus modifiable.", 409)
        return fact

    def _active_identity(self) -> Fact | None:
        return self.session.exec(
            select(Fact).where(Fact.kind == FactKind.IDENTITY, col(Fact.retired_at).is_(None))
        ).first()

    def _validate(
        self, kind: FactKind, content: dict, parent_id: str | None, self_id: str | None = None
    ) -> dict:
        allowed_parents = PARENT_KINDS.get(kind)
        if allowed_parents is None and parent_id is not None:
            raise ProfileError(f"Un fait « {kind} » ne se rattache à aucun autre fait.")
        if allowed_parents is not None:
            if parent_id is None:
                raise ProfileError(
                    f"Un fait « {kind} » doit être rattaché à une expérience ou un projet."
                )
            parent = self._active(parent_id)
            if parent.kind not in allowed_parents:
                raise ProfileError(
                    f"Un fait « {kind} » ne peut pas être rattaché à « {parent.kind} »."
                )

        if kind == FactKind.IDENTITY:
            identity = self._active_identity()
            if identity is not None and identity.id != self_id:
                raise ProfileError("Le profil a déjà une identité : modifie-la plutôt.", 409)

        try:
            normalized = validate_content(kind, content)
        except ValidationError as error:
            details = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])} : {e['msg']}"
                for e in error.errors(include_url=False)
            )
            raise ProfileError(f"Contenu invalide pour « {kind} » : {details}") from None

        if kind == FactKind.SKILL:
            for evidence_id in normalized["evidence"]:
                evidence = self.session.get(Fact, evidence_id)
                if evidence is None or evidence.retired_at is not None:
                    raise ProfileError(f"Preuve introuvable ou retirée : {evidence_id}.")
                if evidence.kind not in EVIDENCE_KINDS:
                    raise ProfileError(f"Un fait « {evidence.kind} » ne peut pas servir de preuve.")
        return normalized


def _kind(kind: FactKind | str) -> FactKind:
    try:
        return FactKind(kind)
    except ValueError:
        raise ProfileError(f"Type de fait inconnu : « {kind} ».") from None
