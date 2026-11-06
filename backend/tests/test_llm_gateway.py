import asyncio
import json

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from tailor.llm import LLMGateway, Task
from tailor.llm.errors import ConfigError, ProviderError, SchemaValidationError
from tailor.llm.models import LlmCall
from tailor.llm.prompts import PromptLibrary
from tailor.llm.providers.fake import FakeProvider

from .conftest import Person, llm_config

VALID = json.dumps({"name": "Jean", "age": 32})


def gateway(
    engine: Engine, prompts: PromptLibrary, fake: FakeProvider, **cfg: object
) -> LLMGateway:
    return LLMGateway(
        engine=engine, config=llm_config(**cfg), prompts=prompts, providers={"fake": fake}
    )


def calls(engine: Engine) -> list[LlmCall]:
    with Session(engine) as session:
        return list(session.exec(select(LlmCall).order_by(LlmCall.id)).all())  # type: ignore[arg-type]


def run(coro):
    return asyncio.run(coro)


def test_valid_response(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=[VALID])
    result = run(
        gateway(engine, prompts, fake).complete(Task.EXTRACT, "demo", {"text": "x"}, Person)
    )

    assert result == Person(name="Jean", age=32)
    request = fake.requests[0]
    assert request.schema["required"] == ["name", "age"]
    assert request.schema_name == "Person"
    [row] = calls(engine)
    assert (row.status, row.task, row.prompt_id, row.input_tokens) == ("ok", "extract", "demo", 100)
    assert row.prompt_version.startswith("1-")


def test_corrected_on_second_attempt(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=['{"name": "Jean", "age": "trente-deux"}', VALID])
    result = run(
        gateway(engine, prompts, fake).complete(Task.EXTRACT, "demo", {"text": "x"}, Person)
    )

    assert result.age == 32
    retry = fake.requests[1].user
    assert (
        "age" in retry and "trente-deux" in retry
    )  # l'erreur et la réponse fautive sont renvoyées
    assert retry.endswith("Texte : <<<x>>>")
    assert [c.status for c in calls(engine)] == ["invalid", "ok"]


def test_explicit_failure_after_limit(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=["pas du json", '{"name": "Jean"}'])
    with pytest.raises(SchemaValidationError, match="Person après 2 tentative"):
        run(gateway(engine, prompts, fake).complete(Task.EXTRACT, "demo", {"text": "x"}, Person))
    assert [c.status for c in calls(engine)] == ["invalid", "invalid"]


def test_identical_call_served_from_cache(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=[VALID])
    gw = gateway(engine, prompts, fake)
    first = run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))
    second = run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))

    assert first == second
    assert len(fake.requests) == 1  # aucun second appel au fournisseur
    assert [c.status for c in calls(engine)] == ["ok", "cached"]


def test_cache_misses_on_different_input_or_regenerate(
    engine: Engine, prompts: PromptLibrary
) -> None:
    fake = FakeProvider(replies=[VALID, VALID, VALID])
    gw = gateway(engine, prompts, fake)
    run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))
    run(gw.complete(Task.EXTRACT, "demo", {"text": "y"}, Person))
    run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person, regenerate=True))
    assert len(fake.requests) == 3


def test_routing_uses_task_model_and_effort(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=[VALID])
    gw = gateway(
        engine,
        prompts,
        fake,
        routes={"write": {"provider": "fake", "model": "gros-modele", "effort": "high"}},
    )
    run(gw.complete(Task.WRITE, "demo", {"text": "x"}, Person))
    assert (fake.requests[0].model, fake.requests[0].effort) == ("gros-modele", "high")


def test_provider_error_is_logged_and_raised(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(replies=[])
    with pytest.raises(ProviderError):
        run(gateway(engine, prompts, fake).complete(Task.EXTRACT, "demo", {"text": "x"}, Person))
    [row] = calls(engine)
    assert row.status == "error" and row.error


def test_cloud_cost_uses_pricing(engine: Engine, prompts: PromptLibrary) -> None:
    fake = FakeProvider(
        "cloudy", replies=[VALID], is_cloud=True, guard=lambda *_: None, tokens=(1_000_000, 100_000)
    )
    config = llm_config(
        providers={"cloudy": {"type": "fake", "cloud": True}},
        routes={"extract": {"provider": "cloudy", "model": "claude-opus-5-5"}},
    )
    gw = LLMGateway(engine=engine, config=config, prompts=prompts, providers={"cloudy": fake})
    run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))
    [row] = calls(engine)
    assert row.cost_usd == pytest.approx(4.0 + 2.0)  # 1M entrée à 4 $ + 100k sortie à 20 $/M


def test_config_rejects_cloud_model_without_pricing() -> None:
    with pytest.raises(ConfigError, match="aucun tarif"):
        llm_config(routes={"extract": {"provider": "anthropic", "model": "modele-inconnu"}})


def test_config_rejects_unknown_provider() -> None:
    with pytest.raises(ConfigError, match="fournisseur inconnu"):
        llm_config(routes={"extract": {"provider": "nulle-part", "model": "m"}})


def test_example_fake_builds_valid_instance(engine: Engine, prompts: PromptLibrary) -> None:
    """Sans script, le faux fournisseur fabrique une réponse valide (mode démo)."""
    gw = gateway(engine, prompts, FakeProvider())
    result = run(gw.complete(Task.SCORE, "demo", {"text": "x"}, Person))
    assert result == Person(name="exemple", age=0)
