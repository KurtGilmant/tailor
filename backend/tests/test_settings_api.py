import json

from fastapi.testclient import TestClient


def test_preferences_round_trip(client: TestClient) -> None:
    assert client.get("/api/preferences").json()["contract_types"] == []
    wanted = {
        "contract_types": ["alternance"],
        "locations": ["Bordeaux"],
        "work_modes": ["sur_site", "teletravail_complet"],
        "available_from": "2027-09-01",
        "salary": {"min": 20000, "max": 24000, "currency": "EUR", "period": "annuel"},
    }
    saved = client.put("/api/preferences", json=wanted)
    assert saved.status_code == 200
    stored = client.get("/api/preferences").json()
    assert {key: stored[key] for key in wanted} == wanted


def test_preferences_validation(client: TestClient) -> None:
    assert client.put("/api/preferences", json={"contract_types": ["bénévolat"]}).status_code == 422
    assert client.put("/api/preferences", json={"inventé": 1}).status_code == 422


def test_answer_bank_reuse_and_uniqueness(client: TestClient) -> None:
    created = client.post(
        "/api/answers", json={"question": "Quel est votre préavis ?", "answer": "Un mois."}
    )
    assert created.status_code == 201

    # Même question, casse / accents / ponctuation différents : même réponse, à l'identique.
    found = client.get("/api/answers/lookup", params={"question": "quel est votre PREAVIS"}).json()
    assert found["answer"] == "Un mois."
    assert client.get("/api/answers/lookup", params={"question": "Autre ?"}).json() is None

    duplicate = client.post(
        "/api/answers", json={"question": "Quel est votre préavis", "answer": "x"}
    )
    assert duplicate.status_code == 409

    entry_id = created.json()["id"]
    updated = client.put(
        f"/api/answers/{entry_id}",
        json={"question": "Quel est votre préavis ?", "answer": "Aucun."},
    )
    assert updated.json()["answer"] == "Aucun."
    assert client.delete(f"/api/answers/{entry_id}").status_code == 204
    assert client.get("/api/answers").json() == []


def seed(client: TestClient) -> None:
    experience = client.post(
        "/api/profile/facts",
        json={"kind": "experience", "content": {"employer": "Acme", "title": "Stagiaire"}},
    ).json()
    client.put(
        f"/api/profile/facts/{experience['id']}",
        json={"content": {"employer": "Acme", "title": "Stagiaire data"}},
    )
    client.put("/api/preferences", json={"contract_types": ["stage"]})
    client.post("/api/answers", json={"question": "Préavis ?", "answer": "Aucun."})
    client.post("/api/llm/consents/anthropic")


def test_export_contains_everything(client: TestClient) -> None:
    seed(client)
    response = client.get("/api/data/export")
    assert response.headers["content-disposition"] == 'attachment; filename="tailor-export.json"'
    export = json.loads(response.text)

    assert (export["format"], export["format_version"]) == ("tailor-export", 1)
    [fact] = export["profile"]["facts"]
    assert [r["content"]["title"] for r in fact["revisions"]] == ["Stagiaire", "Stagiaire data"]
    assert len(export["profile"]["versions"]) == 2
    assert export["preferences"]["contract_types"] == ["stage"]
    assert export["answers"][0]["answer"] == "Aucun."
    assert export["llm"]["consents"][0]["provider"] == "anthropic"


def test_delete_all_requires_confirmation_then_empties_everything(client: TestClient) -> None:
    seed(client)
    files_dir = client.app.state.settings.files_dir  # type: ignore[attr-defined]
    (files_dir / "cv.pdf").write_bytes(b"%PDF")

    assert client.post("/api/data/delete", json={"confirmation": "oui"}).status_code == 422
    assert client.get("/api/profile").json()["facts"] != []

    assert client.post("/api/data/delete", json={"confirmation": "SUPPRIMER"}).status_code == 204

    assert client.get("/api/profile").json() == {"version": 0, "facts": []}
    export = json.loads(client.get("/api/data/export").text)
    assert export["profile"] == {"versions": [], "facts": []}
    assert export["answers"] == [] and export["llm"] == {"consents": [], "calls": []}
    assert export["preferences"]["contract_types"] == []
    assert files_dir.is_dir() and list(files_dir.iterdir()) == []
    # L'application reste utilisable sur un profil vide.
    created = client.post(
        "/api/profile/facts", json={"kind": "language", "content": {"name": "Anglais"}}
    )
    assert created.status_code == 201
