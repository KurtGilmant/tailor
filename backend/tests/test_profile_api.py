import json

import pytest
from fastapi.testclient import TestClient

from tailor.llm import LLMGateway
from tailor.llm.prompts import PromptLibrary
from tailor.llm.providers.fake import FakeProvider

from .conftest import llm_config
from .cv_fixtures import cv_pdf, scanned_pdf
from .test_cv_import import EXTRACTION

PDF = "application/pdf"


def use_fake_llm(client: TestClient, *replies: str) -> FakeProvider:
    app = client.app
    fake = FakeProvider(replies=list(replies))
    app.state.llm = LLMGateway(  # type: ignore[attr-defined]
        engine=app.state.engine,  # type: ignore[attr-defined]
        config=llm_config(),
        prompts=PromptLibrary(),
        providers={"fake": fake},
    )
    return fake


def upload(client: TestClient, data: bytes, filename: str = "cv.pdf") -> dict:
    response = client.post("/api/profile/imports", files={"file": (filename, data, PDF)})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def draft(client: TestClient) -> dict:
    use_fake_llm(client, json.dumps(EXTRACTION, ensure_ascii=False))
    return upload(client, cv_pdf())


def test_import_produces_reviewable_draft(draft: dict, client: TestClient) -> None:
    assert draft["status"] == "draft"
    refs = [item["ref"] for item in draft["draft"]["items"]]
    assert "exp1" in refs and "exp1.a1" in refs
    assert len(draft["draft"]["rejected"]) == 2
    # Rien n'entre dans le profil avant validation.
    assert client.get("/api/profile").json() == {"version": 0, "facts": []}
    assert client.get(f"/api/profile/imports/{draft['id']}").json() == draft
    assert client.get("/api/profile/imports/pending").json()["id"] == draft["id"]
    client.delete(f"/api/profile/imports/{draft['id']}")
    assert client.get("/api/profile/imports/pending").json() is None


def test_validate_with_corrections(draft: dict, client: TestClient) -> None:
    items = draft["draft"]["items"]
    for item in items:
        if item["kind"] == "education":
            item["keep"] = False  # l'utilisateur écarte un élément
        if item["ref"] == "exp1.a1":
            item["content"]["text"] = "Réduction de 20 % du temps de traitement"  # et en corrige un

    response = client.post(f"/api/profile/imports/{draft['id']}/validate", json={"items": items})
    assert response.status_code == 200, response.text
    profile = response.json()

    assert profile["version"] == 1  # un seul lot = une seule version
    kinds = sorted(f["kind"] for f in profile["facts"])
    assert "education" not in kinds
    assert kinds.count("achievement") == 1
    bullet = next(f for f in profile["facts"] if f["kind"] == "achievement")
    assert bullet["content"]["text"] == "Réduction de 20 % du temps de traitement"
    assert bullet["source_excerpt"].startswith("• Réduction de 20 %")
    skills = {
        f["content"]["name"]: f["skill_status"] for f in profile["facts"] if f["kind"] == "skill"
    }
    assert skills == {"Python": "declarative", "GitHub Actions": "supported"}

    again = client.post(f"/api/profile/imports/{draft['id']}/validate", json={"items": items})
    assert again.status_code == 409


def test_validate_rejects_tampered_excerpt(draft: dict, client: TestClient) -> None:
    items = draft["draft"]["items"]
    items[0]["source_excerpt"] = "Passage qui n'est pas dans le CV"
    response = client.post(f"/api/profile/imports/{draft['id']}/validate", json={"items": items})
    assert response.status_code == 422
    assert client.get("/api/profile").json()["facts"] == []


def test_scanned_pdf_refused(client: TestClient) -> None:
    use_fake_llm(client)
    response = client.post("/api/profile/imports", files={"file": ("cv.pdf", scanned_pdf(), PDF)})
    assert response.status_code == 422
    assert "scan" in response.json()["detail"]


def test_import_without_cloud_consent_is_blocked(client: TestClient) -> None:
    """Configuration par défaut (Anthropic) sans consentement : aucun appel, message clair."""
    response = client.post("/api/profile/imports", files={"file": ("cv.pdf", cv_pdf(), PDF)})
    assert response.status_code == 409
    assert response.json()["code"] == "llm_blocked"
    assert "Consentement requis" in response.json()["detail"]


def test_fact_crud_and_history(client: TestClient) -> None:
    experience = client.post(
        "/api/profile/facts",
        json={"kind": "experience", "content": {"employer": "Acme", "title": "Stagiaire"}},
    ).json()
    bullet = client.post(
        "/api/profile/facts",
        json={"kind": "achievement", "parent_id": experience["id"], "content": {"text": "v1"}},
    ).json()
    skill = client.post(
        "/api/profile/facts",
        json={"kind": "skill", "content": {"name": "SQL", "evidence": [bullet["id"]]}},
    ).json()
    assert skill["skill_status"] == "supported"

    updated = client.put(f"/api/profile/facts/{bullet['id']}", json={"content": {"text": "v2"}})
    assert updated.json()["rev"] == 2
    history = client.get(f"/api/profile/facts/{bullet['id']}/revisions").json()
    assert [r["content"]["text"] for r in history] == ["v1", "v2"]

    translated = client.put(
        f"/api/profile/facts/{experience['id']}",
        json={
            "content": {
                "employer": "Acme",
                "title": "Stagiaire",
                "translations": {"en": {"title": "Intern"}},
            }
        },
    )
    assert translated.json()["content"]["translations"] == {"en": {"title": "Intern"}}

    retired = client.delete(f"/api/profile/facts/{experience['id']}").json()["retired"]
    assert set(retired) == {experience["id"], bullet["id"]}
    profile = client.get("/api/profile").json()
    assert [f["skill_status"] for f in profile["facts"]] == ["declarative"]
    assert profile["version"] == 6


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"kind": "experience", "content": {"employer": "Acme"}}, 422),
        ({"kind": "achievement", "parent_id": "inconnu", "content": {"text": "x"}}, 404),
        ({"kind": "hobby", "content": {}}, 422),
    ],
)
def test_fact_errors(client: TestClient, body: dict, status: int) -> None:
    response = client.post("/api/profile/facts", json=body)
    assert response.status_code == status
    assert response.json()["detail"]
