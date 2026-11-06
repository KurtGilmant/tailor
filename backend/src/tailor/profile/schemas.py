"""Contenu des faits du profil maître, par type de fait.

Un fait est atomique : une expérience (le poste), une réalisation (une puce rattachée
à une expérience ou un projet), une compétence, une formation, etc. Les champs
« protégés » (employeur, intitulé, dates, diplôme…) ne seront jamais produits par un
modèle de langage : ils sont recopiés tels quels, ou via la traduction saisie ici.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class FactKind(StrEnum):
    IDENTITY = "identity"
    EXPERIENCE = "experience"
    ACHIEVEMENT = "achievement"
    PROJECT = "project"
    EDUCATION = "education"
    SKILL = "skill"
    LANGUAGE = "language"
    CERTIFICATION = "certification"


# AAAA ou AAAA-MM : on ne fabrique pas de précision que le CV ne donne pas.
PartialDate = Annotated[str, StringConstraints(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None
LangCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
# {"en": {"title": "Software Engineer"}} : traduction saisie par l'utilisateur, par champ.
Translations = dict[LangCode, dict[str, Text]]

# Champs reproduits à l'identique dans tout document généré (spec candidate-profile).
PROTECTED_FIELDS: dict[FactKind, tuple[str, ...]] = {
    FactKind.EXPERIENCE: ("employer", "title", "start", "end"),
    FactKind.EDUCATION: ("institution", "degree", "field", "start", "end"),
    FactKind.CERTIFICATION: ("name", "issuer", "date"),
}
# Parmi eux, ceux qui ont un sens à traduire (pas les dates).
TRANSLATABLE_FIELDS: dict[FactKind, tuple[str, ...]] = {
    FactKind.EXPERIENCE: ("employer", "title"),
    FactKind.EDUCATION: ("institution", "degree", "field"),
    FactKind.CERTIFICATION: ("name",),
}


class _Content(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Translatable(_Content):
    kind: FactKind  # renseigné par le service, pour valider les traductions
    translations: Translations = Field(default_factory=dict)

    @model_validator(mode="after")
    def _known_fields(self) -> _Translatable:
        allowed = TRANSLATABLE_FIELDS[self.kind]
        for lang, fields in self.translations.items():
            unknown = set(fields) - set(allowed)
            if unknown:
                raise ValueError(
                    f"traduction « {lang} » : champs non traduisibles {sorted(unknown)} "
                    f"(autorisés : {', '.join(allowed)})"
                )
        return self


class Link(_Content):
    label: Text
    url: Text


class IdentityContent(_Content):
    full_name: Text
    headline: OptionalText = None
    email: OptionalText = None
    phone: OptionalText = None
    location: OptionalText = None
    links: list[Link] = Field(default_factory=list)


class ExperienceContent(_Translatable):
    kind: FactKind = FactKind.EXPERIENCE
    employer: Text
    title: Text
    start: PartialDate | None = None
    end: PartialDate | None = None
    current: bool = False
    location: OptionalText = None
    summary: OptionalText = None


class AchievementContent(_Content):
    text: Text


class ProjectContent(_Content):
    name: Text
    description: OptionalText = None
    url: OptionalText = None
    start: PartialDate | None = None
    end: PartialDate | None = None


class EducationContent(_Translatable):
    kind: FactKind = FactKind.EDUCATION
    institution: Text
    degree: Text
    field: OptionalText = None
    start: PartialDate | None = None
    end: PartialDate | None = None


class SkillContent(_Content):
    name: Text
    category: OptionalText = None
    # Faits qui démontrent la compétence (expérience, projet, réalisation, formation…).
    evidence: list[str] = Field(default_factory=list)


class LanguageContent(_Content):
    name: Text
    level: OptionalText = None


class CertificationContent(_Translatable):
    kind: FactKind = FactKind.CERTIFICATION
    name: Text
    issuer: OptionalText = None
    date: PartialDate | None = None


CONTENT_MODELS: dict[FactKind, type[_Content]] = {
    FactKind.IDENTITY: IdentityContent,
    FactKind.EXPERIENCE: ExperienceContent,
    FactKind.ACHIEVEMENT: AchievementContent,
    FactKind.PROJECT: ProjectContent,
    FactKind.EDUCATION: EducationContent,
    FactKind.SKILL: SkillContent,
    FactKind.LANGUAGE: LanguageContent,
    FactKind.CERTIFICATION: CertificationContent,
}

# Une réalisation se rattache à une expérience ou à un projet ; les autres faits sont racines.
PARENT_KINDS: dict[FactKind, frozenset[FactKind]] = {
    FactKind.ACHIEVEMENT: frozenset({FactKind.EXPERIENCE, FactKind.PROJECT}),
}
EVIDENCE_KINDS = frozenset(
    {
        FactKind.EXPERIENCE,
        FactKind.ACHIEVEMENT,
        FactKind.PROJECT,
        FactKind.EDUCATION,
        FactKind.CERTIFICATION,
    }
)


def validate_content(kind: FactKind, content: dict) -> dict:
    """Valide et normalise le contenu d'un fait ; renvoie le dict stocké (sans `kind`)."""
    model = CONTENT_MODELS[kind]
    data = dict(content)
    if issubclass(model, _Translatable):
        data["kind"] = kind
    return model.model_validate(data).model_dump(exclude={"kind"}, mode="json")
