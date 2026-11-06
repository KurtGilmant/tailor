from fastapi.testclient import TestClient
from sqlmodel import Session

from tailor.llm.models import LlmCall


def add_calls(client: TestClient) -> None:
    engine = client.app.state.engine  # type: ignore[attr-defined]
    with Session(engine) as session:
        for task, cost in (("write", 0.5), ("write", 0.25), ("extract", 0.01)):
            session.add(
                LlmCall(
                    task=task,
                    provider="anthropic",
                    model="claude-opus-5-5",
                    is_cloud=True,
                    prompt_id="p",
                    prompt_version="1-abc",
                    input_tokens=10,
                    output_tokens=5,
                    cost_usd=cost,
                    status="ok",
                )
            )
        session.commit()


def test_status_lists_routes_and_providers(client: TestClient) -> None:
    status = client.get("/api/llm/status").json()
    assert status["mode"] == "standard"
    assert {r["task"] for r in status["routes"]} == {"extract", "score", "write", "verify"}
    assert all(r["model"] == "claude-opus-5-5" for r in status["routes"])
    anthropic = next(p for p in status["providers"] if p["name"] == "anthropic")
    assert anthropic == {
        "name": "anthropic",
        "type": "anthropic",
        "is_cloud": True,
        "api_key_configured": False,
        "consent_granted_at": None,
    }
    ollama = next(p for p in status["providers"] if p["name"] == "ollama")
    assert ollama["is_cloud"] is False


def test_grant_and_revoke_consent(client: TestClient) -> None:
    granted = client.post("/api/llm/consents/anthropic")
    assert granted.status_code == 201
    assert granted.json()["consent_granted_at"] is not None
    assert client.post("/api/llm/consents/anthropic").status_code == 201  # idempotent

    assert client.delete("/api/llm/consents/anthropic").status_code == 204
    status = client.get("/api/llm/status").json()
    anthropic = next(p for p in status["providers"] if p["name"] == "anthropic")
    assert anthropic["consent_granted_at"] is None


def test_consent_only_for_known_cloud_providers(client: TestClient) -> None:
    assert client.post("/api/llm/consents/inconnu").status_code == 404
    assert client.post("/api/llm/consents/ollama").status_code == 400


def test_usage_aggregates_by_day_and_task(client: TestClient) -> None:
    add_calls(client)
    usage = client.get("/api/llm/usage").json()

    assert usage["month_spend_usd"] == 0.76
    assert len(usage["recent"]) == 3
    assert usage["recent"][0]["task"] == "extract"  # plus récent d'abord
    by_task = {d["task"]: d for d in usage["daily"]}
    assert by_task["write"]["calls"] == 2
    assert by_task["write"]["cost_usd"] == 0.75
    assert by_task["write"]["input_tokens"] == 20


def test_usage_validates_query(client: TestClient) -> None:
    assert client.get("/api/llm/usage", params={"days": 0}).status_code == 422
