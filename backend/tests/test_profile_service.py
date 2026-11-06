from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from tailor.profile.schemas import FactKind
from tailor.profile.service import NewFact, ProfileError, ProfileService

EXPERIENCE = {"employer": "Société Générale", "title": "Ingénieure données", "start": "2023-09"}


@pytest.fixture
def service(engine: Engine) -> Iterator[ProfileService]:
    with Session(engine) as session:
        yield ProfileService(session)


def test_update_creates_revision_keeps_id_and_bumps_version(service: ProfileService) -> None:
    fact = service.create_fact(
        FactKind.ACHIEVEMENT,
        {"text": "x"},
        parent_id=service.create_fact(FactKind.EXPERIENCE, EXPERIENCE).id,
    )
    before = service.current_version()

    updated = service.update_fact(fact.id, {"text": "Réduction de 20 % du temps de traitement"})

    assert updated.id == fact.id
    assert updated.current_rev == 2
    assert service.current_version() == before + 1
    revisions = service.revisions(fact.id)
    assert [r.content["text"] for r in revisions] == [
        "x",
        "Réduction de 20 % du temps de traitement",
    ]
    assert revisions[1].profile_version == before + 1


def test_identical_update_is_a_no_op(service: ProfileService) -> None:
    fact = service.create_fact(FactKind.EXPERIENCE, EXPERIENCE)
    version = service.current_version()
    service.update_fact(fact.id, dict(EXPERIENCE))
    assert (fact.current_rev, service.current_version()) == (1, version)


def test_retired_fact_hidden_but_revisions_readable(service: ProfileService) -> None:
    experience = service.create_fact(FactKind.EXPERIENCE, EXPERIENCE)
    bullet = service.create_fact(
        FactKind.ACHIEVEMENT, {"text": "API FastAPI"}, parent_id=experience.id
    )

    retired = service.retire_fact(experience.id)

    assert set(retired) == {experience.id, bullet.id}  # les réalisations suivent leur parent
    assert service.active_facts() == []
    assert service.revision(bullet.id, 1).content == {"text": "API FastAPI"}
    with pytest.raises(ProfileError) as error:
        service.update_fact(bullet.id, {"text": "autre"})
    assert error.value.status == 409


def test_achievement_must_hang_on_experience_or_project(service: ProfileService) -> None:
    language = service.create_fact(FactKind.LANGUAGE, {"name": "Anglais", "level": "C1"})
    with pytest.raises(ProfileError, match="doit être rattaché"):
        service.create_fact(FactKind.ACHIEVEMENT, {"text": "x"})
    with pytest.raises(ProfileError, match="ne peut pas être rattaché"):
        service.create_fact(FactKind.ACHIEVEMENT, {"text": "x"}, parent_id=language.id)
    with pytest.raises(ProfileError, match="ne se rattache"):
        service.create_fact(FactKind.SKILL, {"name": "SQL"}, parent_id=language.id)


def test_skill_status_follows_active_evidence(service: ProfileService) -> None:
    project = service.create_fact(FactKind.PROJECT, {"name": "Tailor"})
    skill = service.create_fact(FactKind.SKILL, {"name": "Docker", "evidence": []})
    content = service.revision(skill.id, 1).content
    assert not service.skill_supported(content, service.active_ids())  # « déclarative »

    service.update_fact(skill.id, {"name": "Docker", "evidence": [project.id]})
    content = service.revision(skill.id, 2).content
    assert service.skill_supported(content, service.active_ids())  # « étayée »

    service.retire_fact(project.id)
    assert not service.skill_supported(content, service.active_ids())


def test_skill_evidence_must_exist_and_be_a_proof(service: ProfileService) -> None:
    language = service.create_fact(FactKind.LANGUAGE, {"name": "Anglais"})
    with pytest.raises(ProfileError, match="introuvable"):
        service.create_fact(FactKind.SKILL, {"name": "SQL", "evidence": ["inexistant"]})
    with pytest.raises(ProfileError, match="ne peut pas servir de preuve"):
        service.create_fact(FactKind.SKILL, {"name": "SQL", "evidence": [language.id]})


def test_content_validation(service: ProfileService) -> None:
    with pytest.raises(ProfileError, match="start"):
        service.create_fact(FactKind.EXPERIENCE, {**EXPERIENCE, "start": "septembre 2023"})
    with pytest.raises(ProfileError, match="Extra inputs"):
        service.create_fact(FactKind.LANGUAGE, {"name": "Anglais", "inventé": True})
    with pytest.raises(ProfileError, match="Type de fait inconnu"):
        service.create_fact("hobby", {"name": "x"})


def test_protected_field_translations(service: ProfileService) -> None:
    fact = service.create_fact(
        FactKind.EXPERIENCE, {**EXPERIENCE, "translations": {"en": {"title": "Data Engineer"}}}
    )
    assert service.revision(fact.id, 1).content["translations"] == {
        "en": {"title": "Data Engineer"}
    }
    with pytest.raises(ProfileError, match="non traduisibles"):
        service.create_fact(
            FactKind.EXPERIENCE, {**EXPERIENCE, "translations": {"en": {"start": "x"}}}
        )


def test_single_identity(service: ProfileService) -> None:
    service.create_fact(FactKind.IDENTITY, {"full_name": "Léa Martin"})
    with pytest.raises(ProfileError, match="déjà une identité"):
        service.create_fact(FactKind.IDENTITY, {"full_name": "Autre"})


def test_batch_maps_refs_in_one_version(service: ProfileService) -> None:
    version = service.current_version()
    ids = service.create_batch(
        [
            NewFact("s1", FactKind.SKILL, {"name": "Python"}, evidence_refs=("e1", "absent")),
            NewFact("a1", FactKind.ACHIEVEMENT, {"text": "API"}, parent_ref="e1"),
            NewFact("a2", FactKind.ACHIEVEMENT, {"text": "orpheline"}, parent_ref="non-conservé"),
            NewFact("e1", FactKind.EXPERIENCE, EXPERIENCE, source_excerpt="Société Générale"),
        ],
        reason="Import du CV",
    )
    assert set(ids) == {"s1", "a1", "e1"}  # la réalisation orpheline est ignorée
    assert service.current_version() == version + 1
    skill = service.revision(ids["s1"], 1)
    assert skill.content["evidence"] == [ids["e1"]]
    assert service.get_fact(ids["a1"]).parent_id == ids["e1"]
    assert service.revision(ids["e1"], 1).source_excerpt == "Société Générale"
