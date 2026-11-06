"""Import d'un CV : texte -> extraction structurée par LLM -> brouillon à valider.

Invariant de véracité : chaque élément du brouillon cite un passage du CV, et un
élément dont le passage est introuvable dans le texte réel est rejeté (le modèle a pu
l'inventer ou le reformuler). Rien n'entre dans le profil avant validation humaine.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from tailor.llm import LLMGateway, Task
from tailor.profile.schemas import FactKind, validate_content

PROMPT_ID = "cv-extract"

# --- Schéma demandé au modèle ------------------------------------------------------


class XLink(BaseModel):
    label: str
    url: str


class XIdentity(BaseModel):
    full_name: str
    headline: str | None
    email: str | None
    phone: str | None
    location: str | None
    links: list[XLink]
    excerpt: str


class XAchievement(BaseModel):
    text: str
    excerpt: str


class XExperience(BaseModel):
    ref: str
    employer: str
    title: str
    start: str | None
    end: str | None
    current: bool
    location: str | None
    excerpt: str
    achievements: list[XAchievement]


class XProject(BaseModel):
    ref: str
    name: str
    description: str | None
    url: str | None
    start: str | None
    end: str | None
    excerpt: str
    achievements: list[XAchievement]


class XEducation(BaseModel):
    ref: str
    institution: str
    degree: str
    field: str | None
    start: str | None
    end: str | None
    excerpt: str


class XCertification(BaseModel):
    ref: str
    name: str
    issuer: str | None
    date: str | None
    excerpt: str


class XSkill(BaseModel):
    name: str
    category: str | None
    evidence_refs: list[str]
    excerpt: str


class XLanguage(BaseModel):
    name: str
    level: str | None
    excerpt: str


class CvExtraction(BaseModel):
    identity: XIdentity | None
    experiences: list[XExperience]
    projects: list[XProject]
    education: list[XEducation]
    certifications: list[XCertification]
    skills: list[XSkill]
    languages: list[XLanguage]


# --- Brouillon présenté à l'utilisateur ----------------------------------------------


class DraftItem(BaseModel):
    ref: str
    kind: FactKind
    parent_ref: str | None = None
    content: dict[str, Any]
    source_excerpt: str
    evidence_refs: list[str] = Field(default_factory=list)
    keep: bool = True


class RejectedItem(BaseModel):
    kind: FactKind
    content: dict[str, Any]
    source_excerpt: str
    reason: str


class Draft(BaseModel):
    items: list[DraftItem] = Field(default_factory=list)
    rejected: list[RejectedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


async def extract_cv(gateway: LLMGateway, text: str) -> Draft:
    extraction = await gateway.complete(Task.EXTRACT, PROMPT_ID, {"cv_text": text}, CvExtraction)
    return build_draft(extraction, text)


def build_draft(extraction: CvExtraction, text: str) -> Draft:
    builder = _DraftBuilder(text)
    if extraction.identity:
        identity = extraction.identity.model_dump(exclude={"excerpt"})
        builder.add("identity", FactKind.IDENTITY, identity, extraction.identity.excerpt)
    for experience in extraction.experiences:
        content = experience.model_dump(exclude={"ref", "excerpt", "achievements"})
        if builder.add(experience.ref, FactKind.EXPERIENCE, content, experience.excerpt):
            builder.add_achievements(experience.ref, experience.achievements)
    for project in extraction.projects:
        content = project.model_dump(exclude={"ref", "excerpt", "achievements"})
        if builder.add(project.ref, FactKind.PROJECT, content, project.excerpt):
            builder.add_achievements(project.ref, project.achievements)
    for education in extraction.education:
        content = education.model_dump(exclude={"ref", "excerpt"})
        builder.add(education.ref, FactKind.EDUCATION, content, education.excerpt)
    for certification in extraction.certifications:
        content = certification.model_dump(exclude={"ref", "excerpt"})
        builder.add(certification.ref, FactKind.CERTIFICATION, content, certification.excerpt)
    for index, language in enumerate(extraction.languages, 1):
        content = language.model_dump(exclude={"excerpt"})
        builder.add(f"lang{index}", FactKind.LANGUAGE, content, language.excerpt)
    for index, skill in enumerate(extraction.skills, 1):
        content = {"name": skill.name, "category": skill.category}
        builder.add(f"skill{index}", FactKind.SKILL, content, skill.excerpt, skill.evidence_refs)
    return builder.finish()


class _DraftBuilder:
    def __init__(self, text: str) -> None:
        self.text = text
        self.normalized_text = normalize_for_match(text)
        self.draft = Draft()
        self.refs: set[str] = set()

    def add(
        self,
        ref: str,
        kind: FactKind,
        content: dict[str, Any],
        excerpt: str,
        evidence_refs: list[str] | None = None,
        parent_ref: str | None = None,
    ) -> bool:
        if not self.excerpt_found(excerpt):
            self.reject(kind, content, excerpt, "passage introuvable tel quel dans le CV")
            return False
        content = self._coerce_dates(kind, content)
        try:
            validate_content(kind, content)
        except ValidationError as error:
            reason = "; ".join(str(e["msg"]) for e in error.errors(include_url=False))
            self.reject(kind, content, excerpt, f"contenu invalide ({reason})")
            return False
        ref = self._unique(ref)
        self.draft.items.append(
            DraftItem(
                ref=ref,
                kind=kind,
                parent_ref=parent_ref,
                content=content,
                source_excerpt=excerpt.strip(),
                evidence_refs=evidence_refs or [],
            )
        )
        return True

    def add_achievements(self, parent_ref: str, achievements: list[XAchievement]) -> None:
        for index, achievement in enumerate(achievements, 1):
            self.add(
                f"{parent_ref}.a{index}",
                FactKind.ACHIEVEMENT,
                {"text": achievement.text},
                achievement.excerpt,
                parent_ref=parent_ref,
            )

    def reject(self, kind: FactKind, content: dict[str, Any], excerpt: str, reason: str) -> None:
        self.draft.rejected.append(
            RejectedItem(kind=kind, content=content, source_excerpt=excerpt, reason=reason)
        )

    def excerpt_found(self, excerpt: str) -> bool:
        needle = normalize_for_match(excerpt)
        return len(needle) >= 3 and needle in self.normalized_text

    def finish(self) -> Draft:
        # Une preuve qui ne pointe vers aucun élément conservé est retirée, avec un avertissement.
        for item in self.draft.items:
            missing = [ref for ref in item.evidence_refs if ref not in self.refs]
            if missing:
                item.evidence_refs = [ref for ref in item.evidence_refs if ref in self.refs]
                self.draft.warnings.append(
                    f"Compétence « {item.content.get('name')} » : preuves ignorées {missing}."
                )
        return self.draft

    def _unique(self, ref: str) -> str:
        candidate, suffix = ref or "item", 2
        while candidate in self.refs:
            candidate, suffix = f"{ref}-{suffix}", suffix + 1
        self.refs.add(candidate)
        return candidate

    def _coerce_dates(self, kind: FactKind, content: dict[str, Any]) -> dict[str, Any]:
        content = dict(content)
        for field in ("start", "end", "date"):
            raw = content.get(field)
            if raw is None:
                continue
            coerced = coerce_partial_date(raw)
            if coerced != raw:
                content[field] = coerced
                if coerced is None:
                    self.draft.warnings.append(
                        f"{kind} : date « {raw} » non reconnue, laissée vide (à compléter)."
                    )
        return content


_SEPARATORS = re.compile(r"[•·▪◦●‣■□➢►\-–—|*_/]+")
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"'})


def normalize_for_match(text: str) -> str:
    """Compare des passages sans dépendre de la mise en page : casse, puces, tirets,
    guillemets typographiques et espaces sont neutralisés."""
    text = unicodedata.normalize("NFKC", text).casefold().translate(_QUOTES)
    text = _SEPARATORS.sub(" ", text)
    return " ".join(text.split())


_DATE_PATTERNS = [
    (re.compile(r"^(\d{4})-(\d{1,2})$"), lambda m: (m[1], m[2])),
    (re.compile(r"^(\d{1,2})[/.](\d{4})$"), lambda m: (m[2], m[1])),
    (re.compile(r"^(\d{4})$"), lambda m: (m[1], None)),
]


def coerce_partial_date(raw: str) -> str | None:
    """« 09/2023 » -> « 2023-09 », « 2023 » -> « 2023 » ; sinon None (jamais deviné)."""
    value = raw.strip()
    for pattern, parts in _DATE_PATTERNS:
        if match := pattern.match(value):
            year, month = parts(match)
            if month is None:
                return year
            if 1 <= int(month) <= 12:
                return f"{year}-{int(month):02d}"
    return None
