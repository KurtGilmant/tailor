from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tailor.config import Settings
from tailor.main import create_app
from tailor.security import dev_token

from .conftest import BASE_URL, TOKEN


def test_missing_token_rejected(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Authorization": ""})
    assert response.status_code == 401
    assert "version" not in response.text


def test_wrong_token_rejected(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


@pytest.mark.parametrize("host", ["evil.example:8765", "127.0.0.1:9999", "attacker.localhost"])
def test_foreign_host_rejected(client: TestClient, host: str) -> None:
    """Protection DNS rebinding : même avec le bon jeton, un Host étranger est refusé."""
    response = client.get("/api/health", headers={"Host": host})
    assert response.status_code == 400


def test_localhost_alias_accepted(client: TestClient) -> None:
    assert client.get("/api/health", headers={"Host": "localhost:8765"}).status_code == 200


def test_foreign_origin_rejected(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_same_origin_accepted(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": BASE_URL})
    assert response.status_code == 200


def test_vite_origin_only_in_dev(settings: Settings, tmp_path: Path) -> None:
    vite = {"Origin": "http://localhost:5173"}
    auth = {"Authorization": f"Bearer {TOKEN}"}
    for dev, expected in ((False, 403), (True, 200)):
        app = create_app(settings.model_copy(update={"dev": dev}), TOKEN, static_dir=tmp_path)
        with TestClient(app, base_url=BASE_URL, headers=auth) as c:
            assert c.get("/api/health", headers=vite).status_code == expected


def test_no_docs_exposed(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json", "/api/openapi.json"):
        assert client.get(path).status_code in (401, 404)


def test_dev_token_persisted_owner_only(tmp_path: Path) -> None:
    first = dev_token(tmp_path)
    assert dev_token(tmp_path) == first
    assert (tmp_path / "dev_token").stat().st_mode & 0o777 == 0o600


def test_spa_served_without_token_and_no_traversal(settings: Settings, tmp_path: Path) -> None:
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<div id=root></div>")
    (static / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("secret")
    app = create_app(settings, TOKEN, static_dir=static)
    with TestClient(app, base_url=BASE_URL) as c:
        assert c.get("/").text == "<div id=root></div>"
        assert c.get("/offres/42").text == "<div id=root></div>"  # routes du front
        assert c.get("/assets/app.js").text == "console.log(1)"
        assert "secret" not in c.get("/../secret.txt").text
        assert c.get("/api/inconnu").status_code == 401  # l'API reste protégée
