import asyncio
import json

import pytest
from sqlalchemy import Engine

from tailor.llm import LLMGateway
from tailor.llm.prompts import PromptLibrary
from tailor.llm.providers.fake import FakeProvider
from tailor.profile.cv_import import (
    PROMPT_ID,
    Draft,
    coerce_partial_date,
    extract_cv,
    normalize_for_match,
)
from tailor.profile.schemas import FactKind
from tailor.profile.text_extraction import extract_text

from .conftest import llm_config
from .cv_fixtures import cv_pdf

# Ce que renverrait un modèle sur le CV de test, avec deux éléments piégés.
EXTRACTION = {
    "identity": {
        "full_name": "Léa Martin",
        "headline": "Ingénieure données",
        "email": "lea.martin@example.org",
        "phone": None,
        "location": "Bordeaux",
        "links": [],
        "excerpt": "Léa Martin",
    },
    "experiences": [
        {
            "ref": "exp1",
            "employer": "Société Exemple",
            "title": "Ingénieure données",
            "start": "09/2023",
            "end": None,
            "current": True,
            "location": None,
            "excerpt": "Ingénieure données — Société Exemple (2023-09 – aujourd'hui)",
            "achievements": [
                {
                    "text": "Réduction de 20 % du temps de traitement des flux de facturation",
                    "excerpt": "• Réduction de 20 % du temps de traitement des flux de facturation",
                },
                {
                    # Piège : réalisation inventée, absente du CV.
                    "text": "Encadrement d'une équipe de 8 personnes",
                    "excerpt": "Encadrement d'une équipe de 8 personnes",
                },
            ],
        }
    ],
    "projects": [],
    "education": [
        {
            "ref": "edu1",
            "institution": "Université de Bordeaux",
            "degree": "Master Intelligence artificielle",
            "field": None,
            "start": "2021",
            "end": "2023",
            "excerpt": "Master Intelligence artificielle — Université de Bordeaux",
        }
    ],
    "certifications": [],
    "skills": [
        {"name": "Python", "category": "Langage", "evidence_refs": [], "excerpt": "Python, SQL"},
        {
            "name": "GitHub Actions",
            "category": "Outil",
            "evidence_refs": ["exp1", "proj9"],
            "excerpt": "chaîne d'intégration continue avec GitHub Actions",
        },
        # Piège : compétence au passage reformulé.
        {
            "name": "Kubernetes",
            "category": None,
            "evidence_refs": [],
            "excerpt": "Kubernetes avancé",
        },
    ],
    "languages": [],
}


@pytest.fixture
def draft(engine: Engine) -> tuple[Draft, str]:
    text = extract_text("cv.pdf", cv_pdf())
    fake = FakeProvider(replies=[json.dumps(EXTRACTION, ensure_ascii=False)])
    gateway = LLMGateway(
        engine=engine, config=llm_config(), prompts=PromptLibrary(), providers={"fake": fake}
    )
    result = asyncio.run(extract_cv(gateway, text))
    # Le vrai prompt du dépôt est utilisé, avec le texte du CV entre délimiteurs.
    assert fake.requests[0].prompt_id == PROMPT_ID
    assert "<<<CV\n" + text + "\nCV>>>" in fake.requests[0].user
    return result, text


def test_every_kept_excerpt_is_in_the_cv(draft: tuple[Draft, str]) -> None:
    result, text = draft
    normalized = normalize_for_match(text)
    assert result.items
    for item in result.items:
        assert normalize_for_match(item.source_excerpt) in normalized


def test_invented_items_are_rejected(draft: tuple[Draft, str]) -> None:
    result, _ = draft
    rejected = {(r.kind, r.reason) for r in result.rejected}
    assert (FactKind.ACHIEVEMENT, "passage introuvable tel quel dans le CV") in rejected
    assert (FactKind.SKILL, "passage introuvable tel quel dans le CV") in rejected
    texts = [i.content.get("text") for i in result.items if i.kind == FactKind.ACHIEVEMENT]
    assert texts == ["Réduction de 20 % du temps de traitement des flux de facturation"]


def test_structure_dates_and_evidence(draft: tuple[Draft, str]) -> None:
    result, _ = draft
    by_ref = {item.ref: item for item in result.items}
    assert by_ref["exp1"].content["start"] == "2023-09"  # « 09/2023 » normalisé
    assert by_ref["exp1.a1"].parent_ref == "exp1"
    actions = next(i for i in result.items if i.content.get("name") == "GitHub Actions")
    assert actions.evidence_refs == ["exp1"]  # « proj9 » n'existe pas : retiré
    assert any("proj9" in warning for warning in result.warnings)


def test_partial_dates() -> None:
    assert coerce_partial_date("2023-9") == "2023-09"
    assert coerce_partial_date("09/2023") == "2023-09"
    assert coerce_partial_date("2021") == "2021"
    assert coerce_partial_date("13/2023") is None
    assert coerce_partial_date("septembre 2023") is None  # jamais deviné


def test_normalization_ignores_layout() -> None:
    assert normalize_for_match("• Réduction de 20 %\n du temps") == normalize_for_match(
        "réduction de 20 % du temps"
    )
    assert normalize_for_match("l’équipe — “data”") == normalize_for_match('l\'équipe "data"')
